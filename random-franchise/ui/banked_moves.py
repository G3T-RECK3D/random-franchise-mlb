import json
import streamlit as st

from services.offseason_service import resolve_move, trade_card_errors
from services.roster_service import locked, target_pool
from models.domain import State, RuleError
from ui.common import table, navigate


def player_label(player):
    return (
        player['name']
        + ' · ' + str(player['ovr']) + ' OVR'
        + ' · ' + (
            player.get('series')
            or player.get('version')
            or 'Unknown series'
        )
        + ' · ' + player['area']
    )


def incoming_template(move, outgoing=None):
    rules = move.get('constraints', {})
    kind = rules.get(
        'kind',
        outgoing['kind'] if outgoing else 'hitter',
    )
    positions = rules.get('positions', [])
    primary = (
        positions[0]
        if positions
        else 'SP' if kind == 'pitcher'
        else 'CF'
    )
    teams = rules.get('teams', [])

    return [
        dict(
            name='New Card',
            version='Base',
            ovr=min(80, rules.get('max_ovr', 99)),
            primary=primary,
            secondary=[],
            kind=kind,
            team=teams[0] if teams else '',
            series='',
            bat='',
            throw='',
            area='minors',
            position=primary,
            order=1,
            eligibility='legal',
        )
    ]


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
        st.caption('No moves are waiting for resolution.')
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
    players_by_id = {player['id']: player for player in players}
    ids = list(players_by_id)
    labels = {
        player['id']: player_label(player)
        for player in players
    }
    original = players_by_id.get(move.get('target'))

    trade_method = 'New card JSON'
    if move['type'] == 'trade':
        rules = move.get('constraints', {})
        st.info(
            'Trade one hitter for a hitter, or one pitcher for a pitcher. '
            'The incoming card must meet the market, position, '
            'and Event restrictions.'
        )
        if rules.get('teams'):
            st.write('**Allowed teams:** ' + ', '.join(rules['teams']))
        if rules.get('positions'):
            st.write(
                '**Allowed primary or secondary positions:** '
                + ', '.join(rules['positions'])
            )
        if rules.get('max_ovr') is not None:
            st.write(
                '**Maximum incoming OVR:** ' + str(rules['max_ovr'])
            )

        # Outside the form so switching methods updates immediately.
        trade_method = st.radio(
            'Incoming card method',
            ['Existing card from Minors', 'New card JSON'],
            key='trade_method:' + mid,
        )

    elif move['type'] == 'reunion':
        if original:
            st.info('Reunion Signing: ' + player_label(original))
            st.caption(
                'The wheel selected this exact former card. '
                'Its existing ID and stats are preserved. '
                'An inactive card returns to Minors; arrange it '
                'in Roster Manager afterward.'
            )
        else:
            st.warning(
                'The selected former card is unavailable. '
                'You can defer or cancel this reward.'
            )

    elif move['type'] in ['dfa', 'demote']:
        st.info(
            'This action removes the selected player from the active roster. '
            'Fill the vacancy afterward in Roster Manager using an '
            'eligible existing card or an earned acquisition.'
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

        target = None

        if move['type'] == 'reunion':
            target = move.get('target')
            st.write(
                '**Selected former card:** '
                + labels.get(target, 'Unavailable')
            )

        elif move['type'] in ['trade', 'dfa', 'demote']:
            pool = target_pool(repo, fid)
            pool_ids = [player['id'] for player in pool]

            if original and original['id'] in pool_ids:
                target = original['id']
                heading = (
                    'Outgoing player'
                    if move['type'] == 'trade'
                    else 'Player to DFA'
                    if move['type'] == 'dfa'
                    else 'Player to send to Minors'
                )
                st.write('**' + heading + ':** ' + labels[target])
                st.caption('This is the player selected by the wheel.')
            else:
                st.warning(
                    'The original target is unavailable or no longer eligible. '
                    'Choose an eligible replacement target.'
                )
                target = st.selectbox(
                    'Outgoing / removal target',
                    [None] + pool_ids,
                    format_func=lambda identifier: labels.get(
                        identifier, 'Choose a player',
                    ),
                )

        elif move['type'] == 'call_up':
            minor_ids = [
                player['id'] for player in players
                if player['area'] == 'minors'
            ]
            target = st.selectbox(
                'Minor-league player to call up',
                [None] + minor_ids,
                index=(
                    minor_ids.index(move['target']) + 1
                    if move.get('target') in minor_ids else 0
                ),
                format_func=lambda identifier: labels.get(
                    identifier, 'Choose a player',
                ),
            )

        elif move['type'] in ['upgrade', 'tag', 'protect']:
            heading = {
                'upgrade': 'Player receiving the upgrade',
                'tag': 'Franchise Tag recipient',
                'protect': 'Player to protect',
            }[move['type']]
            target = st.selectbox(
                heading,
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
                ['dfa'] if move['type'] == 'save_dfa'
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
        incoming_player_id = None
        max_card_confirmed = False
        next_card_confirmed = False

        if move['type'] == 'trade':
            outgoing = players_by_id.get(target) or original

            if trade_method == 'Existing card from Minors':
                eligible_cards = [
                    player for player in players
                    if player['area'] == 'minors'
                    and player['id'] != target
                    and outgoing
                    and not trade_card_errors(
                        repo, fid, move, outgoing, player,
                    )
                ]
                incoming_labels = {
                    player['id']: player_label(player)
                    for player in eligible_cards
                }

                incoming_player_id = st.selectbox(
                    'Incoming card from Minors',
                    [None] + list(incoming_labels),
                    format_func=lambda identifier: incoming_labels.get(
                        identifier, 'Choose the incoming card',
                    ),
                )

                if not eligible_cards:
                    st.warning(
                        'No saved minor-league cards currently meet this '
                        'trade’s restrictions. Check the card’s Event '
                        'eligibility, team, primary and secondary positions, '
                        'and any OVR limit in Roster Manager.'
                    )

                st.caption(
                    'This reuses the selected card and its saved stats. '
                    'It stays in Minors until you arrange it. '
                    'No incoming JSON is needed.'
                )
            else:
                st.caption(
                    'Enter one new incoming card. It will be added '
                    'to Minors. Use the existing-card option for a '
                    'card already saved in this franchise.'
                )
                incoming = st.text_area(
                    'Incoming card JSON',
                    value=json.dumps(
                        incoming_template(move, outgoing), indent=2,
                    ),
                    height=300,
                )

        elif move['type'] == 'upgrade':
            player = original
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
                'For a teammate upgrade, select the teammate above '
                'and enter that teammate’s upgraded card details. '
                'Explain the transfer in Resolution notes.'
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

        elif move['type'] == 'acquire':
            st.caption(
                'Enter incoming cards as JSON and verify the reward’s '
                'restrictions. Incoming cards are added to Minors.'
            )
            incoming = st.text_area(
                'Incoming card(s) JSON',
                value=json.dumps(incoming_template(move), indent=2),
                height=300,
            )

        notes = st.text_area(
            'Resolution notes / external-constraint verification'
        )
        confirm = st.checkbox(
            'I confirm the selected action, players, and Event eligibility.'
        )

        if st.form_submit_button(
            'Apply offseason resolution',
            type='primary',
        ):
            needs_json = (
                move['type'] in ['acquire', 'upgrade']
                or (
                    move['type'] == 'trade'
                    and trade_method == 'New card JSON'
                )
            )

            if action == 'resolved':
                if (
                    move['type'] == 'trade'
                    and trade_method == 'Existing card from Minors'
                    and incoming_player_id is None
                ):
                    st.error('Choose an incoming card from Minors.')
                    return

                if (
                    move['type'] == 'upgrade'
                    and not next_card_confirmed
                ):
                    st.error('Confirm the next available legal card first.')
                    return

                if needs_json:
                    try:
                        parsed = json.loads(incoming)
                    except ValueError:
                        st.error('Incoming JSON is invalid.')
                        return

                    if move['type'] in ['trade', 'upgrade']:
                        if isinstance(parsed, list):
                            if (
                                len(parsed) != 1
                                or not isinstance(parsed[0], dict)
                            ):
                                st.error('Provide exactly one card object.')
                                return
                            parsed = parsed[0]
                        if not isinstance(parsed, dict):
                            st.error('Provide one card object.')
                            return
                        new = dict(parsed)

                        if move['type'] == 'trade':
                            new['area'] = 'minors'
                    else:
                        if isinstance(parsed, dict):
                            parsed = [parsed]
                        if (
                            not isinstance(parsed, list)
                            or any(
                                not isinstance(card, dict)
                                for card in parsed
                            )
                        ):
                            st.error('Provide a JSON list of card objects.')
                            return
                        new = [
                            dict(card, area='minors') for card in parsed
                        ]

            try:
                resolve_move(
                    repo,
                    fid,
                    mid,
                    action,
                    notes,
                    target_id=target,
                    new_player=new,
                    replace_tag=replacement,
                    confirmed=confirm,
                    cancel_move_id=cancel_id,
                    max_card_confirmed=max_card_confirmed,
                    incoming_player_id=(
                        incoming_player_id
                        if action == 'resolved'
                        and move['type'] == 'trade'
                        else None
                    ),
                )
            except RuleError as exc:
                st.error(str(exc))
            else:
                st.rerun()
