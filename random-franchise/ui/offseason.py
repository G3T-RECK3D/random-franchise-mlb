import streamlit as st
from models.domain import State
from services.offseason_service import confirm_end,select_mvp,progress,finish_validation
from services.game_engine import start_run
from services.roster_validator import validate
from services.challenge_service import confirm_manual
from ui.common import navigate,table

def render(repo,f):
    fid=f['id'];state=f['state']
    if state==State.ACTIVE:st.info('Your Event entry is still active. Offseason begins only when the loss limit is reached.');return
    if state==State.WHEEL:navigate('Spin the required wheel','Wheel Room');return
    if state==State.ENDED:
        run=repo.get('runs',f['current_run'])
        st.write(f"Final record: **{run['wins']}–{run['losses']}**")
        if st.button('Confirm ended run and select MVP',type='primary'):confirm_end(repo,fid);st.rerun()
    elif state==State.MVP:
        run=repo.get('runs',f['current_run']);ids=run['roster_ids']
        labels={i:repo.get('players',i)['name'] for i in ids}
        pid=st.selectbox('Run MVP',ids,format_func=labels.get)
        st.caption('MVP receives temporary protection through this offseason’s elimination cycle.')
        if st.button('Confirm MVP and spin reward',type='primary'):select_mvp(repo,fid,pid);st.rerun()
    elif state in [State.ELIMINATION,State.MELTDOWN]:
        st.write('Next: elimination' if state==State.ELIMINATION else 'Next: check configured 0–2 Meltdown')
        if st.button('Continue offseason',type='primary'):progress(repo,fid);st.rerun()
    elif state==State.MOVES:
        st.write('Resolve consequences first, then rewards. Optional acquisitions can remain deferred for a later Event.')
        navigate('Resolve banked moves','Banked Moves')
        manual=[c for c in repo.list('challenges',fid) if c['status']=='awaiting_manual']
        for c in manual:
            with st.form('challenge:'+c['id']):
                st.write(repo.get('players',c['player_id'])['name']+' — '+c['description'])
                passed=st.checkbox('Challenge passed')
                evidence=st.text_input('Evidence / what happened')
                if st.form_submit_button('Confirm challenge result'):confirm_manual(repo,fid,c['id'],passed,evidence);st.rerun()
        if st.button('Proceed to roster reconstruction',type='primary'):progress(repo,fid);st.rerun()
    elif state==State.REBUILD:
        navigate('Rebuild roster','Roster Manager')
        if st.button('Proceed to validation',type='primary'):progress(repo,fid);st.rerun()
    elif state==State.VALIDATION:
        result=validate(repo,fid)
        if result.valid:
            st.success('Roster checks pass. Confirm in-game Event eligibility as well.')
            if st.button('Approve roster for next run',type='primary'):finish_validation(repo,fid);st.rerun()
        else:
            for error in result.errors:st.warning(error)
            navigate('Fix roster assignments','Roster Manager')
            navigate('Resolve outstanding moves','Banked Moves')
    elif state in [State.SETUP,State.READY]:
        navigate('Review roster','Roster Manager')
        if st.button('Start next Event run at 0–0',type='primary'):start_run(repo,fid);st.rerun()
