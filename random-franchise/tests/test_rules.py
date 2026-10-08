import json
import sqlite3
import pytest
from models.domain import RuleError, State, uid
from services.game_engine import record_game,correct_game,start_run
from services.roster_service import add_player,remove_player,swap,arrange,target_pool,locked
from services.roster_validator import validate
from services.franchise_service import create_franchise,settings,save_settings
from services.franchise_tag_service import grant
from services.wheel_engine import spin,continue_spin,available,current_job
from services.offseason_service import confirm_end,select_mvp,progress,resolve_move,finish_validation
from services.stat_engine import calculate,aggregate
from services.import_export import export_roster,import_roster
from services.challenge_service import create


def one_wedge(repo,fid,wid,**changes):
    w=repo.get('wheels',f'{fid}:{wid}')
    wedge=dict(id='fixed',text='Fixed result',weight=1,active=True,effect='none',eligibility={})
    wedge.update(changes);w['wedges']=[wedge];repo.put('wheels',w)


def drain(repo,fid):
    for _ in range(30):
        job=current_job(repo,fid)
        if not job:return
        spin(repo,fid,job['id']);continue_spin(repo,fid,job['id'],True)
    raise AssertionError('Queue did not finish')


def lose_twice(repo,fid):
    one_wedge(repo,fid,'hot_seat')
    record_game(repo,fid,uid(),'L');drain(repo,fid);record_game(repo,fid,uid(),'L')


def test_active_personnel_lock(demo):
    repo,fid=demo;p=repo.list('players',fid)[1]
    with pytest.raises(RuleError):add_player(repo,fid,{'name':'External'})
    with pytest.raises(RuleError):remove_player(repo,fid,p['id'])
    with pytest.raises(RuleError):arrange(repo,fid,p['id'],'minors',p['position'],1)
    minors=next(p for p in repo.list('players',fid) if p['area']=='minors')
    with pytest.raises(RuleError):arrange(repo,fid,minors['id'],'bench','SS',1)


def test_legal_starter_bench_and_position_swaps(demo):
    repo,fid=demo;players=repo.list('players',fid)
    starter=next(p for p in players if p['area']=='lineup' and p['position']=='CF')
    bench=next(p for p in players if p['area']=='bench')
    swap(repo,fid,starter['id'],bench['id'])
    assert repo.get('players',bench['id'])['area']=='lineup'
    assert validate(repo,fid,False).valid
    left=next(p for p in players if p['position']=='LF' and p['area']=='lineup')
    right=next(p for p in players if p['position']=='RF' and p['area']=='lineup')
    swap(repo,fid,left['id'],right['id'])
    assert repo.get('players',left['id'])['position']=='RF'


def test_illegal_swap_rolls_back(demo):
    repo,fid=demo;players=repo.list('players',fid)
    pitcher=next(p for p in players if p['kind']=='pitcher');hitter=players[0]
    before=repo.get('players',pitcher['id'])
    with pytest.raises(RuleError):swap(repo,fid,pitcher['id'],hitter['id'])
    assert repo.get('players',pitcher['id'])==before


def test_first_loss_and_second_loss(demo):
    repo,fid=demo;one_wedge(repo,fid,'hot_seat')
    record_game(repo,fid,uid(),'L')
    assert repo.get('franchises',fid)['state']==State.WHEEL
    assert current_job(repo,fid)['wheel_id']=='hot_seat'
    assert locked(repo,fid)
    with pytest.raises(RuleError):record_game(repo,fid,uid(),'W')
    drain(repo,fid);record_game(repo,fid,uid(),'L')
    assert repo.get('franchises',fid)['state']==State.ENDED
    assert not locked(repo,fid)
    with pytest.raises(RuleError):record_game(repo,fid,uid(),'W')
    assert len(repo.list('snapshots',fid))==2


def test_move_cannot_resolve_during_run(demo):
    repo,fid=demo;m=repo.list('moves',fid)[0]
    with pytest.raises(RuleError):resolve_move(repo,fid,m['id'],'resolved','Confirmed',new_player={'name':'A'},confirmed=True)
    assert repo.get('moves',m['id'])['status']=='pending'


def test_game_duplicate_and_milestone_idempotent(demo):
    repo,fid=demo;record_game(repo,fid,uid(),'W')
    gid=uid();record_game(repo,fid,gid,'W');record_game(repo,fid,gid,'W')
    assert len(repo.list('games',fid))==2
    assert len([r for r in repo.list('rewards',fid) if r['id'].startswith('milestone:')])==1
    assert len(repo.get('franchises',fid)['queue'])==1


def test_tags_excluded_and_fourth_tag_decision(demo):
    repo,fid=demo;players=repo.list('players',fid)
    assert players[0]['id'] not in {p['id'] for p in target_pool(repo,fid)}
    assert grant(repo,fid,players[1]['id'])=='granted'
    assert grant(repo,fid,players[2]['id'])=='granted'
    assert grant(repo,fid,players[3]['id'])=='cap_decision_required'
    assert grant(repo,fid,players[3]['id'],players[0]['id'])=='granted'
    assert players[3]['id'] not in {p['id'] for p in target_pool(repo,fid)}
    assert players[0]['id'] in {p['id'] for p in target_pool(repo,fid)}


def test_nested_wheel_and_immutable_spins(demo):
    repo,fid=demo;one_wedge(repo,fid,'front_office',follow_up='position');one_wedge(repo,fid,'position',effect='acquire')
    record_game(repo,fid,uid(),'W');record_game(repo,fid,uid(),'W')
    job=current_job(repo,fid);first=spin(repo,fid,job['id'])
    assert spin(repo,fid,job['id'])==first
    continue_spin(repo,fid,job['id'])
    assert current_job(repo,fid)['wheel_id']=='position'
    drain(repo,fid)
    assert len(repo.list('spins',fid))==2
    assert repo.list('moves',fid)[-1]['constraints']['branch']==['Fixed result']
    with pytest.raises(sqlite3.IntegrityError):repo.delete('spins',first['id'])
    with pytest.raises(sqlite3.IntegrityError):repo.put('spins',first)


def test_impossible_nested_branch_preserves_parent(demo):
    repo,fid=demo;one_wedge(repo,fid,'front_office',follow_up='position');one_wedge(repo,fid,'position',active=False)
    record_game(repo,fid,uid(),'W');record_game(repo,fid,uid(),'W')
    parent=current_job(repo,fid);original=spin(repo,fid,parent['id']);continue_spin(repo,fid,parent['id'])
    child=current_job(repo,fid);result=spin(repo,fid,child['id']);continue_spin(repo,fid,child['id'])
    assert result['result']['id']=='impossible'
    assert repo.get('spins',parent['id'])==original
    assert len(repo.list('spins',fid))==2
    assert repo.list('moves',fid)[-1]['status']=='deferred'


def test_zero_two_meltdown(demo):
    repo,fid=demo;lose_twice(repo,fid)
    confirm_end(repo,fid);select_mvp(repo,fid,repo.list('players',fid)[0]['id'])
    one_wedge(repo,fid,'mvp');drain(repo,fid);progress(repo,fid)
    one_wedge(repo,fid,'elimination');drain(repo,fid);progress(repo,fid)
    assert current_job(repo,fid)['wheel_id']=='meltdown'


def test_hitting_and_pitching_rates():
    h=calculate('hitter',dict(ab=10,h=4,doubles=1,triples=0,hr=1,bb=2,hbp=1,sf=1))
    assert h['avg']==.4 and h['slg']==.8 and h['obp']==.5 and h['ops']==1.3
    p=calculate('pitcher',dict(outs=8,er=2,ha=3,bb=1))
    assert p['ip']=='2.2' and p['era']==6.75 and p['whip']==1.5
    assert calculate('pitcher',{'outs':1})['ip']=='0.1'
    assert calculate('pitcher',{'outs':2})['ip']=='0.2'
    assert calculate('pitcher',{'outs':0})['era']==0


def test_stat_corrections_no_duplicate_rewards(demo):
    repo,fid=demo;p=repo.list('players',fid)[0]
    gid=uid();record_game(repo,fid,gid,'W',[dict(player_id=p['id'],line=dict(games=1,pa=3,ab=3,h=1))])
    line=[dict(player_id=p['id'],line=dict(games=1,pa=3,ab=3,h=2))]
    correct_game(repo,fid,gid,line,'Fix a missed hit');correct_game(repo,fid,gid,line,'Verify')
    assert aggregate(repo,fid,p)['h']==2
    assert len(repo.list('games',fid))==1
    assert len(repo.list('rewards',fid))==1
    assert len([c for c in repo.list('corrections',fid) if c['action']=='correct_game'])==2


def test_outcome_correction_retracts_unspun_milestone(demo):
    repo,fid=demo;record_game(repo,fid,uid(),'W');gid=uid();record_game(repo,fid,gid,'W')
    correct_game(repo,fid,gid,[],'It was a loss','L')
    rewards=[r for r in repo.list('rewards',fid) if r['id'].startswith('milestone:')]
    assert rewards[0]['status']=='revoked'
    assert current_job(repo,fid)['wheel_id']=='hot_seat'
    correct_game(repo,fid,gid,[],'Actually a win','W')
    assert len(repo.list('rewards',fid))==1
    assert current_job(repo,fid)['wheel_id']=='front_office'


def test_outcome_edit_after_spin_rejected(demo):
    repo,fid=demo;gid=uid();record_game(repo,fid,gid,'L');job=current_job(repo,fid);spin(repo,fid,job['id'])
    with pytest.raises(RuleError):correct_game(repo,fid,gid,[],'Change result','W')
    correct_game(repo,fid,gid,[],'Stats only')


def test_validation_blocks_illegal_next_run(demo):
    repo,fid=demo;lose_twice(repo,fid)
    f=repo.get('franchises',fid);f['state']=State.READY;repo.put('franchises',f)
    p=repo.list('players',fid)[0];p['eligibility']='illegal';repo.put('players',p)
    with pytest.raises(RuleError):start_run(repo,fid)


def test_invalid_stat_transaction_has_no_partial_game(demo):
    repo,fid=demo;p=repo.list('players',fid)[0];gid=uid()
    with pytest.raises(RuleError):record_game(repo,fid,gid,'W',[dict(player_id=p['id'],line=dict(games=1,ab=1,pa=1,h=2))])
    assert repo.get('games',gid) is None
    assert repo.get('runs',repo.get('franchises',fid)['current_run'])['wins']==0


def test_import_export_atomic(repo):
    fid=create_franchise(repo,'Test','Event')
    raw=json.dumps([dict(name='One',ovr=80),dict(name='',ovr=80)])
    with pytest.raises(RuleError):import_roster(repo,fid,raw,'json')
    assert repo.list('players',fid)==[]
    import_roster(repo,fid,json.dumps([dict(name='One',ovr=80,secondary=['CF'])]),'json')
    another=create_franchise(repo,'Other','Event');import_roster(repo,another,export_roster(repo,fid,'csv'),'csv')
    assert repo.list('players',another)[0]['secondary']==['CF']


def test_dfa_target_is_dynamic_bottom_three(demo):
    repo,fid=demo;options=available(repo,fid,dict(wheel_id='dfa_target',depth=1))
    assert len(options)==3
    assert repo.list('tags',fid)[0]['player_id'] not in {w['target_id'] for w in options}


def test_settings_cannot_change_mid_run(demo):
    repo,fid=demo
    with pytest.raises(RuleError):save_settings(repo,fid,settings(repo,fid))


def test_no_hitter_auto_tag_idempotent(demo):
    repo,fid=demo;p=next(p for p in repo.list('players',fid) if p['kind']=='pitcher')
    line=dict(player_id=p['id'],line={'games':1,'outs':9},flags={'no_hitter':True})
    gid=uid();record_game(repo,fid,gid,'W',[line]);correct_game(repo,fid,gid,[line],'Verify')
    assert len([t for t in repo.list('tags',fid) if t['player_id']==p['id'] and t['active']])==1


def test_next_run_challenge_binds_to_next_entry(demo):
    repo,fid=demo;lose_twice(repo,fid);f=repo.get('franchises',fid);p=repo.list('players',fid)[0]
    cid=create(repo,fid,f['current_run'],p['id'],'5 hits next run','h',5,'next_run','tag')
    assert repo.get('challenges',cid)['status']=='waiting_next_run'
    f['state']=State.READY;repo.put('franchises',f);rid=start_run(repo,fid)
    assert repo.get('challenges',cid)['run_id']==rid
    assert repo.get('challenges',cid)['status']=='active'


def test_sqlite_backup_contains_committed_data(demo,tmp_path):
    repo,fid=demo;path=tmp_path/'backup.db';path.write_bytes(repo.backup_bytes())
    con=sqlite3.connect(path)
    assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
    assert con.execute('SELECT count(*) FROM players').fetchone()[0]==27
    con.close()


def test_retry_only_impossible_child_keeps_parent(demo):
    from services.wheel_engine import retry_impossible_branch
    repo,fid=demo;one_wedge(repo,fid,'front_office',follow_up='position');one_wedge(repo,fid,'position',active=False)
    record_game(repo,fid,uid(),'W');record_game(repo,fid,uid(),'W')
    parent=current_job(repo,fid);parent_result=spin(repo,fid,parent['id'])
    with pytest.raises(RuleError):retry_impossible_branch(repo,fid,parent['id'])
    continue_spin(repo,fid,parent['id']);child=current_job(repo,fid);spin(repo,fid,child['id'])
    with pytest.raises(RuleError):retry_impossible_branch(repo,fid,child['id'])
    one_wedge(repo,fid,'position',effect='acquire')
    next_id=retry_impossible_branch(repo,fid,child['id']);spin(repo,fid,next_id);continue_spin(repo,fid,next_id)
    assert repo.get('spins',parent['id'])==parent_result
    assert len(repo.list('spins',fid))==3
    assert repo.get('spins',next_id)['parent_spin']==parent['id']


def test_complete_offseason_and_next_run(demo):
    repo,fid=demo;lose_twice(repo,fid)
    confirm_end(repo,fid);select_mvp(repo,fid,repo.list('players',fid)[0]['id'])
    one_wedge(repo,fid,'mvp');drain(repo,fid);progress(repo,fid)
    one_wedge(repo,fid,'elimination');drain(repo,fid);progress(repo,fid)
    one_wedge(repo,fid,'meltdown');drain(repo,fid)
    assert repo.get('franchises',fid)['state']==State.MOVES
    progress(repo,fid);progress(repo,fid);finish_validation(repo,fid)
    rid=start_run(repo,fid);r=repo.get('runs',rid)
    assert r['number']==2 and r['wins']==0 and r['losses']==0


def test_full_backup_restore_only_into_empty(demo,tmp_path):
    from services.backup_service import restore_empty
    from repositories.sqlite import SQLiteRepository
    repo,fid=demo;record_game(repo,fid,uid(),'W');data=repo.backup_bytes()
    destination=SQLiteRepository(tmp_path/'restored.db')
    assert restore_empty(destination,data)==1
    assert destination.get('franchises',fid)==repo.get('franchises',fid)
    assert destination.list('games',fid)==repo.list('games',fid)
    with pytest.raises(RuleError):restore_empty(destination,data)
    destination.close()


def test_pending_removal_can_be_canceled_only_with_award(demo):
    repo,fid=demo;lose_twice(repo,fid)
    f=repo.get('franchises',fid);f['state']=State.MOVES;repo.put('franchises',f)
    target=target_pool(repo,fid)[0]
    removal=dict(id=uid(),franchise_id=fid,run_id=f['current_run'],type='dfa',target=target['id'],status='pending',critical=True,description='DFA target',source='elimination',constraints={})
    reward=dict(id=uid(),franchise_id=fid,run_id=f['current_run'],type='save_dfa',status='pending',critical=False,description='Save Pending DFA',source='premium',constraints={})
    repo.put('moves',removal);repo.put('moves',reward)
    with pytest.raises(RuleError):resolve_move(repo,fid,removal['id'],'canceled','I just want to skip it',confirmed=True)
    resolve_move(repo,fid,reward['id'],'resolved','Use earned save',confirmed=True,cancel_move_id=removal['id'])
    assert repo.get('moves',removal['id'])['status']=='canceled'
    assert repo.get('players',target['id'])['area']==target['area']


def test_audited_target_cannot_be_arbitrarily_changed(demo):
    repo,fid=demo;lose_twice(repo,fid)
    f=repo.get('franchises',fid);f['state']=State.MOVES;repo.put('franchises',f)
    pool=target_pool(repo,fid)
    m=dict(id=uid(),franchise_id=fid,run_id=f['current_run'],type='dfa',target=pool[0]['id'],status='pending',critical=True,description='DFA selected player',source='elimination',constraints={})
    repo.put('moves',m)
    with pytest.raises(RuleError):resolve_move(repo,fid,m['id'],'resolved','Different player',target_id=pool[1]['id'],confirmed=True)
    resolve_move(repo,fid,m['id'],'resolved','Apply audited target',confirmed=True)
    assert repo.get('players',pool[0]['id'])['area']=='dfa'


def test_trade_is_atomic_when_incoming_card_invalid(demo):
    repo,fid=demo;lose_twice(repo,fid)
    f=repo.get('franchises',fid);f['state']=State.MOVES;repo.put('franchises',f)
    target=target_pool(repo,fid)[0]
    m=dict(id=uid(),franchise_id=fid,run_id=f['current_run'],type='trade',target=target['id'],status='pending',critical=True,description='Trade',source='wheel',constraints={})
    repo.put('moves',m)
    with pytest.raises(RuleError):resolve_move(repo,fid,m['id'],'resolved','Bad incoming card',new_player={'name':''},confirmed=True)
    assert repo.get('players',target['id'])['area']==target['area']
    assert repo.get('moves',m['id'])['status']=='pending'
