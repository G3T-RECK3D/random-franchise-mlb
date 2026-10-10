import json
import math
import streamlit as st
from services.franchise_service import settings,save_settings,audit
from services.roster_service import locked
from models.domain import RuleError
from ui.game_entry import correction

def render(repo,f):
    fid=f['id'];cfg=settings(repo,fid)
    with st.expander('Restore previous Event seasons'):
        from services.franchise_service import setup_recovered_seasons

        st.write('Selected franchise: **' + f['name'] + '**')
        st.write('Season 1: 2026 Wildcard Series Event — completed')
        st.write('Season 2: 2026 Division Series Event — current')

        if not repo.list('runs', fid) and not repo.list('games', fid):
            if st.button(
                'Set up these two seasons',
                key='recover_seasons:' + fid,
            ):
                setup_recovered_seasons(repo, fid)
                st.rerun()
        else:
            st.info('Recovery setup is available before adding weeks or games.')

        for season in sorted(
            repo.list('seasons', fid),
            key=lambda item: item['number'],
        ):
            st.write(
                f"Season {season['number']}: {season['name']}"
                f" — {season['status']}"
            )
    st.subheader('Back up your complete app data')
    st.caption('This backup contains all franchises, games, stats, wheels, and audits. Local cloud disk is temporary. Download after each session; restore with the documented database command.')
    st.download_button('Download full SQLite backup',repo.backup_bytes(),'random_franchise_backup.db','application/octet-stream')
    if locked(repo,fid):st.info('Rules and wheel settings are editable between runs. Game/stat corrections remain available below.')
    else:
        with st.form('settings'):
            st.subheader('Challenge and Event rules')
            st.caption('Edit the JSON fields: loss limit, milestones, tag cap, meltdown, roster sizes, optional average OVR cap, Event restrictions, dates, cooldown, and special wheel availability.')
            text=st.text_area('Settings JSON',value=json.dumps(cfg,indent=2),height=420)
            if st.form_submit_button('Save rules'):
                try:values=json.loads(text)
                except ValueError:raise RuleError('Invalid settings JSON.')
                save_settings(repo,fid,values);st.rerun()
        wheels=repo.list('wheels',fid)
        labels={w['id']:w['display_name'] for w in wheels}
        wid=st.selectbox('Wheel to edit',list(labels),format_func=labels.get)
        wheel=repo.get('wheels',wid)
        with st.form('wheel:'+wid):
            text=st.text_area('Wedges JSON (weights, active flags, effects, eligibility, follow-up wheel)',value=json.dumps(wheel['wedges'],indent=2),height=420)
            if st.form_submit_button('Save wheel configuration'):
                try:wedges=json.loads(text)
                except ValueError:raise RuleError('Invalid wheel JSON.')
                if not isinstance(wedges,list) or not wedges or len({w.get('id') for w in wedges})!=len(wedges):
                    raise RuleError('Wedges need distinct IDs and a nonempty list.')
                valid_wheels={w['wheel_id'] for w in wheels}
                effects={'acquire','dfa','demote','trade','review','none','protect','unprotect','hot_seat','arrangement','challenge','tag','extra_spin','call_up','cancel_elimination','save_dfa'}
                for w in wedges:
                    if not isinstance(w.get('text'),str) or not isinstance(w.get('weight'),(int,float)) or not math.isfinite(w['weight']) or w['weight']<0 or w.get('effect') not in effects:
                        raise RuleError('Every wedge needs text, a nonnegative numeric weight, and a supported effect.')
                    if w.get('follow_up') and w['follow_up'] not in valid_wheels:raise RuleError('Unknown follow-up wheel.')
                    if not isinstance(w.get('quantity',1),int) or not 1<=w.get('quantity',1)<=4:raise RuleError('Quantity must be an integer 1–4.')
                if not any(w.get('active',True) and w['weight']>0 for w in wedges):raise RuleError('Keep at least one active weighted wedge.')
                with repo.transaction():
                    before=dict(wheel);wheel['wedges']=wedges;repo.put('wheels',wheel)
                    audit(repo,fid,'wheel_configuration',before,wheel,'Wheel editor')
                st.rerun()
    with st.expander('Administrative corrections'):correction(repo,f)
    with st.expander('Delete an empty test franchise'):
        history_tables = [
            'players', 'runs', 'games', 'stats', 'spins', 'moves',
            'rewards', 'challenges', 'snapshots', 'corrections', 'tags',
        ]
        candidates = [
            franchise
            for franchise in repo.list('franchises')
            if franchise['id'] != fid
            and franchise['name'].strip().casefold().startswith('test')
            and not any(
                repo.list(table_name, franchise['id'])
                for table_name in history_tables
            )
        ]

        if not candidates:
            st.info('No other empty test franchises are available to delete.')
        else:
            choices = {item['id']: item for item in candidates}
            delete_id = st.selectbox(
                'Empty test franchise to delete',
                list(choices),
                format_func=lambda identifier: (
                    choices[identifier]['name']
                    + ' · ' + choices[identifier].get('event', '')
                    + ' · ID ending ' + identifier[-6:]
                ),
                key='delete_empty_test_target',
            )
            confirmed = st.checkbox(
                'Permanently delete this empty test franchise.',
                key='delete_empty_test_confirm',
            )
            if st.button('Delete empty test franchise', disabled=not confirmed):
                with repo.transaction():
                    selected = repo.get('franchises', delete_id)
                    if (
                        not selected
                        or delete_id == fid
                        or not selected['name'].strip().casefold().startswith('test')
                        or any(
                            repo.list(table_name, delete_id)
                            for table_name in history_tables
                        )
                    ):
                        raise RuleError('Only another empty test franchise can be deleted.')

                    for table_name in ['wheels', 'settings']:
                        for row in repo.list(table_name, delete_id):
                            repo.delete(table_name, row['id'])
                    repo.delete('franchises', delete_id)
                st.rerun()
