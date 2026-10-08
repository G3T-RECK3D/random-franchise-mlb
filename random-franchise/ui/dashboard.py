import streamlit as st
from models.domain import State
from services.game_engine import start_run
from services.franchise_service import settings
from ui.common import navigate,table,badges

def render(repo,f):
    fid=f['id'];run=repo.get('runs',f['current_run']) if f['current_run'] else None
    games=repo.list('games',fid)
    a,b,c,d=st.columns(4)
    a.metric('Run record',f"{run['wins']}–{run['losses']}" if run else 'Not started')
    b.metric('Franchise record',f"{sum(g['result']=='W' for g in games)}–{sum(g['result']=='L' for g in games)}")
    pending=[m for m in repo.list('moves',fid) if m['status'] in ['pending','deferred']]
    c.metric('📦 Next-run moves',len(pending))
    threshold=next((n for n in sorted(int(x) for x in settings(repo,fid)['milestones']) if not run or n>run['wins']),None)
    d.metric('Next milestone',f'{threshold} wins' if threshold else 'All earned')
    if f['state']==State.ACTIVE:navigate('▶ Enter Next Game','Game Entry')
    elif f['state']==State.WHEEL:navigate('🎡 Spin required wheel','Wheel Room')
    elif f['state'] in [State.SETUP,State.READY]:
        navigate('Build / inspect roster','Roster Manager')
        if st.button('Validate and start next run',type='primary'):
            start_run(repo,fid);st.rerun()
    else:navigate('Continue offseason','Offseason')
    st.subheader('Franchise status')
    table([{'Player':p['name'],'Status':badges(repo,fid,p)} for p in repo.list('players',fid) if badges(repo,fid,p)])
    st.subheader('Active challenges')
    table([{'Player':repo.get('players',c['player_id'])['name'],'Challenge':c['description'],'Status':c['status']} for c in repo.list('challenges',fid) if c['status'] in ['active','awaiting_manual']])
    st.subheader('📦 Next Run Moves')
    table([{'Move':m['description'],'Type':m['type'],'Status':m['status']} for m in pending[:8]])
    spins=repo.list('spins',fid)
    if spins:st.info('Latest wheel: '+spins[-1]['result']['text'])
