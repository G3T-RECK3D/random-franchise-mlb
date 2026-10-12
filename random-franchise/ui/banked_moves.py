import json
import streamlit as st

from services.offseason_service import resolve_move, trade_card_errors
from services.roster_service import locked, target_pool
from models.domain import State, RuleError
from ui.common import table, navigate


COLD_BAT_TYPES = {
    'cold_bat_hot_seat',
    'cold_bat_order',
    'cold_bat_bench',
    'downgrade',
}


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
        'kind', outgoing['kind'] if outgoing else 'hitter',
    )
    positions = rules.get('positions', [])
    primary = (
        positions[0] if positions
        else 'SP' if kind == 'pitcher'
        else 'CF'
    )
    teams = rules.get('teams', [])
    max_ovr = rules.get('max_ovr')
    default_ovr = min(80, max_ovr) if max_ovr is not None else 80

    return [
        dict(
            name='New Card',
            version='Base',
            ovr=default_ovr,
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


def card_change_template(player):
    if not player:
        return {}
    template = {
        field: player.get(field, '')
        for field in [
            'name', 'version', 'ovr', 'primary', 'secondary',
            'kind', 'team', 'series', 'bat', 'throw', 'eligibility',
        ]
    }
    for field in ['card_uuid', 'card_image_url']:
        template[field] = ''
    return template


def parse_cards(text, single=False):
    try:
        parsed = json.loads(text)
    except ValueError:
        raise RuleError('Incoming JSON is invalid.')

    if isinstance(parsed, dict):
        parsed = [parsed]

    if (
        not isinstance(parsed, list)
        or not parsed
        or any(not isinstance(card, dict) for card in parsed)
    ):
        raise RuleError('Provide a JSON list of card objects.')

    if single:
        if len(parsed) != 1:
            raise RuleError('Provide exactly one card object.')
        return dict(parsed[0])

    return [dict(card) for card in parsed]


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
        'downgrade': 'Downgrade a card',
        'cold_bat_hot_seat': 'Hot Seat next week',
        'cold_bat_order': 'Move to batting spots 7–9',
        'cold_bat_bench': 'Bench assignment',
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
                move['type'], move['type'].replace('_', ' ').title(),
            ),
            'Status': status_labels.get(
                move['status'], move['status'],
            ),
            'Required': (
                'Yes'
                if move.get('critical')
                and move['status'] in ['pending', 'deferred']
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
    rules = move.get('constraints', {})

    players = repo.list('players', fid)
    players_by_id = {player['id']: player for player in players}
    ids = list(players_by_id)
    labels = {
        player['id']: player_label(player) for player in players
    }
    original = players_by_id.get(move.get('target'))

    is_mvp_upgrade = (
        move['type'] == 'upgrade'
        and rules.get('fallback') == 'protection'
    )
    fixed_target = (
        move['type'] == 'reunion'
        or move['type'] in COLD_BAT_TYPES
        or is_mvp_upgrade
        or rules.get('fixed_target', False)
    )

    trade_method = 'New card JSON'
    use_fallback = False

    if move['type'] == 'trade':
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

        trade_method = st.radio(
            'Incoming card method',
            ['Existing card from Minors', 'New card JSON'],
            key='trade_method:' + mid,
        )

    elif move['type'] == 'reunion':
        if original:
            st.info('Reunion Signing: ' + player_label(original))
        st.caption(
            'Return the exact former card selected by the wheel. '
            'An inactive card returns to Minors. Its ID and stats '
            'are preserved; no incoming JSON is needed.'
        )

    elif move['type'] in ['dfa', 'demote']:
        st.info(
            'Remove the selected player from the active roster. '
            'Fill the vacancy afterward in Roster Manager using an '
            'eligible existing card or an earned acquisition.'
        )

    elif move['type'] == 'cold_bat_order':
        st.info(
            'Move the selected hitter to lineup spot 7, 8, or 9 '
            'for the start of next week. Save that arrangement, '
            'then return here to confirm the consequence.'
        )
        navigate('Arrange batting order', 'Roster Manager')

    elif move['type'] == 'cold_bat_bench':
        st.info(
            'Move the selected hitter to the bench for the start '
            'of next week. Arrange an eligible replacement in the '
            'lineup, then return here to confirm.'
        )
        navigate('Arrange lineup and bench', 'Roster Manager')

    elif move['type'] == 'cold_bat_hot_seat':
        st.info(
            'Apply Hot Seat to the selected hitter for next week. '
            'This flags them for your existing Hot Seat rules; '
            'it does not remove them or change their card.'
        )

    elif move['type'] == 'downgrade':
        st.info(
            'Use the next available lower-rated Event-legal version '
            'of the selected player. Their existing ID and stats stay.'
        )
        method = st.radio(
            'Downgrade resolution',
            [
                'Use the next lower-rated legal card',
                'No lower-rated legal card exists — apply Hot Seat',
            ],
            key='downgrade_method:' + mid,
        )
        use_fallback = method.startswith('No lower')

    elif is_mvp_upgrade:
        st.info(
            'Upgrade this Weekly MVP to their next available '
            'higher-rated Event-legal card. This reward stays '
            'with the MVP and cannot transfer to a teammate.'
        )
        method = st.radio(
            'MVP upgrade resolution',
            [
                'Use the next higher-rated legal card',
                'No higher-rated legal card exists — apply protection',
            ],
            key='mvp_upgrade_method:' + mid,
        )
        use_fallback = method.startswith('No higher')

    else:
        st.info(json.dumps(rules, indent=2))

    with st.form('resolve:' + mid):
        actions = (
            ['resolved']
            if move.get('critical') and move['type'] != 'tag'
            else ['resolved', 'deferred', 'canceled']
        )
        action = st.selectbox(
            'Resolution',
            actions,
            format_func=lambda value: {
                'resolved': 'Apply move',
                'deferred': 'Save for later',
                'canceled': 'Cancel move',
            }[value],
        )

        target = None

        if fixed_target:
            target = move.get('target')
            st.write(
                '**Selected player:** ' + labels.get(target, 'Unavailable')
            )
            if not original:
                st.warning('The selected player entry is unavailable.')

        elif move['type'] in ['trade', 'dfa', 'demote']:
            pool = target_pool(repo, fid)
            pool_ids = [player['id'] for player in pool]

            if original and original['id'] in pool_ids:
                target = original['id']
                heading = (
                    'Outgoing player' if move['type'] == 'trade'
                    else 'Player to DFA' if move['type'] == 'dfa'
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
            consequence_labels = {
                item['id']: item['description']
                for item in moves
                if item.get('run_id') == move.get('run_id')
                and item['status'] == 'pending'
                and item['type'] in allowed
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
        no_lower_card_confirmed = False
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
                        'No saved minor-league cards meet this trade’s '
                        'restrictions. Check Event eligibility, team, '
                        'primary/secondary positions, and any OVR limit.'
                    )
                st.caption(
                    'Reuses the existing card and saved stats. '
                    'It stays in Minors until arranged. No JSON is needed.'
                )
            else:
                incoming = st.text_area(
                    'Incoming card JSON',
                    value=json.dumps(
                        incoming_template(move, outgoing), indent=2,
                    ),
                    height=300,
                )
                st.caption(
                    'New incoming cards are added to Minors. Use the '
                    'existing-card option for cards already saved here.'
                )

        elif move['type'] == 'downgrade':
            if use_fallback:
                no_lower_card_confirmed = st.checkbox(
                    'I verified that this player has no lower-rated '
                    'Event-legal card available.'
                )
            else:
                incoming = st.text_area(
                    'Lower-rated card JSON',
                    value=json.dumps(
                        card_change_template(original), indent=2,
                    ),
                    height=300,
                )
                next_card_confirmed = st.checkbox(
                    'I verified this is the next available lower-rated '
                    'Event-legal version of this player.'
                )
                st.caption(
                    'Replace the current card details with the lower '
                    'version. Keep the player name and type unchanged. '
                    'Include the new card UUID/image URL if you have them; '
                    'otherwise old artwork is cleared.'
                )

        elif is_mvp_upgrade:
            if use_fallback:
                max_card_confirmed = st.checkbox(
                    'I verified that this MVP has no higher-rated '
                    'Event-legal card available.'
                )
            else:
                incoming = st.text_area(
                    'Upgraded MVP card JSON',
                    value=json.dumps(
                        card_change_template(original), indent=2,
                    ),
                    height=300,
                )
                next_card_confirmed = st.checkbox(
                    'I verified this is the next available higher-rated '
                    'Event-legal version of this MVP.'
                )

        elif move['type'] == 'upgrade':
            if original:
                st.info(
                    original['name'] + ' earned this upgrade. '
                    'Normally upgrade their own card. A development '
                    'upgrade may transfer to an active teammate only '
                    'if the original player has no higher legal version.'
                )

            max_card_confirmed = st.checkbox(
                'I verified the player who earned this reward has no '
                'higher-rated Event-legal card available.'
            )
            st.caption(
                'For a development transfer, select the teammate above '
                'and replace the JSON with that teammate’s upgraded '
                'card details. Explain the transfer in your notes.'
            )
            incoming = st.text_area(
                'Upgraded card JSON',
                value=json.dumps(
                    card_change_template(original), indent=2,
                ),
                height=300,
            )
            next_card_confirmed = st.checkbox(
                'I verified this is the next available higher-rated '
                'Event-legal card of the player being upgraded.'
            )

        elif move['type'] == 'acquire':
            incoming = st.text_area(
                'Incoming card(s) JSON',
                value=json.dumps(incoming_template(move), indent=2),
                height=300,
            )
            st.caption(
                'Verify the reward’s restrictions. Incoming cards '
                'are added to Minors.'
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
            if action == 'resolved':
                if (
                    move['type'] == 'trade'
                    and trade_method == 'Existing card from Minors'
                    and incoming_player_id is None
                ):
                    st.error('Choose an incoming card from Minors.')
                    return

                if move['type'] == 'downgrade':
                    if use_fallback and not no_lower_card_confirmed:
                        st.error('Confirm that no qualifying lower card exists.')
                        return
                    if not use_fallback and not next_card_confirmed:
                        st.error('Confirm the next lower-rated legal card.')
                        return

                if move['type'] == 'upgrade':
                    if is_mvp_upgrade and use_fallback:
                        if not max_card_confirmed:
                            st.error(
                                'Confirm that no qualifying higher card exists.'
                            )
                            return
                    elif not next_card_confirmed:
                        st.error('Confirm the next higher-rated legal card.')
                        return

                needs_json = (
                    move['type'] == 'acquire'
                    or (
                        move['type'] == 'trade'
                        and trade_method == 'New card JSON'
                    )
                    or (
                        move['type'] == 'upgrade'
                        and not (is_mvp_upgrade and use_fallback)
                    )
                    or (
                        move['type'] == 'downgrade'
                        and not use_fallback
                    )
                )

                if needs_json:
                    try:
                        new = parse_cards(
                            incoming,
                            single=move['type'] != 'acquire',
                        )
                    except RuleError as exc:
                        st.error(str(exc))
                        return

                    if move['type'] == 'trade':
                        new['area'] = 'minors'
                    elif move['type'] == 'acquire':
                        new = [
                            dict(card, area='minors') for card in new
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
                    no_lower_card_confirmed=no_lower_card_confirmed,
                    next_card_confirmed=next_card_confirmed,
                )
            except RuleError as exc:
                st.error(str(exc))
            else:
                st.rerun()
