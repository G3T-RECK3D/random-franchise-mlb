import json
import streamlit as st

from services.offseason_service import resolve_move
from services.roster_service import locked
from models.domain import State, RuleError
from ui.common import table, navigate


def render(repo, f):
    fid = f['id']
    moves = repo.list('moves', fid)

    type_labels = {
        'acquire': 'Add a player',
        'trade': 'Trade a player',
        'reunion': 'Bring back a former card',
        'save_dfa': 'Save a player from DFA',
        'cancel_elimination': 'Cancel a removal',
        'upgrade': 'Upgrade a card',
        'dfa': 'DFA a player',
        'demote': 'Send to minors',
        'call_up': 'Call up a player',
        'tag': 'Franchise Tag',
        'protect': 'Protect a player',
        'extra_spin': 'Extra wheel spin',
    }
    status_labels = {
        'pending': 'Ready for offseason',
        'deferred': 'Saved for later',
        'resolved': 'Completed',
        'canceled': 'Canceled',
        'invalid': 'Unavailable',
    }

    rows = []
    for move in moves:
        run = (
            repo.get('runs', move['run_id'])
            if move.get('run_id') else None
        )
        game = (
            repo.get('games', move['game_id'])
            if move.get('game_id') else None
        )
        rows.append({
            'Week': (
                run.get('week_number', run['number']) if run else ''
            ),
            'Game': game['number'] if game else '',
            'Move': move['description'],
            'Action': type_labels.get(
                move['type'],
                move['type'].replace('_', ' ').title(),
            ),
            'Status': status_labels.get(
                move['status'], move['status'],
            ),
            'Required': (
                'Yes'
                if move.get('critical')
                and move['status'] == 'pending'
                else ''
            ),
            'Available': 'During offseason',
        })

    table(rows)

    if locked(repo, fid):
        st.info('Moves are banked until the current week ends.')
        return

    if f['state'] not in [
        State.MOVES, State.REBUILD, State.VALIDATION,
    ]:
        st.info(
            'Confirm Weekly MVP and complete required offseason wheels first.'
        )
        navigate('Continue offseason', 'Offseason')
        return

    pending = [
        move for move in moves
        if move['status'] in ['pending', 'deferred']
    ]
    if not pending:
        return

    choices = {move['id']: move for move in pending}
    mid = st.selectbox(
        'Move to resolve',
        list(choices),
        format_func=lambda identifier: choices[identifier]['description'],
        key='banked_move:' + fid,
    )
    move = repo.get('moves', mid)

    players = repo.list('players', fid)
    ids = [player['id'] for player in players]
    labels = {
        player['id']: (
            player['name']
            + ' · ' + str(player['ovr']) + ' OVR'
            + ' · ' + player['area']
        )
        for player in players
    }

    if move['type'] == 'reunion':
        former = repo.get('players', move.get('target'))
        if former:
            st.info(
                'Reunion Signing: ' + former['name']
                + ' · ' + str(former['ovr']) + ' OVR'
                + ' · ' + (
                    former.get('series')
                    or former.get('version')
                    or 'Card series not recorded'
                )
            )
            st.caption(
                'This returns the exact card selected by the wheel. '
                'Its existing player ID and saved stats are preserved. '
                'An inactive card returns to Minors; then arrange it '
                'in Roster Manager. No incoming card JSON is needed.'
            )
        else:
            st.warning(
                'The selected former card is unavailable. '
                'You can defer or cancel this reward.'
            )
    else:
        st.info(json.dumps(move.get('constraints', {}), indent=2))

    with st.form('resolve:' + mid):
        action = st.selectbox(
            'Resolution',
            ['resolved', 'deferred', 'canceled'],
            format_func=lambda value: {
                'resolved': 'Apply move',
                'deferred': 'Save for later',
                'canceled': 'Cancel move',
            }[value],
        )

        if move['type'] == 'reunion':
            target = move.get('target')
            st.write(
                '**Selected former card:** '
                + labels.get(target, 'Unavailable')
            )
        else:
            target = st.selectbox(
                'Target / replacement / tag recipient (if needed)',
                [None] + ids,
                index=(
                    ids.index(move['target']) + 1
                    if move.get('target') in ids else 0
                ),
                format_func=lambda identifier: labels.get(
                    identifier, 'Use original target / no target',
                ),
            )

        replacement = None
        if move['type'] == 'tag':
            replacement = st.selectbox(
                'Replace existing tag holder (only at tag cap)',
                [None] + ids,
                format_func=lambda identifier: labels.get(
                    identifier, 'No replacement',
                ),
            )

        cancel_id = None
        if move['type'] in ['cancel_elimination', 'save_dfa']:
            allowed = (
                ['dfa']
                if move['type'] == 'save_dfa'
                else ['dfa', 'demote', 'trade']
            )
            eligible = [
                item for item in moves
                if item.get('run_id') == move.get('run_id')
                and item['status'] == 'pending'
                and item['type'] in allowed
            ]
            consequence_labels = {
                item['id']: item['description'] for item in eligible
            }
            cancel_id = st.selectbox(
                'Consequence to cancel',
                [None] + list(consequence_labels),
                format_func=lambda identifier: consequence_labels.get(
                    identifier, 'Choose a consequence',
                ),
            )

        new = None
        incoming = ''
        max_card_confirmed = False
        next_card_confirmed = False

        if move['type'] == 'upgrade':
            player = repo.get('players', move.get('target'))

            if player:
                st.info(
                    player['name'] + ' earned this upgrade. '
                    'Normally, upgrade their own card. If they have no '
                    'higher Event-eligible card, you may upgrade one '
                    'active teammate instead.'
                )
                template = {
                    field: player.get(field, '')
                    for field in [
                        'name', 'version', 'ovr', 'primary', 'secondary',
                        'kind', 'team', 'series', 'bat', 'throw',
                        'eligibility',
                    ]
                }
            else:
                st.warning('The player who earned this reward is unavailable.')
                template = {}

            max_card_confirmed = st.checkbox(
                'I verified the player who earned this reward has no '
                'higher-rated Event-eligible card available.'
            )
            st.caption(
                'For a teammate upgrade, select the teammate in the Target '
                'dropdown above. Replace the JSON with that teammate’s '
                'name, type, and next available higher-rated Event-legal '
                'card details. Explain the transfer in Resolution notes.'
            )
            incoming = st.text_area(
                'Upgraded card JSON',
                value=json.dumps(template, indent=2),
                height=300,
            )
            next_card_confirmed = st.checkbox(
                'I verified this is the next available higher-rated '
                'Event-legal card of the player being upgraded.'
            )

        elif move['type'] in ['acquire', 'trade']:
            st.caption(
                'Enter incoming cards as JSON. Confirm the wheel’s '
                'external constraints yourself. Cards default to '
                'Minors until arranged.'
            )
            template = [
                dict(
                    name='New Card',
                    version='Base',
                    ovr=80,
                    primary='CF',
                    secondary=['LF', 'RF'],
                    kind='hitter',
                    area='minors',
                    position='CF',
                    order=1,
                    eligibility='legal',
                )
            ]
            incoming = st.text_area(
                'Incoming card(s) JSON',
                value=json.dumps(template, indent=2),
                height=230,
            )

        notes = st.text_area(
            'Resolution notes / external-constraint verification'
        )
        confirm = st.checkbox(
            'I confirm the selected action, targets, and Event eligibility.'
        )

        if st.form_submit_button(
            'Apply offseason resolution',
            type='primary',
        ):
            if (
                move['type'] in ['acquire', 'trade', 'upgrade']
                and action == 'resolved'
            ):
                if (
                    move['type'] == 'upgrade'
                    and not next_card_confirmed
                ):
                    st.error('Confirm the next available legal card first.')
                    return

                try:
                    parsed = json.loads(incoming)
                    new = (
                        parsed[0]
                        if move['type'] in ['trade', 'upgrade']
                        and isinstance(parsed, list)
                        and len(parsed) == 1
                        else parsed
                    )
                except ValueError:
                    st.error('Incoming JSON is invalid.')
                    return

            try:
                resolve_move(
                    repo,
                    fid,
                    mid,
                    action,
                    notes,
                    target,
                    new,
                    replacement,
                    confirm,
                    cancel_id,
                    max_card_confirmed=max_card_confirmed,
                )
            except RuleError as exc:
                st.error(str(exc))
            else:
                st.rerun()
