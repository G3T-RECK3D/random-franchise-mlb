import hashlib
import json

import streamlit as st

from models.domain import State, RuleError, POSITIONS, ACTIVE_AREAS
from services.offseason_service import trade_card_errors
from services.acquisition_service import (
    resolve_banked_move as resolve_move,
    incoming_card_errors,
)
from services.roster_service import locked, target_pool
from services.franchise_service import settings
from services.roster_validator import card_event_errors
from ui.common import table, navigate
from ui.wheel_room import card_url, stadium_url


COLD_BAT_TYPES = {
    'cold_bat_hot_seat',
    'cold_bat_order',
    'cold_bat_bench',
    'downgrade',
}

TYPE_LABELS = {
    'acquire': 'Add or upgrade a player',
    'trade': 'Trade a player',
    'reunion': 'Reunion Signing',
    'save_dfa': 'Save a player from DFA',
    'cancel_elimination': 'Cancel a removal',
    'upgrade': 'Upgrade a card',
    'downgrade': 'Downgrade a card',
    'cold_bat_hot_seat': 'Hot Seat next week',
    'cold_bat_order': 'Move to batting spots 7–9',
    'cold_bat_bench': 'Bench assignment',
    'dfa': 'DFA a player',
    'demote': 'Send to Minors',
    'call_up': 'Call up a player',
    'tag': 'Franchise Tag',
    'protect': 'Protect a player',
    'extra_spin': 'Extra wheel spin',
}

STATUS_LABELS = {
    'pending': 'Ready for offseason',
    'deferred': 'Saved for later',
    'resolved': 'Completed',
    'canceled': 'Canceled',
    'invalid': 'Unavailable',
}


def player_label(player):
    return (
        player['name']
        + ' · '
        + str(player['ovr'])
        + ' OVR · '
        + str(player.get('series') or player.get('version') or 'Card')
        + ' · '
        + player['area']
    )


def header():
    st.markdown(
        '<div style="padding:26px;border:1px solid #744639;'
        'border-top:4px solid #ff334f;border-radius:14px;'
        'margin-bottom:20px;background-color:#171b26;'
        'background-image:linear-gradient(90deg,'
        'rgba(9,13,22,.94),rgba(9,13,22,.35)),url(&quot;'
        + stadium_url()
        + '&quot;);background-size:cover;background-position:center;">'
        '<div style="color:#efc778;font-size:11px;letter-spacing:3px;'
        'font-weight:800;">FRONT OFFICE • TRANSACTIONS</div>'
        '<div style="color:#fff0ce;font-size:32px;font-weight:900;'
        'margin-top:10px;">Banked Moves</div>'
        '<div style="color:#d3d9e5;margin-top:8px;font-size:13px;">'
        'Choose your cards. Review the move. Build next week’s roster.'
        '</div></div>',
        unsafe_allow_html=True,
    )


def show_card(player, heading):
    with st.container(border=True):
        st.markdown('**' + heading + '**')

        if not player:
            st.caption('No player selected.')
            return

        image = card_url(player)

        if image:
            st.image(image, width=115)

        st.write(player.get('name') or 'Unnamed card')

        st.caption(
            str(player.get('ovr', ''))
            + ' OVR · '
            + str(player.get('series') or player.get('version') or 'Card')
        )

        st.caption(
            'Position: '
            + str(player.get('primary', ''))
            + ' · '
            + str(player.get('area', 'minors')).title()
            + ' · Event eligibility: '
            + str(player.get('eligibility', 'unknown'))
        )


def parse_cards(text):
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
        raise RuleError(
            'Provide a card object or a JSON list of card objects.'
        )

    return [dict(card) for card in parsed]


def template(move, player=None, changing=False):
    if changing and player:
        result = {
            field: player.get(field, '')
            for field in [
                'name', 'version', 'ovr', 'primary', 'secondary',
                'kind', 'team', 'series', 'bat', 'throw', 'eligibility',
            ]
        }
        result.update(card_uuid='', card_image_url='')
        return result

    rules = move.get('constraints', {})
    kind = rules.get('kind', player['kind'] if player else 'hitter')

    positions = [
        pos for pos in rules.get('positions', [])
        if pos in POSITIONS
    ]

    primary = (
        positions[0]
        if positions
        else 'SP'
        if kind == 'pitcher'
        else 'CF'
    )

    maximum = rules.get('max_ovr')
    teams = rules.get('teams', [])

    return dict(
        name='',
        version='Base',
        ovr=min(80, maximum) if maximum is not None else 80,
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
        eligibility='unknown',
        card_uuid='',
        card_image_url='',
    )


def card_fields(seed, key, changing=False):
    positions = sorted(POSITIONS)
    a, b = st.columns(2)

    name = a.text_input(
        'Player name',
        value=seed.get('name', ''),
        key=key + ':name',
        disabled=changing,
    )

    kind_options = ['hitter', 'pitcher']

    kind = b.selectbox(
        'Player type',
        kind_options,
        index=kind_options.index(seed.get('kind', 'hitter')),
        key=key + ':kind',
        disabled=changing,
    )

    a, b = st.columns(2)

    version = a.text_input(
        'Card version',
        value=seed.get('version', 'Base'),
        key=key + ':version',
    )

    ovr = b.number_input(
        'OVR',
        min_value=0,
        max_value=99,
        value=int(seed.get('ovr', 80)),
        step=1,
        key=key + ':ovr',
    )

    a, b = st.columns(2)

    primary = a.selectbox(
        'Primary position',
        positions,
        index=positions.index(seed.get('primary', positions[0])),
        key=key + ':primary',
    )

    secondary = b.multiselect(
        'Secondary positions',
        positions,
        default=[
            p for p in seed.get('secondary', [])
            if p in positions
        ],
        key=key + ':secondary',
    )

    a, b = st.columns(2)

    team = a.text_input(
        'MLB team',
        value=seed.get('team', ''),
        key=key + ':team',
    )

    series = b.text_input(
        'Card series',
        value=seed.get('series', ''),
        key=key + ':series',
    )

    a, b, c = st.columns(3)
    bats = ['', 'R', 'L', 'S']
    throws = ['', 'R', 'L']

    bat = a.selectbox(
        'Bats',
        bats,
        index=(
            bats.index(seed.get('bat'))
            if seed.get('bat') in bats else 0
        ),
        key=key + ':bat',
    )

    throw = b.selectbox(
        'Throws',
        throws,
        index=(
            throws.index(seed.get('throw'))
            if seed.get('throw') in throws else 0
        ),
        key=key + ':throw',
    )

    eligibility_options = ['unknown', 'legal', 'illegal']

    eligibility = c.selectbox(
        'Event eligibility',
        eligibility_options,
        index=(
            eligibility_options.index(seed.get('eligibility'))
            if seed.get('eligibility') in eligibility_options else 0
        ),
        key=key + ':eligibility',
    )

    with st.expander('Optional card artwork details'):
        card_uuid = st.text_input(
            'Card UUID',
            value=seed.get('card_uuid', ''),
            key=key + ':uuid',
        )

        image_url = st.text_input(
            'Card image URL',
            value=seed.get('card_image_url', ''),
            key=key + ':image',
        )

    return dict(
        name=name.strip(),
        version=version.strip(),
        ovr=int(ovr),
        primary=primary,
        secondary=secondary,
        kind=kind,
        team=team.strip(),
        series=series.strip(),
        bat=bat,
        throw=throw,
        eligibility=eligibility,
        area='minors',
        position=primary,
        order=1,
        card_uuid=card_uuid.strip(),
        card_image_url=image_url.strip(),
    )


def show_rules(move):
    rules = move.get('constraints', {})

    with st.container(border=True):
        st.markdown('**Move restrictions**')
        st.write(move['description'])

        if rules.get('teams'):
            st.write('Allowed teams: ' + ', '.join(rules['teams']))

        if rules.get('positions'):
            st.write(
                'Allowed primary or secondary positions: '
                + ', '.join(rules['positions'])
            )

        if rules.get('kind'):
            st.write('Player type: ' + rules['kind'])

        if rules.get('max_ovr') is not None:
            st.write(
                'Maximum incoming OVR: ' + str(rules['max_ovr'])
            )

        if move['type'] in ['acquire', 'trade']:
            st.caption(
                'Incoming cards must be Event-legal. Verify any '
                'additional wheel instructions in your notes.'
            )

        if rules:
            with st.expander('All saved restrictions'):
                st.json(rules)


def move_rows(moves, runs, games):
    rows = []

    for move in moves:
        run = runs.get(move.get('run_id'))
        game = games.get(move.get('game_id'))

        rows.append({
            'Week': (
                run.get('week_number', run['number'])
                if run else ''
            ),
            'Game': game['number'] if game else '',
            'Move': move['description'],
            'Action': TYPE_LABELS.get(move['type'], move['type']),
            'Status': STATUS_LABELS.get(
                move['status'], move['status']
            ),
            'Required': (
                'Yes'
                if move.get('critical')
                and move['status'] in ['pending', 'deferred']
                else ''
            ),
        })

    return rows


def review_lines(move, payload, players, moves, removal_pool):
    action = payload['action']

    if action != 'resolved':
        return [
            'Save this move for later.'
            if action == 'deferred'
            else 'Cancel this move.'
        ]

    kind = move['type']
    target = players.get(
        payload['target_id'] or move.get('target')
    )
    name = target['name'] if target else 'Selected player'
    new = payload['new_player']

    if kind == 'trade':
        incoming = players.get(payload['incoming_player_id']) or new

        return [
            name + ' → DFA',
            incoming['name']
            + ' → Minors ('
            + (
                'reuse existing card and stats'
                if payload['incoming_player_id']
                else 'add new card'
            )
            + ')',
            'Arrange the lineup afterward in Roster Manager.',
        ]

    if kind == 'acquire':
        if payload['upgrade_player_id']:
            recipient = players[payload['upgrade_player_id']]

            return [
                recipient['name']
                + f" → {new['ovr']} OVR · {new['version']}",
                'Update the same player ID. Keep their roster '
                'assignment and accumulated stats.',
            ]

        if payload['incoming_player_id']:
            incoming = players[payload['incoming_player_id']]

            return [
                incoming['name'] + ' → use existing Minors card',
                'Keep the existing ID and stats. Arrange the '
                'card in Roster Manager afterward.',
            ]

        return [
            card['name'] + ' → Minors (new card)'
            for card in new
        ]

    if kind in ['dfa', 'demote']:
        quantity = move.get('constraints', {}).get('quantity', 1)

        targets = (
            [target['id']] if target else []
        ) + [
            pid
            for pid in removal_pool
            if not target or pid != target['id']
        ][:quantity - 1]

        return [
            players[pid]['name']
            + (' → DFA' if kind == 'dfa' else ' → Minors')
            for pid in targets
        ] + [
            'Fill roster vacancies in Roster Manager. '
            'This move does not award an incoming card.'
        ]

    if kind == 'upgrade':
        if (
            payload['max_card_confirmed']
            and move.get('constraints', {}).get('fallback') == 'protection'
        ):
            return [
                name + ' → temporary protection '
                '(no higher legal card available)'
            ]

        return [
            name + f" → {new['ovr']} OVR · {new['version']}",
            'Update the existing player entry; preserve its ID and stats.',
        ]

    if kind == 'downgrade':
        if payload['no_lower_card_confirmed']:
            return [
                name + ' → Hot Seat next week '
                '(no lower legal card available)'
            ]

        return [
            name + f" → {new['ovr']} OVR · {new['version']}",
            'Update the existing player entry; preserve its ID and stats.',
        ]

    if kind == 'reunion':
        return [
            name + ' → return the existing former card',
            'Inactive cards return to Minors; '
            'active cards keep their assignment.',
        ]

    if kind == 'cold_bat_order':
        return [
            name + ' → confirm batting spot 7, 8, or 9 for next week'
        ]

    if kind == 'cold_bat_bench':
        return [
            name + ' → confirm bench assignment for next week'
        ]

    if kind == 'cold_bat_hot_seat':
        return [name + ' → Hot Seat next week']

    if kind == 'call_up':
        return [
            name + ' → active roster',
            'Check roster sizes and assignments afterward.',
        ]

    if kind in ['tag', 'protect']:
        lines = [
            name
            + (
                ' → Franchise Tag'
                if kind == 'tag'
                else ' → temporary protection'
            )
        ]

        replacement = players.get(payload['replace_tag'])

        if kind == 'tag' and replacement:
            lines.append(
                'Replace tag holder: ' + replacement['name']
            )

        return lines

    if kind in ['cancel_elimination', 'save_dfa']:
        other = next(
            (
                m for m in moves
                if m['id'] == payload['cancel_move_id']
            ),
            None,
        )

        return [
            'Cancel consequence: '
            + (other['description'] if other else 'not selected')
        ]

    if kind == 'extra_spin':
        return ['Queue another Front Office spin.']

    return ['Record resolution: ' + move['description']]


def render(repo, f):
    fid = f['id']
    moves = repo.list('moves', fid)
    players = repo.list('players', fid)

    by_id = {p['id']: p for p in players}
    labels = {p['id']: player_label(p) for p in players}
    runs = {r['id']: r for r in repo.list('runs', fid)}
    games = {g['id']: g for g in repo.list('games', fid)}

    pending = [
        m for m in moves
        if m['status'] in ['pending', 'deferred']
    ]
    required = [m for m in pending if m.get('critical')]
    optional = [m for m in pending if not m.get('critical')]
    finished = [
        m for m in moves
        if m['status'] not in ['pending', 'deferred']
    ]

    header()

    a, b, c = st.columns(3)
    a.metric('Required moves', len(required))
    b.metric('Optional / saved', len(optional))
    c.metric(
        'Completed moves',
        sum(m['status'] == 'resolved' for m in finished),
    )

    tabs = st.tabs([
        'Required consequences',
        'Rewards & saved moves',
        'History',
    ])

    for tab, group in zip(tabs, [required, optional, finished]):
        with tab:
            table(move_rows(group, runs, games))

    if locked(repo, fid):
        st.info('Moves stay banked until the current week ends.')
        return

    if f['state'] not in [
        State.MOVES, State.REBUILD, State.VALIDATION,
    ]:
        st.info(
            'Confirm Weekly MVP and finish '
            'required offseason wheels first.'
        )
        navigate('Continue offseason', 'Offseason')
        return

    if not pending:
        st.success('No moves are waiting for resolution.')
        navigate('Continue offseason', 'Offseason')
        return

    removal_pool = [
        p['id'] for p in target_pool(repo, fid)
    ]

    choices = {
        m['id']: m for m in required + optional
    }

    mid = st.selectbox(
        'Move to resolve',
        list(choices),
        format_func=lambda i: (
            'Required · ' if choices[i].get('critical') else ''
        ) + choices[i]['description'],
        key='banked_move:' + fid,
    )

    move = choices[mid]
    kind = move['type']
    rules = move.get('constraints', {})
    original = by_id.get(move.get('target'))

    is_mvp = (
        kind == 'upgrade'
        and rules.get('fallback') == 'protection'
    )

    fixed = (
        kind == 'reunion'
        or kind in COLD_BAT_TYPES
        or is_mvp
        or rules.get('fixed_target', False)
    )

    show_rules(move)

    actions = (
        ['resolved']
        if move.get('critical') and kind != 'tag'
        else ['resolved', 'deferred', 'canceled']
    )

    action = st.selectbox(
        'Resolution',
        actions,
        format_func=lambda a: {
            'resolved': 'Apply move',
            'deferred': 'Save for later',
            'canceled': 'Cancel move',
        }[a],
        key='resolution:' + mid,
    )

    acquisition_method = 'Add a new card'
    upgrade_pid = None

    if kind == 'acquire' and action == 'resolved':
        methods = [
            'Existing card from Minors',
            'Add a new card',
            'Upgrade an existing player’s card',
        ]

        if rules.get('quantity', 1) != 1:
            methods = ['Add a new card']
            st.caption(
                'This reward requires multiple incoming cards; '
                'enter each new card below.'
            )

        acquisition_method = st.radio(
            'How to use this acquisition reward',
            methods,
            index=methods.index('Add a new card'),
            key='acquire_method:' + mid,
        )

        if acquisition_method == 'Upgrade an existing player’s card':
            upgrade_ids = [
                p['id']
                for p in players
                if p['area'] in ACTIVE_AREAS
                and (
                    not rules.get('kind')
                    or p['kind'] == rules['kind']
                )
            ]

            upgrade_pid = st.selectbox(
                'Existing player to upgrade',
                [None] + upgrade_ids,
                format_func=lambda i: labels.get(
                    i, 'Choose a player'
                ),
                key='acquire_upgrade:' + mid,
            )

            st.caption(
                'Use the same player’s higher-rated Event-legal card. '
                'For a worst-position reward, select the player at '
                'that position and explain your choice in the notes. '
                'This consumes the acquisition reward.'
            )

    target = None

    if fixed:
        target = move.get('target')

        if not original:
            st.warning('The selected player is unavailable.')

    elif kind in ['trade', 'dfa', 'demote']:
        pool_ids = [
            p['id'] for p in target_pool(repo, fid)
        ]

        if original and original['id'] in pool_ids:
            target = original['id']
            st.caption(
                'The outgoing player is fixed '
                'by the audited wheel result.'
            )

        else:
            target = st.selectbox(
                'Outgoing / removal target',
                [None] + pool_ids,
                format_func=lambda i: labels.get(
                    i, 'Choose a player'
                ),
                key='target:' + mid,
            )

    elif kind == 'call_up':
        ids = [
            p['id'] for p in players
            if p['area'] == 'minors'
        ]

        target = st.selectbox(
            'Minor-league player to call up',
            [None] + ids,
            index=(
                ids.index(move['target']) + 1
                if move.get('target') in ids else 0
            ),
            format_func=lambda i: labels.get(
                i, 'Choose a player'
            ),
            key='target:' + mid,
        )

    elif kind in ['upgrade', 'tag', 'protect']:
        ids = [
            p['id']
            for p in players
            if kind != 'upgrade' or p['area'] in ACTIVE_AREAS
        ]

        target = st.selectbox(
            'Player receiving this reward',
            [None] + ids,
            index=(
                ids.index(move['target']) + 1
                if move.get('target') in ids else 0
            ),
            format_func=lambda i: labels.get(
                i, 'Use original target'
            ),
            key='target:' + mid,
        )

    selected = (
        by_id.get(upgrade_pid)
        if upgrade_pid
        else by_id.get(target) or original
    )

    replacement = None
    cancel_id = None

    if kind == 'tag':
        replacement = st.selectbox(
            'Replace tag holder (only at tag cap)',
            [None] + list(by_id),
            format_func=lambda i: labels.get(
                i, 'No replacement'
            ),
            key='tag_replace:' + mid,
        )

    if kind in ['cancel_elimination', 'save_dfa']:
        allowed = (
            ['dfa']
            if kind == 'save_dfa'
            else ['dfa', 'demote', 'trade']
        )

        cancellations = {
            m['id']: m['description']
            for m in moves
            if m.get('run_id') == move.get('run_id')
            and m['status'] == 'pending'
            and m['type'] in allowed
        }

        cancel_id = st.selectbox(
            'Consequence to cancel',
            [None] + list(cancellations),
            format_func=lambda i: cancellations.get(
                i, 'Choose a consequence'
            ),
            key='cancel:' + mid,
        )

    fallback = False
    max_confirmed = False
    lower_confirmed = False
    next_confirmed = False
    incoming_id = None
    incoming_cards = None
    incoming_json = None
    incoming_preview = None
    field_errors = []

    if action == 'resolved':
        if kind in ['cold_bat_order', 'cold_bat_bench']:
            st.info(
                'Save the required assignment in Roster Manager first, '
                'then return here to confirm it. Keep it through '
                'the start of next week.'
            )
            navigate('Arrange roster', 'Roster Manager')

        elif kind in ['dfa', 'demote']:
            st.info(
                'This removes the player. Fill the vacancy afterward '
                'in Roster Manager with an eligible existing card '
                'or an earned acquisition.'
            )

        elif kind == 'reunion':
            st.info(
                'Reuses the exact former card selected by the wheel. '
                'No new card entry is needed.'
            )

        elif kind == 'cold_bat_hot_seat':
            st.info(
                'Flags this hitter for Hot Seat targeting next week. '
                'It does not remove them.'
            )

        if kind == 'downgrade' or is_mvp:
            options = [
                'Use the next legal card',
                'No qualifying card exists — use fallback',
            ]

            fallback = (
                st.radio(
                    'Card change',
                    options,
                    key='fallback:' + mid,
                )
                == options[1]
            )

            if fallback:
                if kind == 'downgrade':
                    st.caption('Fallback: Hot Seat next week.')
                    lower_confirmed = st.checkbox(
                        'I verified no lower-rated Event-legal card exists.',
                        key='lower:' + mid,
                    )
                else:
                    st.caption(
                        'Fallback: temporary protection. '
                        'The MVP reward cannot transfer.'
                    )
                    max_confirmed = st.checkbox(
                        'I verified no higher-rated Event-legal card exists.',
                        key='max:' + mid,
                    )

        if kind == 'upgrade' and not is_mvp:
            st.info(
                (
                    original['name']
                    if original else 'The original player'
                )
                + ' earned this upgrade. A development reward may '
                'transfer to an active teammate only when the '
                'original player has no higher legal card.'
            )

            max_confirmed = st.checkbox(
                'I verified the original player has no '
                'higher-rated Event-legal card.',
                key='max:' + mid,
            )

        existing_trade = False

        if kind == 'trade':
            method = st.radio(
                'Incoming card',
                [
                    'Existing card from Minors',
                    'Add a new card',
                ],
                key='trade_method:' + mid,
            )

            existing_trade = (
                method == 'Existing card from Minors'
            )

            if existing_trade:
                eligible = [
                    p
                    for p in players
                    if p['area'] == 'minors'
                    and p['id'] != target
                    and selected
                    and not trade_card_errors(
                        repo, fid, move, selected, p
                    )
                ]

                incoming_labels = {
                    p['id']: player_label(p)
                    for p in eligible
                }

                incoming_id = st.selectbox(
                    'Incoming card from Minors',
                    [None] + list(incoming_labels),
                    format_func=lambda i: incoming_labels.get(
                        i, 'Choose an incoming card'
                    ),
                    key='incoming:' + mid,
                )

                incoming_preview = by_id.get(incoming_id)

                if not eligible:
                    st.warning(
                        'No Minors cards meet the saved trade restrictions. '
                        'Check eligibility, team, positions, and OVR.'
                    )

                st.caption(
                    'Reuses this card’s ID and stats. '
                    'It stays in Minors until arranged.'
                )

        if (
            kind == 'acquire'
            and acquisition_method == 'Existing card from Minors'
        ):
            eligible = [
                p
                for p in players
                if p['area'] == 'minors'
                and not incoming_card_errors(repo, fid, move, p)
            ]

            incoming_labels = {
                p['id']: player_label(p)
                for p in eligible
            }

            incoming_id = st.selectbox(
                'Incoming card from Minors',
                [None] + list(incoming_labels),
                format_func=lambda i: incoming_labels.get(
                    i, 'Choose an incoming card'
                ),
                key='incoming:' + mid,
            )

            incoming_preview = by_id.get(incoming_id)

            if not eligible:
                st.warning(
                    'No Minors cards meet this reward’s saved restrictions. '
                    'Check Event eligibility and card details.'
                )

            st.caption(
                'Reuses the existing card and stats. '
                'It stays in Minors until arranged.'
            )

        acquire_upgrade = (
            kind == 'acquire'
            and acquisition_method == 'Upgrade an existing player’s card'
        )

        needs_card = (
            (
                kind == 'acquire'
                and acquisition_method != 'Existing card from Minors'
            )
            or (kind == 'trade' and not existing_trade)
            or (kind in ['upgrade', 'downgrade'] and not fallback)
        )

        if needs_card:
            changing = (
                kind in ['upgrade', 'downgrade']
                or acquire_upgrade
            )

            seed = template(move, selected, changing)

            entry = st.radio(
                'Card entry method',
                ['Fill in fields', 'Paste JSON'],
                key='entry_method:' + mid,
            )

            quantity = (
                rules.get('quantity', 1)
                if kind == 'acquire' else 1
            )

            if entry == 'Fill in fields':
                incoming_cards = []

                for index in range(quantity):
                    st.markdown(f'**Card {index + 1} details**')

                    incoming_cards.append(
                        card_fields(
                            seed,
                            mid + ':card:' + str(index),
                            changing,
                        )
                    )

                incoming_preview = incoming_cards[0]

            else:
                value = (
                    seed
                    if changing
                    else [dict(seed) for _ in range(quantity)]
                )

                incoming_json = st.text_area(
                    'Card JSON',
                    value=json.dumps(value, indent=2),
                    height=280,
                    key='json:' + mid,
                )

                try:
                    incoming_cards = parse_cards(incoming_json)
                    incoming_preview = incoming_cards[0]
                except RuleError as exc:
                    field_errors.append(str(exc))

            if changing and not acquire_upgrade:
                next_confirmed = st.checkbox(
                    'I verified this is the next available '
                    + ('lower' if kind == 'downgrade' else 'higher')
                    + '-rated Event-legal version of the recipient.',
                    key='next:' + mid,
                )

                st.caption(
                    'Updates the existing player entry and preserves stats. '
                    'New artwork details are optional; old version '
                    'artwork is cleared when omitted.'
                )

            elif acquire_upgrade:
                st.caption(
                    'Enter the higher-rated version. The player stays '
                    'in their current roster slot and keeps their stats. '
                    'Old artwork is cleared when new artwork details '
                    'are omitted.'
                )

            else:
                st.caption(
                    'New cards enter Minors. Arrange them '
                    'afterward in Roster Manager.'
                )

        if selected or incoming_preview:
            left, right = st.columns(2)

            with left:
                show_card(
                    selected,
                    'Outgoing card'
                    if kind in ['trade', 'dfa', 'demote']
                    else 'Current / selected card',
                )

            with right:
                show_card(
                    incoming_preview,
                    'Incoming / new version'
                    if incoming_preview else 'Next step',
                )

    notes = st.text_area(
        'Resolution notes / restriction verification',
        key='notes:' + mid,
    )

    confirm = st.checkbox(
        'I verified the players, action, '
        'and applicable Event restrictions.',
        key='confirm:' + mid,
    )

    payload = dict(
        action=action,
        notes=notes,
        target_id=target,
        new_player=None,
        replace_tag=replacement,
        confirmed=confirm,
        cancel_move_id=cancel_id,
        max_card_confirmed=max_confirmed,
        incoming_player_id=None,
        upgrade_player_id=None,
        no_lower_card_confirmed=lower_confirmed,
        next_card_confirmed=next_confirmed,
    )

    if action == 'resolved':
        payload['incoming_player_id'] = (
            incoming_id if kind in ['trade', 'acquire'] else None
        )

        payload['upgrade_player_id'] = (
            upgrade_pid if kind == 'acquire' else None
        )

        if incoming_cards is not None:
            cards = [
                dict(card, area='minors')
                for card in incoming_cards
            ]

            payload['new_player'] = (
                cards
                if kind == 'acquire'
                and acquisition_method == 'Add a new card'
                else cards[0]
                if len(cards) == 1
                else cards
            )

    signature = hashlib.sha256(
        json.dumps(
            {
                'payload': payload,
                'json': incoming_json,
            },
            sort_keys=True,
            allow_nan=False,
        ).encode()
    ).hexdigest()

    review_key = 'move_review:' + fid + ':' + mid

    if st.session_state.get(review_key) != signature:
        st.session_state.pop(review_key, None)

    for error in field_errors:
        st.error(error)

    if st.button(
        'Review this move',
        type='primary',
        key='review:' + mid,
    ):
        try:
            if field_errors:
                raise RuleError(field_errors[0])

            if not notes.strip() or not confirm:
                raise RuleError(
                    'Enter notes and confirm your selections '
                    'before reviewing.'
                )

            if action == 'resolved':
                if (
                    kind == 'trade'
                    and not incoming_id
                    and payload['new_player'] is None
                ):
                    raise RuleError(
                        'Choose an incoming card or enter its details.'
                    )

                if kind == 'acquire':
                    if (
                        acquisition_method == 'Existing card from Minors'
                        and not incoming_id
                    ):
                        raise RuleError(
                            'Choose an existing card from Minors.'
                        )

                    if (
                        acquisition_method
                        == 'Upgrade an existing player’s card'
                        and not upgrade_pid
                    ):
                        raise RuleError(
                            'Choose the existing player to upgrade.'
                        )

                if kind in ['upgrade', 'downgrade']:
                    if (
                        fallback
                        and not (max_confirmed or lower_confirmed)
                    ):
                        raise RuleError(
                            'Confirm that no qualifying '
                            'alternate card exists.'
                        )

                    if not fallback and not next_confirmed:
                        raise RuleError(
                            'Confirm the next available legal card.'
                        )

                if (
                    kind in ['cancel_elimination', 'save_dfa']
                    and not cancel_id
                ):
                    raise RuleError(
                        'Choose a consequence to cancel.'
                    )

                new = payload['new_player']

                if new is not None:
                    cards = (
                        new if isinstance(new, list) else [new]
                    )

                    expected = (
                        rules.get('quantity', 1)
                        if kind == 'acquire' else 1
                    )

                    if len(cards) != expected:
                        raise RuleError(
                            f'Provide exactly {expected} card(s).'
                        )

                    for card in cards:
                        if not str(card.get('name', '')).strip():
                            raise RuleError(
                                'Enter a player name for every card.'
                            )

                        if kind in ['trade', 'acquire']:
                            errors = (
                                incoming_card_errors(
                                    repo, fid, move, card
                                )
                                if kind == 'acquire'
                                else card_event_errors(
                                    card, settings(repo, fid)
                                )
                            )

                            if errors:
                                raise RuleError(' '.join(errors))

                if (
                    kind == 'acquire'
                    and acquisition_method
                    == 'Upgrade an existing player’s card'
                ):
                    if not isinstance(new, dict) or not selected:
                        raise RuleError(
                            'Enter one upgraded card for the selected player.'
                        )

                    if (
                        new.get('name', '').strip().casefold()
                        != selected['name'].strip().casefold()
                        or new.get('kind') != selected['kind']
                    ):
                        raise RuleError(
                            'The upgraded card must be '
                            'the same player and type.'
                        )

                    if (
                        type(new.get('ovr')) is not int
                        or new['ovr'] <= selected['ovr']
                    ):
                        raise RuleError(
                            'Enter a higher OVR for the upgraded version.'
                        )

                if kind == 'trade':
                    incoming = by_id.get(incoming_id) or new

                    if not selected:
                        raise RuleError(
                            'Choose an outgoing player.'
                        )

                    errors = trade_card_errors(
                        repo, fid, move, selected, incoming
                    )

                    if errors:
                        raise RuleError(' '.join(errors))

            review_lines(
                move,
                payload,
                by_id,
                moves,
                removal_pool,
            )

        except RuleError as exc:
            st.error(str(exc))

        else:
            st.session_state[review_key] = signature

    if st.session_state.get(review_key) == signature:
        with st.container(border=True):
            st.subheader('Review transaction')

            for line in review_lines(
                move,
                payload,
                by_id,
                moves,
                removal_pool,
            ):
                st.write('• ' + line)

            st.write('Notes: ' + notes)

            st.caption(
                'Nothing has been saved yet. Editing a selection '
                'requires a fresh review. The service rechecks '
                'the move when you apply it.'
            )

            if st.button(
                'Confirm and apply reviewed move',
                type='primary',
                key='apply:' + mid,
            ):
                try:
                    resolve_move(
                        repo,
                        fid,
                        mid,
                        **payload,
                    )

                except RuleError as exc:
                    st.error(str(exc))

                else:
                    st.session_state.pop(review_key, None)
                    st.rerun()
