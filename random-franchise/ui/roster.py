import json
import streamlit as st
from models.domain import AREAS,POSITIONS
from services.roster_service import locked,add_player,arrange,swap,remove_player
from services.import_export import export_roster,import_roster
from services.roster_validator import validate
from services.franchise_service import audit
from ui.common import table,badges
from ui.forms import player_fields

def render(repo,f):
    fid=f['id'];players=repo.list('players',fid)
    is_locked=locked(repo,fid)
    if is_locked:st.info('Active run: lineup, bench, positions, rotation, and bullpen arrangements are available. New cards, call-ups, and removals wait until offseason.')
    with st.expander('⚾ Set batting order', expanded=False):
        import pandas as pd

        lineup = sorted(
            [
                p for p in players
                if p['area'] == 'lineup' and p['kind'] == 'hitter'
            ],
            key=lambda p: (p['order'], p['name'], p['id']),
        )

        st.caption(
            'Change the Order numbers, then save once. '
            'Use each number from 1–9 exactly once. '
            'Set your order before entering the next game’s stats.'
        )

        if len(lineup) != 9:
            st.info('You need nine lineup hitters to set the batting order.')
        else:
            with st.form('set_batting_order'):
                edited_order = st.data_editor(
                    pd.DataFrame([
                        {
                            'player_id': p['id'],
                            'Player': p['name'],
                            'Position': p['position'],
                            'Order': p['order'],
                        }
                        for p in lineup
                    ]),
                    hide_index=True,
                    use_container_width=True,
                    num_rows='fixed',
                    disabled=['player_id', 'Player', 'Position'],
                    column_config={
                        'player_id': None,
                        'Order': st.column_config.NumberColumn(
                            'Order',
                            min_value=1,
                            max_value=9,
                            step=1,
                            required=True,
                        ),
                    },
                    key='batting_order_editor',
                )

                if st.form_submit_button(
                    'Save batting order',
                    type='primary',
                ):
                    rows = edited_order.to_dict('records')
                    orders = [row['Order'] for row in rows]

                    if sorted(
                        value for value in orders if pd.notna(value)
                    ) != list(range(1, 10)):
                        st.error('Use each batting-order number 1–9 exactly once.')
                    else:
                        with repo.transaction():
                            for row in rows:
                                player = repo.get('players', row['player_id'])
                                arrange(
                                    repo,
                                    fid,
                                    player['id'],
                                    'lineup',
                                    player['position'],
                                    int(row['Order']),
                                )
                        st.rerun()
    if is_locked:
        with st.expander('Admin: correct starting roster'):
            from models.domain import RuleError
            from services.roster_validator import legal_positions

            run = repo.get('runs', f['current_run'])
            games = repo.list('games', fid, run['id'])

            if games:
                st.info('This correction is available only before the first saved game.')
            else:
                active = [
                    p for p in players
                    if p['area'] in ['lineup', 'bench', 'rotation', 'bullpen']
                ]
                minors = [p for p in players if p['area'] == 'minors']
                choices = {p['id']: p for p in players}

                if not active or not minors:
                    st.info('You need an active player and a Minors player to swap.')
                else:
                    with st.form('correct_starting_roster'):
                        outgoing_id = st.selectbox(
                            'Incorrectly listed active player',
                            [p['id'] for p in active],
                            format_func=lambda pid: (
                                choices[pid]['name'] + ' · ' + choices[pid]['area']
                            ),
                        )
                        incoming_id = st.selectbox(
                            'Player actually on your in-game roster',
                            [p['id'] for p in minors],
                            format_func=lambda pid: choices[pid]['name'],
                        )
                        reason = st.text_input('Correction reason')
                        confirmed = st.checkbox(
                            'This corrects the roster used when this run started.'
                        )

                        if st.form_submit_button('Apply starting-roster correction'):
                            try:
                                with repo.transaction():
                                    current_f = repo.get('franchises', fid)
                                    current_run = repo.get('runs', current_f['current_run'])
                                    if current_run['id'] != run['id']:
                                        raise RuleError('The current run changed. Reload this page.')
                                    if current_run.get('ended_at') or repo.list('games', fid, run['id']):
                                        raise RuleError('Only available before the first saved game.')
                                    if not confirmed or not reason.strip():
                                        raise RuleError('Enter a reason and confirm the correction.')

                                    outgoing = repo.get('players', outgoing_id)
                                    incoming = repo.get('players', incoming_id)
                                    if (
                                        outgoing['franchise_id'] != fid
                                        or incoming['franchise_id'] != fid
                                        or outgoing['area'] not in ['lineup', 'bench', 'rotation', 'bullpen']
                                        or incoming['area'] != 'minors'
                                        or outgoing_id not in current_run['roster_ids']
                                        or incoming_id in current_run['roster_ids']
                                    ):
                                        raise RuleError('The selected roster assignments changed.')
                                    if incoming['kind'] != outgoing['kind']:
                                        raise RuleError('Both players must be the same type.')
                                    if outgoing['position'] not in legal_positions(incoming):
                                        raise RuleError('The incoming player cannot fill that position.')
                                    if incoming.get('eligibility') != 'legal':
                                        raise RuleError('Verify the incoming card is Event-legal first.')

                                    references = [current_f.get('queue', [])]
                                    for table_name in ['spins', 'moves', 'challenges']:
                                        references.extend(repo.list(table_name, fid, run['id']))
                                    if any(
                                        outgoing_id in json.dumps(item)
                                        or incoming_id in json.dumps(item)
                                        for item in references
                                    ):
                                        raise RuleError('A current-run wheel or challenge references these players.')

                                    if any(
                                        prefix + run['id'] in st.session_state
                                        for prefix in ['draft:', 'paste_import:']
                                    ):
                                        raise RuleError('Discard the unsaved game draft first.')

                                    before = {
                                        'outgoing': dict(outgoing),
                                        'incoming': dict(incoming),
                                        'roster_ids': list(current_run['roster_ids']),
                                    }
                                    assignment = (
                                        outgoing['area'],
                                        outgoing['position'],
                                        outgoing['order'],
                                    )
                                    outgoing.update(
                                        area='minors',
                                        position=incoming['position'],
                                        order=incoming['order'],
                                    )
                                    incoming.update(
                                        area=assignment[0],
                                        position=assignment[1],
                                        order=assignment[2],
                                    )
                                    current_run['roster_ids'] = [
                                        incoming_id if pid == outgoing_id else pid
                                        for pid in current_run['roster_ids']
                                    ]
                                    repo.put('players', outgoing)
                                    repo.put('players', incoming)
                                    repo.put('runs', current_run)
                                    audit(
                                        repo, fid, 'starting_roster_correction',
                                        before,
                                        {
                                            'outgoing': outgoing,
                                            'incoming': incoming,
                                            'roster_ids': current_run['roster_ids'],
                                        },
                                        reason.strip(),
                                        run['id'],
                                    )
                            except RuleError as exc:
                                st.error(str(exc))
                            else:
                                st.rerun()
    for area in AREAS:
        with st.expander(area.title(),expanded=area in ['lineup','bench']):
            table([{'Player':p['name'],'Card':p['version'],'OVR':p['ovr'],'Position':p['position'],'Order':p['order'],
                    'Eligibility':p['eligibility'],'Status':badges(repo,fid,p)} for p in sorted(players,key=lambda p:p['order']) if p['area']==area])
    if players:
        ids=[p['id'] for p in players];labels={p['id']:p['name']+' · '+p['area'] for p in players}
        with st.form('arrange'):
            st.subheader('Arrange one player')
            pid=st.selectbox('Player',ids,format_func=labels.get)
            a,b,c=st.columns(3)
            area=a.selectbox('Destination area',AREAS[:-1])
            pos=b.selectbox('Assigned position',POSITIONS)
            order=c.number_input('Batting order / role priority',1,30,1)
            if st.form_submit_button('Save arrangement'):
                arrange(repo,fid,pid,area,pos,int(order));st.rerun()
        with st.form('swap'):
            st.subheader('Swap two assignments')
            first=st.selectbox('First player',ids,format_func=labels.get)
            second=st.selectbox('Second player',ids,format_func=labels.get)
            st.caption('Both destination positions must be legal. Use this for starter/bench swaps and order changes.')
            if st.form_submit_button('Swap assignments'):
                swap(repo,fid,first,second);st.rerun()
        with st.form('eligibility'):
            st.subheader('Update Event eligibility and notes')
            pid=st.selectbox('Card to verify',ids,format_func=labels.get)
            value=st.selectbox('Eligibility',['legal','illegal','unknown'])
            note=st.text_input('Verification note')
            if st.form_submit_button('Update eligibility'):
                with repo.transaction():
                    p=repo.get('players',pid);before=dict(p);p.update(eligibility=value,notes=note)
                    repo.put('players',p);audit(repo,fid,'eligibility',before,p,note or 'Manual eligibility check')
                st.rerun()
    if not is_locked:
        with st.expander('Add a card'):
            with st.form('new_player'):
                data=player_fields('new_')
                if st.form_submit_button('Add card'):
                    add_player(repo,fid,data);st.rerun()
        if players:
            with st.form('remove'):
                st.subheader('DFA / demote')
                pid=st.selectbox('Removal target',ids,format_func=labels.get)
                destination=st.selectbox('Destination',['dfa','minors'])
                confirm=st.checkbox('I confirm this offseason removal.')
                if st.form_submit_button('Apply removal') and confirm:
                    remove_player(repo,fid,pid,destination);st.rerun()
        upload=st.file_uploader('Import additional cards (CSV / JSON)',type=['csv','json'])
        confirmed=st.checkbox('Import appends cards; I have checked for duplicates.')
        if upload and confirmed and st.button('Import cards'):
            import_roster(repo,fid,upload.getvalue().decode('utf-8-sig'),upload.name.rsplit('.',1)[-1]);st.rerun()
    with st.expander('Delete accidental duplicate permanently'):
        from models.domain import RuleError

        saved_stats = repo.list('stats', fid)
        used_ids = {s['player_id'] for s in saved_stats}

        gp = {}
        saved_lines = {}
        for row in saved_stats:
            pid = row['player_id']
            gp[pid] = gp.get(pid, 0) + row['line'].get('games', 0)
            saved_lines[pid] = saved_lines.get(pid, 0) + 1

        st.caption('Compare DFA entries below. GP includes all runs.')
        table([
            {
                'Player': p['name'],
                'Card': p['version'],
                'OVR': p['ovr'],
                'GP': gp.get(p['id'], 0),
                'Saved stat lines': saved_lines.get(p['id'], 0),
                'Player ID': p['id'],
            }
            for p in players
            if p['area'] in ['dfa', 'minors']
        ])
        duplicates = [
            p for p in players
            if p['area'] in ['dfa', 'minors'] and p['id'] not in used_ids
        ]
        if not duplicates:
            st.info('No DFA players without saved stats are available to delete.')
        else:
            choices = {p['id']: p for p in duplicates}
            duplicate_id = st.selectbox(
                'Unused DFA entry to delete',
                list(choices),
                format_func=lambda pid: (
                    f"{choices[pid]['name']} · {choices[pid]['version']} "
                    f"· OVR {choices[pid]['ovr']} · ID {pid}"
                ),
                key='delete_duplicate_target',
            )
            confirmed = st.checkbox(
                'This is an accidental duplicate. Permanently delete this entry.',
                key='delete_duplicate_confirm',
            )
            if st.button('Delete unused duplicate', disabled=not confirmed):
                try:
                    with repo.transaction():
                        player = repo.get('players', duplicate_id)
                        if not player or player['franchise_id'] != fid or player['area'] not in ['dfa', 'minors']:
                            raise RuleError('Choose an unused DFA or Minors entry.')
                        if any(s['player_id'] == duplicate_id for s in repo.list('stats', fid)):
                            raise RuleError('This entry has saved stats and cannot be deleted.')
                        runs = repo.list('runs', fid)
                        if any(
                            prefix + run['id'] in st.session_state
                            for run in runs
                            for prefix in ['draft:', 'paste_import:']
                        ):
                            raise RuleError('Finish or discard your unsaved game draft first.')
                        if player.get('protected') or any(run.get('mvp') == duplicate_id for run in runs):
                            raise RuleError('This entry is protected or has an MVP record.')
                        references = [repo.get('franchises', fid).get('queue', [])]
                        for table_name in ['tags', 'challenges', 'spins', 'moves', 'rewards', 'wheels']:
                            references.extend(repo.list(table_name, fid))
                        if any(duplicate_id in json.dumps(item) for item in references):
                            raise RuleError('This entry is referenced by a wheel, tag, or challenge and cannot be deleted here.')
                        for run in runs:
                            if duplicate_id in run['roster_ids']:
                                run['roster_ids'] = [pid for pid in run['roster_ids'] if pid != duplicate_id]
                                repo.put('runs', run)
                        audit(repo, fid, 'delete_unused_duplicate', player, None,
                              'Permanently remove accidental DFA duplicate with no saved stats')
                        repo.delete('players', duplicate_id)
                except RuleError as exc:
                    st.error(str(exc))
                else:
                    st.rerun()
    a,b=st.columns(2)
    a.download_button('Export roster JSON',export_roster(repo,fid),'roster.json','application/json')
    b.download_button('Export roster CSV',export_roster(repo,fid,'csv'),'roster.csv','text/csv')
    st.subheader('Roster check')
    result=validate(repo,fid)
    if result.valid:st.success('Roster composition and configured eligibility checks pass.')
    else:
        for error in result.errors:st.warning(error)
