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
        from services.stat_engine import aggregate

        st.subheader('🏆 Run MVP candidates')
        st.caption(
            'Custom contribution points from this run’s saved stats—not WAR. '
            'Compare hitters and pitchers separately; the final choice is yours.'
        )

        hitters = []
        pitchers = []

        for player_id in ids:
            player = repo.get('players', player_id)
            if not player:
                continue

            totals = aggregate(repo, fid, player, run['id'])
            if not totals.get('games', 0):
                continue

            if player['kind'] == 'hitter':
                total_bases = (
                    totals.get('h', 0)
                    + totals.get('doubles', 0)
                    + 2 * totals.get('triples', 0)
                    + 3 * totals.get('hr', 0)
                )
                score = (
                    total_bases
                    + totals.get('bb', 0)
                    + totals.get('hbp', 0)
                    + totals.get('r', 0)
                    + totals.get('rbi', 0)
                    + totals.get('sb', 0)
                    - totals.get('cs', 0)
                )
                hitters.append({
                    'Player': player['name'],
                    'Run Value': score,
                    'PA': totals.get('pa', 0),
                    'H': totals.get('h', 0),
                    'HR': totals.get('hr', 0),
                    'RBI': totals.get('rbi', 0),
                    'Runs': totals.get('r', 0),
                    'OPS': f"{totals.get('ops', 0):.3f}",
                })
            else:
                outs = totals.get('outs', 0)
                score = (
                    outs
                    + totals.get('so', 0)
                    - 3 * totals.get('er', 0)
                    - totals.get('ha', 0)
                    - totals.get('bb', 0)
                )
                pitchers.append({
                    'Player': player['name'],
                    'Run Value': score,
                    'IP': f"{int(outs) // 3}.{int(outs) % 3}",
                    'K': totals.get('so', 0),
                    'ER': totals.get('er', 0),
                    'Hits allowed': totals.get('ha', 0),
                    'Walks': totals.get('bb', 0),
                })

        hitters.sort(key=lambda row: row['Run Value'], reverse=True)
        pitchers.sort(key=lambda row: row['Run Value'], reverse=True)

        st.markdown('**Top hitters**')
        table(hitters[:3])
        st.markdown('**Top pitchers**')
        table(pitchers[:3])

        with st.expander('How Run Value is calculated'):
            st.write(
                'Hitters: total bases + walks + hit-by-pitch '
                '+ runs + RBI + steals − caught stealing.'
            )
            st.write(
                'Pitchers: outs + strikeouts − (3 × earned runs) '
                '− hits allowed − walks allowed.'
            )
            st.caption(
                'These are starting weights. The two lists are not calibrated '
                'to determine whether a hitter or pitcher deserves MVP.'
            )
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
