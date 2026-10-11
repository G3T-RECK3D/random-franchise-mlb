import json
import streamlit as st
from models.domain import AREAS, POSITIONS, RuleError, State
from services.roster_service import locked, add_player, arrange, swap, remove_player
from services.import_export import export_roster, import_roster
from services.roster_validator import validate
from services.franchise_service import audit
from ui.common import table, badges
from ui.forms import player_fields


def apply_complete_roster(repo, fid, cards, outgoing_area):
    """Reuse player IDs and replace active assignments in one transaction."""
    from services.roster_service import protected
    from services.roster_validator import legal_positions
    import unicodedata

    def name_key(value):
        text = unicodedata.normalize('NFD', value.strip().casefold())
        return ''.join(
            ch for ch in text if not unicodedata.combining(ch)
        )

    if not isinstance(cards, list) or not cards:
        raise RuleError('Upload a JSON list of player cards.')

    if outgoing_area not in ['minors', 'dfa']:
        raise RuleError('Select Minors or DFA for outgoing cards.')

    with repo.transaction():
        f = repo.get('franchises', fid)

        if locked(repo, fid):
            raise RuleError(
                'Finish the active week before applying a complete roster.'
            )

        allowed_states = [
            State.SETUP,
            State.READY,
            State.REBUILD,
            State.VALIDATION,
        ]
        if f.get('queue') or f['state'] not in allowed_states:
            raise RuleError(
                'Finish required wheels and banked moves before '
                'applying a complete roster.'
            )

        before = repo.list('players', fid)
        plan = []
        identities = set()
        used_existing = set()

        for card in cards:
            if not isinstance(card, dict):
                raise RuleError('Every card must be a JSON object.')

            if (
                not isinstance(card.get('name'), str)
                or not card['name'].strip()
            ):
                raise RuleError('Every card needs a player name.')

            if (
                not isinstance(card.get('card_uuid'), str)
                or not card['card_uuid'].strip()
            ):
                raise RuleError(
                    'Every card needs its verified card_uuid '
                    'for duplicate-safe matching.'
                )

            if card.get('kind') not in ['hitter', 'pitcher']:
                raise RuleError(
                    'Every card needs a valid hitter/pitcher kind.'
                )

            identity = (card['card_uuid'], card['kind'])
            if identity in identities:
                raise RuleError(
                    'The JSON contains the same card twice: '
                    + card['name']
                )
            identities.add(identity)

            if (
                type(card.get('ovr')) is not int
                or not 0 <= card['ovr'] <= 99
            ):
                raise RuleError(
                    'Every card needs an integer OVR from 0 to 99.'
                )

            if (
                card.get('primary') not in POSITIONS
                or not isinstance(card.get('secondary'), list)
                or any(
                    position not in POSITIONS
                    for position in card['secondary']
                )
            ):
                raise RuleError(
                    'Invalid primary/secondary positions for '
                    + card['name']
                )

            area = card.get('area')
            if area not in ['lineup', 'bench', 'rotation', 'bullpen']:
                raise RuleError(
                    'A complete roster contains only active roster areas.'
                )

            if (
                type(card.get('order')) is not int
                or not 1 <= card['order'] <= 30
            ):
                raise RuleError(
                    'Use positive integer order numbers from 1 to 30.'
                )

            if card.get('position') not in POSITIONS:
                raise RuleError(
                    'Invalid assigned position for ' + card['name']
                )

            if card.get('eligibility') != 'legal':
                raise RuleError(
                    'Verify Event eligibility for every card before applying.'
                )

            if (
                area in ['lineup', 'bench']
                and card['kind'] != 'hitter'
            ):
                raise RuleError(
                    'Lineup and bench entries must be hitters.'
                )

            if area == 'lineup' and (
                card['position'] not in legal_positions(card)
                or not 1 <= card['order'] <= 9
            ):
                raise RuleError(
                    'Illegal lineup position/order for ' + card['name']
                )

            if area in ['rotation', 'bullpen']:
                role = 'SP' if area == 'rotation' else 'RP'
                if (
                    card['kind'] != 'pitcher'
                    or card['position'] != role
                    or role not in legal_positions(card)
                ):
                    raise RuleError(
                        'Illegal pitching role for ' + card['name']
                    )

            matches = [
                player for player in before
                if player.get('card_uuid') == card['card_uuid']
                and player['kind'] == card['kind']
            ]

            if len(matches) > 1:
                raise RuleError(
                    'Multiple existing entries match '
                    + card['name']
                    + '. Resolve the duplicate first; no changes were saved.'
                )

            if matches:
                player = matches[0]
                if (
                    name_key(player['name']) != name_key(card['name'])
                    or player['ovr'] != card['ovr']
                ):
                    raise RuleError(
                        'Existing card identity disagrees with the JSON: '
                        + card['name']
                    )
            else:
                legacy = [
                    player for player in before
                    if not player.get('card_uuid')
                    and name_key(player['name']) == name_key(card['name'])
                    and player['kind'] == card['kind']
                    and player['ovr'] == card['ovr']
                ]

                if len(legacy) > 1:
                    raise RuleError(
                        'Multiple older entries match '
                        + card['name']
                        + '. Resolve the duplicate first.'
                    )

                player = legacy[0] if legacy else None
                if (
                    player
                    and player.get('series')
                    and player['series'].strip().casefold()
                    != str(card.get('series', '')).strip().casefold()
                ):
                    raise RuleError(
                        'Confirm the older card series for '
                        + card['name']
                        + ' before importing.'
                    )

            if player:
                if player['id'] in used_existing:
                    raise RuleError(
                        'Two incoming cards matched the same existing player.'
                    )
                used_existing.add(player['id'])

            plan.append((card, player))

        lineup = [
            card for card in cards if card['area'] == 'lineup'
        ]

        if (
            len(lineup) != 9
            or sorted(card['order'] for card in lineup)
            != list(range(1, 10))
        ):
            raise RuleError(
                'Include nine lineup hitters with each '
                'order number 1–9 exactly once.'
            )

        if len({card['position'] for card in lineup}) != 9:
            raise RuleError('Lineup positions must be distinct.')

        outgoing = [
            player for player in before
            if player['area'] in ['lineup', 'bench', 'rotation', 'bullpen']
            and player['id'] not in used_existing
        ]

        for player in outgoing:
            if protected(repo, fid, player):
                raise RuleError(
                    'The JSON omits protected player '
                    + player['name']
                    + '. Include the player or resolve their protection first.'
                )

        fields = [
            'name',
            'version',
            'ovr',
            'primary',
            'secondary',
            'kind',
            'team',
            'series',
            'bat',
            'throw',
            'eligibility',
            'card_uuid',
            'card_image_url',
        ]

        for card, existing in plan:
            if existing:
                player = dict(existing)
                player.update({
                    key: card[key] for key in fields if key in card
                })
                player['historical_only'] = False
                repo.put('players', player)
                pid = player['id']
            else:
                data = {
                    key: card[key] for key in fields if key in card
                }
                data.update(
                    area='minors',
                    position=card['primary'],
                    order=card['order'],
                    historical_only=False,
                )
                pid = add_player(repo, fid, data)

            arrange(
                repo,
                fid,
                pid,
                card['area'],
                card['position'],
                card['order'],
            )

        for player in outgoing:
            remove_player(repo, fid, player['id'], outgoing_area)

        result = validate(repo, fid, check_tasks=False)
        if not result.valid:
            raise RuleError(
                'Roster checks failed; nothing changed: '
                + '; '.join(result.errors)
            )

        audit(
            repo,
            fid,
            'apply_complete_roster',
            before,
            repo.list('players', fid),
            'Apply complete roster JSON; reuse existing IDs, preserve '
            'saved stats, move omitted active cards to ' + outgoing_area,
        )

        return (
            sum(player is None for _, player in plan),
            len(used_existing),
            len(outgoing),
        )


def render(repo, f):
    fid = f['id']
    players = repo.list('players', fid)
    is_locked = locked(repo, fid)

    notice = st.session_state.pop(
        'complete_roster_notice:' + fid,
        None,
    )
    if notice:
        st.success(notice)

    if is_locked:
        st.info(
            'Active run: lineup, bench, positions, rotation, and bullpen '
            'arrangements are available. New cards, call-ups, and '
            'removals wait until offseason.'
        )

    with st.expander('⚾ Set batting order', expanded=False):
        import pandas as pd

        lineup = sorted(
            [
                player for player in players
                if player['area'] == 'lineup'
                and player['kind'] == 'hitter'
            ],
            key=lambda player: (
                player['order'],
                player['name'],
                player['id'],
            ),
        )

        st.caption(
            'Change the Order numbers, then save once. '
            'Use each number from 1–9 exactly once. '
            'Set your order before entering the next game’s stats.'
        )

        if len(lineup) != 9:
            st.info(
                'You need nine lineup hitters to set the batting order.'
            )
        else:
            with st.form('set_batting_order'):
                edited_order = st.data_editor(
                    pd.DataFrame([
                        {
                            'player_id': player['id'],
                            'Player': player['name'],
                            'Position': player['position'],
                            'Order': player['order'],
                        }
                        for player in lineup
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
                        st.error(
                            'Use each batting-order number 1–9 exactly once.'
                        )
                    else:
                        with repo.transaction():
                            for row in rows:
                                player = repo.get(
                                    'players',
                                    row['player_id'],
                                )
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
            from services.roster_validator import legal_positions

            run = repo.get('runs', f['current_run'])
            games = repo.list('games', fid, run['id'])

            if games:
                st.info(
                    'This correction is available only '
                    'before the first saved game.'
                )
            else:
                active = [
                    player for player in players
                    if player['area'] in [
                        'lineup', 'bench', 'rotation', 'bullpen'
                    ]
                ]
                minors = [
                    player for player in players
                    if player['area'] == 'minors'
                ]
                choices = {
                    player['id']: player for player in players
                }

                if not active or not minors:
                    st.info(
                        'You need an active player '
                        'and a Minors player to swap.'
                    )
                else:
                    with st.form('correct_starting_roster'):
                        outgoing_id = st.selectbox(
                            'Incorrectly listed active player',
                            [player['id'] for player in active],
                            format_func=lambda pid: (
                                choices[pid]['name']
                                + ' · '
                                + choices[pid]['area']
                            ),
                        )
                        incoming_id = st.selectbox(
                            'Player actually on your in-game roster',
                            [player['id'] for player in minors],
                            format_func=lambda pid: choices[pid]['name'],
                        )
                        reason = st.text_input('Correction reason')
                        confirmed = st.checkbox(
                            'This corrects the roster used '
                            'when this run started.'
                        )

                        if st.form_submit_button(
                            'Apply starting-roster correction'
                        ):
                            try:
                                with repo.transaction():
                                    current_f = repo.get('franchises', fid)
                                    current_run = repo.get(
                                        'runs',
                                        current_f['current_run'],
                                    )

                                    if current_run['id'] != run['id']:
                                        raise RuleError(
                                            'The current run changed. '
                                            'Reload this page.'
                                        )

                                    if (
                                        current_run.get('ended_at')
                                        or repo.list(
                                            'games', fid, run['id']
                                        )
                                    ):
                                        raise RuleError(
                                            'Only available before '
                                            'the first saved game.'
                                        )

                                    if not confirmed or not reason.strip():
                                        raise RuleError(
                                            'Enter a reason and '
                                            'confirm the correction.'
                                        )

                                    outgoing = repo.get(
                                        'players', outgoing_id
                                    )
                                    incoming = repo.get(
                                        'players', incoming_id
                                    )

                                    if (
                                        outgoing['franchise_id'] != fid
                                        or incoming['franchise_id'] != fid
                                        or outgoing['area'] not in [
                                            'lineup',
                                            'bench',
                                            'rotation',
                                            'bullpen',
                                        ]
                                        or incoming['area'] != 'minors'
                                        or outgoing_id
                                        not in current_run['roster_ids']
                                        or incoming_id
                                        in current_run['roster_ids']
                                    ):
                                        raise RuleError(
                                            'The selected roster '
                                            'assignments changed.'
                                        )

                                    if incoming['kind'] != outgoing['kind']:
                                        raise RuleError(
                                            'Both players must '
                                            'be the same type.'
                                        )

                                    if (
                                        outgoing['position']
                                        not in legal_positions(incoming)
                                    ):
                                        raise RuleError(
                                            'The incoming player cannot '
                                            'fill that position.'
                                        )

                                    if incoming.get('eligibility') != 'legal':
                                        raise RuleError(
                                            'Verify the incoming card '
                                            'is Event-legal first.'
                                        )

                                    references = [
                                        current_f.get('queue', [])
                                    ]
                                    for table_name in [
                                        'spins', 'moves', 'challenges'
                                    ]:
                                        references.extend(
                                            repo.list(
                                                table_name,
                                                fid,
                                                run['id'],
                                            )
                                        )

                                    if any(
                                        outgoing_id in json.dumps(item)
                                        or incoming_id in json.dumps(item)
                                        for item in references
                                    ):
                                        raise RuleError(
                                            'A current-run wheel or '
                                            'challenge references '
                                            'these players.'
                                        )

                                    if any(
                                        prefix + run['id']
                                        in st.session_state
                                        for prefix in [
                                            'draft:', 'paste_import:'
                                        ]
                                    ):
                                        raise RuleError(
                                            'Discard the unsaved '
                                            'game draft first.'
                                        )

                                    before = {
                                        'outgoing': dict(outgoing),
                                        'incoming': dict(incoming),
                                        'roster_ids': list(
                                            current_run['roster_ids']
                                        ),
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
                                        incoming_id
                                        if pid == outgoing_id
                                        else pid
                                        for pid
                                        in current_run['roster_ids']
                                    ]

                                    repo.put('players', outgoing)
                                    repo.put('players', incoming)
                                    repo.put('runs', current_run)

                                    audit(
                                        repo,
                                        fid,
                                        'starting_roster_correction',
                                        before,
                                        {
                                            'outgoing': outgoing,
                                            'incoming': incoming,
                                            'roster_ids':
                                                current_run['roster_ids'],
                                        },
                                        reason.strip(),
                                        run['id'],
                                    )
                            except RuleError as exc:
                                st.error(str(exc))
                            else:
                                st.rerun()

    for area in AREAS:
        with st.expander(
            area.title(),
            expanded=area in ['lineup', 'bench'],
        ):
            table([
                {
                    'Player': player['name'],
                    'Card': player['version'],
                    'OVR': player['ovr'],
                    'Position': player['position'],
                    'Order': player['order'],
                    'Eligibility': player['eligibility'],
                    'Status': badges(repo, fid, player),
                }
                for player in sorted(
                    players,
                    key=lambda player: player['order'],
                )
                if player['area'] == area
            ])

    if players:
        ids = [player['id'] for player in players]
        labels = {
            player['id']:
                player['name'] + ' · ' + player['area']
            for player in players
        }

        with st.form('arrange'):
            st.subheader('Arrange one player')
            pid = st.selectbox(
                'Player',
                ids,
                format_func=labels.get,
            )
            a, b, c = st.columns(3)
            area = a.selectbox('Destination area', AREAS[:-1])
            pos = b.selectbox('Assigned position', POSITIONS)
            order = c.number_input(
                'Batting order / role priority',
                1,
                30,
                1,
            )

            if st.form_submit_button('Save arrangement'):
                arrange(repo, fid, pid, area, pos, int(order))
                st.rerun()

        with st.form('swap'):
            st.subheader('Swap two assignments')
            first = st.selectbox(
                'First player',
                ids,
                format_func=labels.get,
            )
            second = st.selectbox(
                'Second player',
                ids,
                format_func=labels.get,
            )
            st.caption(
                'Both destination positions must be legal. '
                'Use this for starter/bench swaps and order changes.'
            )

            if st.form_submit_button('Swap assignments'):
                swap(repo, fid, first, second)
                st.rerun()

        with st.form('eligibility'):
            st.subheader('Update Event eligibility and notes')
            pid = st.selectbox(
                'Card to verify',
                ids,
                format_func=labels.get,
            )
            value = st.selectbox(
                'Eligibility',
                ['legal', 'illegal', 'unknown'],
            )
            note = st.text_input('Verification note')

            if st.form_submit_button('Update eligibility'):
                with repo.transaction():
                    player = repo.get('players', pid)
                    before = dict(player)
                    player.update(eligibility=value, notes=note)
                    repo.put('players', player)
                    audit(
                        repo,
                        fid,
                        'eligibility',
                        before,
                        player,
                        note or 'Manual eligibility check',
                    )
                st.rerun()

    if not is_locked:
        with st.expander('Add a card'):
            with st.form('new_player'):
                data = player_fields('new_')
                if st.form_submit_button('Add card'):
                    add_player(repo, fid, data)
                    st.rerun()

        if players:
            with st.form('remove'):
                st.subheader('DFA / demote')
                pid = st.selectbox(
                    'Removal target',
                    ids,
                    format_func=labels.get,
                )
                destination = st.selectbox(
                    'Destination',
                    ['dfa', 'minors'],
                )
                confirm = st.checkbox(
                    'I confirm this offseason removal.'
                )

                if (
                    st.form_submit_button('Apply removal')
                    and confirm
                ):
                    remove_player(repo, fid, pid, destination)
                    st.rerun()

        with st.expander(
            'Apply complete roster JSON — preserve existing stats'
        ):
            st.caption(
                'Reuses matching cards, adds missing cards, and sets '
                'the full lineup, bench, rotation, and bullpen. '
                'Active cards omitted from the JSON move to your '
                'selected destination. No saved games or stats are deleted.'
            )

            complete_upload = st.file_uploader(
                'Complete roster JSON',
                type=['json'],
                key='complete_roster_upload:' + fid,
            )
            pasted_roster = st.text_area(
                'Or paste complete roster JSON',
                key='complete_roster_paste:' + fid,
                height=180,
            )
            outgoing_area = st.selectbox(
                'Destination for active cards left out of this roster',
                ['minors', 'dfa'],
                key='complete_roster_outgoing:' + fid,
            )

            st.caption(
                'For the Week 4 roster, choose DFA to remove Seigler '
                'and Peralta from the active roster while preserving '
                'their past stats.'
            )

            complete_confirm = st.checkbox(
                'I verified the franchise, all card identities, '
                'Event eligibility, and outgoing destination.',
                key='complete_roster_confirm:' + fid,
            )

            if st.button(
                'Apply complete roster',
                disabled=(
                    not complete_confirm
                    or (
                        complete_upload is None
                        and not pasted_roster.strip()
                    )
                ),
                key='complete_roster_apply:' + fid,
            ):
                try:
                    if (
                        complete_upload is not None
                        and pasted_roster.strip()
                    ):
                        raise RuleError(
                            'Use either an uploaded file '
                            'or pasted JSON, not both.'
                        )

                    text = (
                        complete_upload.getvalue().decode('utf-8-sig')
                        if complete_upload is not None
                        else pasted_roster
                    )
                    payload = json.loads(text)

                    added, reused, removed = apply_complete_roster(
                        repo,
                        fid,
                        payload,
                        outgoing_area,
                    )
                except (ValueError, UnicodeError):
                    st.error('Enter a valid JSON list of cards.')
                except RuleError as exc:
                    st.error(str(exc))
                else:
                    st.session_state[
                        'complete_roster_notice:' + fid
                    ] = (
                        f'Roster applied: {reused} existing cards reused, '
                        f'{added} missing cards added, '
                        f'{removed} outgoing cards moved to {outgoing_area}. '
                        'Saved stats retained.'
                    )
                    st.rerun()

        upload = st.file_uploader(
            'Import additional cards (CSV / JSON)',
            type=['csv', 'json'],
        )
        confirmed = st.checkbox(
            'Import appends cards; I have checked for duplicates.'
        )

        if upload and confirmed and st.button('Import cards'):
            import_roster(
                repo,
                fid,
                upload.getvalue().decode('utf-8-sig'),
                upload.name.rsplit('.', 1)[-1],
            )
            st.rerun()

    with st.expander('Delete accidental duplicate permanently'):
        saved_stats = repo.list('stats', fid)
        used_ids = {stat['player_id'] for stat in saved_stats}

        gp = {}
        saved_lines = {}
        for row in saved_stats:
            pid = row['player_id']
            gp[pid] = gp.get(pid, 0) + row['line'].get('games', 0)
            saved_lines[pid] = saved_lines.get(pid, 0) + 1

        st.caption('Compare DFA entries below. GP includes all runs.')
        table([
            {
                'Player': player['name'],
                'Card': player['version'],
                'OVR': player['ovr'],
                'GP': gp.get(player['id'], 0),
                'Saved stat lines': saved_lines.get(player['id'], 0),
                'Player ID': player['id'],
            }
            for player in players
            if player['area'] in ['dfa', 'minors']
        ])

        duplicates = [
            player for player in players
            if player['area'] in ['dfa', 'minors']
            and player['id'] not in used_ids
        ]

        if not duplicates:
            st.info(
                'No DFA players without saved stats '
                'are available to delete.'
            )
        else:
            choices = {
                player['id']: player for player in duplicates
            }
            duplicate_id = st.selectbox(
                'Unused DFA entry to delete',
                list(choices),
                format_func=lambda pid: (
                    f"{choices[pid]['name']} · "
                    f"{choices[pid]['version']} · "
                    f"OVR {choices[pid]['ovr']} · ID {pid}"
                ),
                key='delete_duplicate_target',
            )
            confirmed = st.checkbox(
                'This is an accidental duplicate. '
                'Permanently delete this entry.',
                key='delete_duplicate_confirm',
            )

            if st.button(
                'Delete unused duplicate',
                disabled=not confirmed,
            ):
                try:
                    with repo.transaction():
                        player = repo.get('players', duplicate_id)

                        if (
                            not player
                            or player['franchise_id'] != fid
                            or player['area'] not in ['dfa', 'minors']
                        ):
                            raise RuleError(
                                'Choose an unused DFA or Minors entry.'
                            )

                        if any(
                            stat['player_id'] == duplicate_id
                            for stat in repo.list('stats', fid)
                        ):
                            raise RuleError(
                                'This entry has saved stats '
                                'and cannot be deleted.'
                            )

                        runs = repo.list('runs', fid)

                        if any(
                            prefix + run['id'] in st.session_state
                            for run in runs
                            for prefix in ['draft:', 'paste_import:']
                        ):
                            raise RuleError(
                                'Finish or discard your '
                                'unsaved game draft first.'
                            )

                        if (
                            player.get('protected')
                            or any(
                                run.get('mvp') == duplicate_id
                                for run in runs
                            )
                        ):
                            raise RuleError(
                                'This entry is protected '
                                'or has an MVP record.'
                            )

                        references = [
                            repo.get('franchises', fid).get('queue', [])
                        ]
                        for table_name in [
                            'tags',
                            'challenges',
                            'spins',
                            'moves',
                            'rewards',
                            'wheels',
                        ]:
                            references.extend(
                                repo.list(table_name, fid)
                            )

                        if any(
                            duplicate_id in json.dumps(item)
                            for item in references
                        ):
                            raise RuleError(
                                'This entry is referenced by a wheel, '
                                'tag, or challenge and cannot '
                                'be deleted here.'
                            )

                        for run in runs:
                            if duplicate_id in run['roster_ids']:
                                run['roster_ids'] = [
                                    pid for pid in run['roster_ids']
                                    if pid != duplicate_id
                                ]
                                repo.put('runs', run)

                        audit(
                            repo,
                            fid,
                            'delete_unused_duplicate',
                            player,
                            None,
                            'Permanently remove accidental DFA '
                            'duplicate with no saved stats',
                        )
                        repo.delete('players', duplicate_id)
                except RuleError as exc:
                    st.error(str(exc))
                else:
                    st.rerun()

    a, b = st.columns(2)
    a.download_button(
        'Export roster JSON',
        export_roster(repo, fid),
        'roster.json',
        'application/json',
    )
    b.download_button(
        'Export roster CSV',
        export_roster(repo, fid, 'csv'),
        'roster.csv',
        'text/csv',
    )

    st.subheader('Roster check')
    result = validate(repo, fid)

    if result.valid:
        st.success(
            'Roster composition and configured eligibility checks pass.'
        )
    else:
        for error in result.errors:
            st.warning(error)
