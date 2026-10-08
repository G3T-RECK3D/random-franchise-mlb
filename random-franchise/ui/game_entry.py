from datetime import date
import streamlit as st
from models.domain import State,uid
from services.game_engine import record_game,correct_game
from ui.forms import stat_fields
from ui.common import navigate

def render(repo,f):
    fid=f['id'];run=repo.get('runs',f['current_run']) if f['current_run'] else None
    if f['state']!=State.ACTIVE or not run:
        st.info('Game entry is locked. Finish the current wheel or offseason action.')
        navigate('Open required wheel','Wheel Room') if f['state']==State.WHEEL else navigate('Open offseason','Offseason')
        return
    key='draft:'+run['id']
    if key not in st.session_state:
        with st.form('game_entry'):
            a,b,c=st.columns(3)
            result=a.selectbox('Result',['W','L'])
            opponent=b.text_input('Opponent (optional)')
            played=c.date_input('Game date',value=date.today())
            include=st.checkbox('Include scores')
            a,b=st.columns(2)
            own=a.number_input('Your score',0,99,0)
            opp=b.number_input('Opponent score',0,99,0)
            notes=st.text_area('Game notes')
            lines=stat_fields(repo,fid,run['roster_ids'],'entry:'+run['id'])
            if st.form_submit_button('Review game',type='primary'):
                st.session_state[key]=dict(request_id=uid(),result=result,opponent=opponent,date=str(played),
                    team_score=int(own) if include else None,opponent_score=int(opp) if include else None,notes=notes,lines=lines)
                st.rerun()
    else:
        draft=st.session_state[key]
        st.subheader('Review before saving')
        st.write({k:v for k,v in draft.items() if k not in ['request_id','lines']})
        st.write(f"{len(draft['lines'])} player stat lines")
        for row in draft['lines']:
            st.write(repo.get('players',row['player_id'])['name'],row['line'])
        a,b=st.columns(2)
        if a.button('Confirm and save once',type='primary'):
            record_game(repo,fid,**draft)
            del st.session_state[key]
            st.session_state['last_saved_game']=draft['request_id']
            st.rerun()
        if b.button('Discard draft'):
            del st.session_state[key];st.rerun()
    if st.session_state.get('last_saved_game'):
        st.success('Game saved. Your record and stats have been updated.')
        navigate('Return to dashboard','Dashboard')


def correction(repo,f):
    games=repo.list('games',f['id'])
    if not games:return
    st.subheader('Administrative game / stats correction')
    labels={g['id']:f"Run {repo.get('runs',g['run_id'])['number']} · Game {g['number']} · {g['result']}" for g in games}
    gid=st.selectbox('Game',list(labels),format_func=labels.get)
    game=repo.get('games',gid);run=repo.get('runs',game['run_id'])
    st.caption('Stats corrections are always audited. Outcome edits are allowed only for the latest current-run game before dependent wheels or offseason actions.')
    with st.form('correct:'+gid):
        outcome=st.selectbox('Corrected result',['W','L'],index=0 if game['result']=='W' else 1)
        lines=stat_fields(repo,f['id'],run['roster_ids'],'correct:'+gid,[s for s in repo.list('stats',f['id'],run['id']) if s['game_id']==gid])
        reason=st.text_input('Correction reason (required)')
        confirmed=st.checkbox('I confirm replacement of this game’s stat lines.')
        if st.form_submit_button('Apply audited correction') and confirmed:
            correct_game(repo,f['id'],gid,lines,reason,outcome);st.rerun()
