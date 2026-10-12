import html
import math
import re
import unicodedata

import streamlit as st

from models.domain import State
from services.game_engine import start_run
from services.franchise_service import settings, audit
from services.stat_engine import aggregate, weekly_mvp_candidates
from ui.common import navigate, table, badges


def escape(value):
    return html.escape(str(value), quote=True)


def name_key(value):
    text = unicodedata.normalize(
        'NFKD', str(value or '').strip().casefold()
    )
    return ' '.join(
        ''.join(
            character for character in text
            if not unicodedata.combining(character)
        ).split()
    )


def player_art_url(player):
    cards = {
        ('lance berkman', 99, 'spotlight'):
            'f3ed2f8ef5616481987e95ce6cbb7e5c',
        ('mike trout', 99, 'awards'):
            'e84d5fa03896ff54cdadabf5d2ca8a7b',
        ('ozzie albies', 98, '2026 all-star'):
            '6bca0765db76ea057be8289cf7bb0af2',
        ('max muncy', 92, 'cityscapes'):
            '5fe05e1065c026ec88edd48e841c80a7',
        ('dustin may', 99, 'new threads'):
            '0136a957b1243dcd640122b066a34aa7',
        ('adley rutschman', 99, 'new threads'):
            '095405569042bf08e28ca0c411eac121',
        ('jose ramirez', 95, 'mural'):
            '56c113bcf0449e4c45679da6a9f521de',
    }
    legacy = {
        ('manny ramirez', 94): 'f5e8e6d59d01a65fa1a76fe3bc41d753',
        ('carlos beltran', 92): 'ae298137b980fa4713aa235891188659',
        ('luis lara', 96): 'b85163e6c27ffebaab0cfa52e6deb84d',
        ('daniel schneemann', 90): 'c4b6a635bc56b98c94d77a9188b2087b',
        ('ozzie albies', 89): '3b1a482628a2a10f81bb6e47b9ee4e2d',
        ('chase headley', 88): '0725dd19ed80c6cff262389a69fa379e',
        ('chase utley', 88): '16588688df24c071adf191b89717de13',
        ('cam schlittler', 98): 'ebb513f936b81fb5910c21d7687cbcad',
        ('anthony seigler', 67): '3675fe0474e7202d802666cb405a3ffa',
        ('junior caminero', 87): '5f74a86f361c5124d1ef06cbabad638e',
    }

    name = name_key(player.get('name'))
    overall = player.get('ovr')
    series = str(player.get('series') or '').strip().casefold()
    version = str(player.get('version') or '').strip().casefold()

    identifier = (
        cards.get((name, overall, series))
        or cards.get((name, overall, version))
        or legacy.get((name, overall))
    )
    if not identifier:
        saved = str(player.get('card_uuid') or '').strip()
        if re.fullmatch(r'[a-fA-F0-9]{32}', saved):
            identifier = saved

    if identifier:
        return (
            'https://cards.theshow.com/mlb26/'
            + identifier + '-baked-lg.webp'
        )
    return None


def add_styles():
    st.markdown(
        """
        <style>
        .broadcast-hero {
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:24px;
            padding:24px 30px;
            max-width:1200px;
            margin:0 auto 18px;
            min-height:245px;
            box-sizing:border-box;
            overflow:hidden;
            border:1px solid #543b31;
            border-top:4px solid #d92640;
            border-radius:16px;
            background:
                radial-gradient(
                    ellipse at 90% 10%,#9d233b55,transparent 50%
                ),
                repeating-linear-gradient(
                    125deg,transparent 0px,transparent 65px,
                    #ffffff03 66px,#ffffff03 68px
                ),
                linear-gradient(120deg,#171b25,#0c1018);
        }
        .broadcast-copy {
            flex:1;
            min-width:0;
        }
        .broadcast-eyebrow {
            color:#f3ce7d;
            font-size:12px;
            font-weight:800;
            letter-spacing:2px;
            text-transform:uppercase;
        }
        .broadcast-name {
            color:#fff3d0;
            font-size:clamp(28px,4vw,44px);
            font-weight:900;
            line-height:1.1;
            margin:10px 0 16px;
            overflow-wrap:anywhere;
        }
        .broadcast-stat-row {
            display:flex;
            flex-wrap:wrap;
            gap:10px;
        }
        .broadcast-stat {
            min-width:65px;
            padding:9px 14px;
            background:#080d16aa;
            border:1px solid #ffffff20;
            border-radius:9px;
            text-align:center;
        }
        .broadcast-stat strong {
            display:block;
            color:white;
            font-size:25px;
        }
        .broadcast-stat span {
            color:#c9cdd6;
            font-size:11px;
            letter-spacing:1px;
        }
        .broadcast-note {
            color:#bbc3d1;
            font-size:13px;
            margin-top:14px;
            line-height:1.5;
        }
        .broadcast-art {
            flex:0 0 145px;
            width:145px;
            height:205px;
            position:relative;
            display:grid;
            place-items:center;
        }
        .broadcast-art img {
            position:absolute;
            width:100%;
            height:100%;
            object-fit:contain;
            filter:drop-shadow(0 8px 16px #0008);
        }
        .broadcast-art-fallback {
            width:110px;
            height:145px;
            display:grid;
            place-items:center;
            color:#f3ce7d;
            border:1px solid #b88b43;
            border-radius:12px;
            background:linear-gradient(145deg,#321921,#121824);
            font-size:34px;
            font-weight:900;
        }
        .broadcast-score {
            background:linear-gradient(135deg,#1b202c,#10151e);
            border:1px solid #343a49;
            border-top:3px solid #d92640;
            border-radius:10px;
            padding:14px;
            min-height:95px;
            box-sizing:border-box;
        }
        .broadcast-score-label {
            color:#bfc5d1;
            font-size:11px;
            font-weight:700;
            letter-spacing:1px;
            margin-bottom:9px;
        }
        .broadcast-score-value {
            color:white;
            font-size:28px;
            line-height:1.15;
            font-weight:900;
        }
        .broadcast-next {
            border-left:4px solid #ff334f;
            padding:5px 0 5px 14px;
        }
        .broadcast-next strong {
            display:block;
            color:#ffb2be;
            font-size:12px;
            letter-spacing:2px;
            margin-bottom:5px;
        }
        .broadcast-next span {
            color:#d9dee7;
            font-size:14px;
        }
        .broadcast-tracker {
            display:grid;
            grid-template-columns:repeat(6,minmax(0,1fr));
            gap:8px;
            margin:12px 0;
        }
        .broadcast-step {
            padding:13px 6px;
            text-align:center;
            border:1px solid #343b49;
            background:#111721;
            border-radius:9px;
        }
        .broadcast-step-icon {
            font-size:20px;
            margin-bottom:7px;
        }
        .broadcast-step-name {
            color:#e4e8ee;
            font-size:12px;
            font-weight:700;
        }
        .broadcast-step-status {
            color:#8590a2;
            font-size:10px;
            margin-top:5px;
        }
        .broadcast-step.current {
            border-color:#e1b863;
            background:linear-gradient(140deg,#47351b,#1a1c22);
        }
        .broadcast-step.current .broadcast-step-status {
            color:#ffdc8c;
        }
        .broadcast-step.done {
            border-color:#35544d;
        }
        .broadcast-step.done .broadcast-step-status {
            color:#84d2b2;
        }
        @media(max-width:650px) {
            .broadcast-hero {
                padding:18px;
                gap:12px;
                min-height:215px;
            }
            .broadcast-art {
                flex-basis:95px;
                width:95px;
                height:140px;
            }
            .broadcast-art-fallback {
                width:85px;
                height:115px;
                font-size:27px;
            }
            .broadcast-stat {
                min-width:45px;
                padding:7px;
            }
            .broadcast-stat strong { font-size:20px; }
            .broadcast-tracker {
                grid-template-columns:repeat(3,minmax(0,1fr));
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def show_featured(repo, fid, franchise, run, players):
    candidates = (
        weekly_mvp_candidates(repo, fid, run['id'])
        if run else []
    )
    by_id = {player['id']: player for player in players}
    featured = candidates[0] if candidates else None
    player = by_id.get(featured['player_id']) if featured else None

    if not player:
        st.markdown(
            '<div class="broadcast-hero">'
            '<div class="broadcast-copy">'
            '<div class="broadcast-eyebrow">Franchise Headquarters</div>'
            '<div class="broadcast-name">'
            + escape(franchise['name'])
            + '</div><div class="broadcast-note">'
            'Your featured player appears after qualifying '
            'stats are saved for this week.'
            '</div></div></div>',
            unsafe_allow_html=True,
        )
        return

    totals = featured['totals']
    if player['kind'] == 'hitter':
        stats = [
            (totals.get('hr', 0), 'HR'),
            (totals.get('rbi', 0), 'RBI'),
            (f"{totals.get('ops', 0):.3f}", 'OPS'),
        ]
    else:
        stats = [
            (totals.get('ip', '0.0'), 'IP'),
            (totals.get('so', 0), 'K'),
            (f"{totals.get('era', 0):.2f}", 'ERA'),
        ]

    stat_html = ''.join(
        '<div class="broadcast-stat"><strong>'
        + escape(value)
        + '</strong><span>' + escape(label)
        + '</span></div>'
        for value, label in stats
    )
    tied = [
        candidate['name']
        for candidate in candidates
        if math.isclose(
            candidate['score'], featured['score'],
            rel_tol=1e-9, abs_tol=1e-9,
        )
    ]
    note = f"Weekly MVP score: {featured['score']:.2f}"
    if len(tied) > 1:
        note += ' · Shared lead: ' + ', '.join(tied)
    else:
        note += ' · Current score leader'
    note += ' · Final selection is yours.'

    initials = ''.join(
        word[0] for word in player['name'].split()[:2]
    ).upper()
    art = (
        '<div class="broadcast-art-fallback">'
        + escape(initials) + '</div>'
    )
    url = player_art_url(player)
    if url:
        art += (
            '<img src="' + escape(url) + '" alt="'
            + escape(player['name'])
            + '" decoding="async" '
            'onerror="this.style.display=\'none\'">'
        )

    st.markdown(
        '<div class="broadcast-hero">'
        '<div class="broadcast-copy">'
        '<div class="broadcast-eyebrow">Player of the Week Watch</div>'
        '<div class="broadcast-name">'
        + escape(player['name'])
        + '</div><div class="broadcast-stat-row">'
        + stat_html
        + '</div><div class="broadcast-note">'
        + escape(note)
        + '</div></div><div class="broadcast-art">'
        + art + '</div></div>',
        unsafe_allow_html=True,
    )


def leader_totals(rows, run_id=None):
    totals = {}
    for row in rows:
        if run_id is not None and row.get('run_id') != run_id:
            continue
        counters = totals.setdefault(
            row['player_id'], {'hr': 0, 'rbi': 0, 'so': 0}
        )
        for field in counters:
            counters[field] += row.get('line', {}).get(field, 0)
    return totals


def show_leaders(players, totals, empty_message):
    categories = [
        ('hitter', 'hr', 'Home runs', 'HR'),
        ('hitter', 'rbi', 'Runs batted in', 'RBI'),
        ('pitcher', 'so', 'Strikeouts', 'K'),
    ]

    for column, (kind, field, title, unit) in zip(
        st.columns(3), categories
    ):
        # Only disambiguate cards that actually appear in this category.
        candidates = [
            player for player in players
            if player['kind'] == kind
            and totals.get(player['id'], {}).get(field, 0) > 0
        ]
        counts = {}
        for player in candidates:
            key = name_key(player['name'])
            counts[key] = counts.get(key, 0) + 1

        grouped = {}
        for player in candidates:
            label = player['name']
            if counts[name_key(label)] > 1:
                label += (
                    f" ({player['ovr']} OVR · "
                    + str(player.get('series') or player.get('version') or 'Card')
                    + ')'
                )
            value = totals[player['id']][field]
            grouped.setdefault(value, []).append(label)

        values = sorted(grouped, reverse=True)[:3]
        with column:
            with st.container(border=True):
                if not values:
                    st.metric(title, 0)
                    st.caption(empty_message)
                    continue

                st.metric(title, values[0])
                names = sorted(grouped[values[0]], key=str.casefold)
                st.write(' · '.join(names))
                if len(names) > 1:
                    st.caption('Tied for first')

                if len(values) > 1:
                    st.divider()
                for place, value in enumerate(values[1:], start=2):
                    medal = '🥈' if place == 2 else '🥉'
                    names = sorted(grouped[value], key=str.casefold)
                    rank = f'Tied {place}' if len(names) > 1 else str(place)
                    st.caption(
                        f'{medal} {rank} · '
                        + ', '.join(names)
                        + f' — {value:g} {unit}'
                    )


def challenge_progress(repo, fid, challenge):
    if (
        challenge['status'] == 'waiting_next_run'
        or not challenge.get('metric')
    ):
        return None

    player = repo.get('players', challenge['player_id'])
    if not player:
        return None

    rid = challenge['run_id']
    game_id = None
    if challenge.get('scope') == 'next_game':
        games = repo.list('games', fid, rid)
        source = (
            repo.get('games', challenge['source_game'])
            if challenge.get('source_game') else None
        )
        games = [
            game for game in games
            if not source or game['number'] > source['number']
        ]
        if not games:
            return 0
        game_id = min(games, key=lambda game: game['number'])['id']

    totals = aggregate(repo, fid, player, rid, game_id)
    metric = challenge['metric']

    if metric == 'extra_base_hits':
        return sum(
            totals.get(field, 0)
            for field in ['doubles', 'triples', 'hr']
        )
    if metric == 'times_on_base':
        return sum(
            totals.get(field, 0)
            for field in ['h', 'bb', 'hbp']
        )
    return totals.get(metric, 0)


def show_challenges(repo, fid, run):
    challenges = [
        challenge
        for challenge in repo.list('challenges', fid)
        if challenge['status'] in [
            'active', 'awaiting_manual', 'waiting_next_run'
        ]
        or (
            run and challenge['run_id'] == run['id']
            and challenge['status'] in ['passed', 'failed']
        )
    ]

    st.markdown('### 🌱 Development & challenges')
    if not challenges:
        st.caption('No challenges to track right now.')
        return

    labels = {
        'h': 'hits', 'hr': 'home runs', 'rbi': 'RBI',
        'so': 'strikeouts', 'outs': 'outs recorded',
        'w': 'wins', 'sv': 'saves',
        'extra_base_hits': 'extra-base hits',
        'times_on_base': 'times on base',
    }
    statuses = {
        'active': 'In progress',
        'passed': 'Completed',
        'failed': 'Not achieved',
        'awaiting_manual': 'Needs confirmation',
        'waiting_next_run': 'Starts next week',
    }
    columns = st.columns(2)

    for index, challenge in enumerate(challenges):
        player = repo.get('players', challenge['player_id'])
        status = challenge['status']
        total = challenge_progress(repo, fid, challenge)
        goal = challenge.get('threshold', 1)
        unit = labels.get(
            challenge.get('metric'), challenge.get('metric', '')
        )

        with columns[index % 2]:
            with st.container(border=True):
                st.markdown(
                    '**' + (player['name'] if player else 'Player unavailable')
                    + '**'
                )
                if total is not None:
                    st.write(f'{total:g} / {goal:g} {unit}')
                    st.progress(
                        min(max(float(total) / goal, 0.0), 1.0)
                        if goal > 0 else 1.0
                    )
                st.caption(statuses.get(status, status))

                with st.expander('Goal & details'):
                    st.write(challenge['description'])
                    if status == 'waiting_next_run':
                        st.caption(
                            'Current-week stats do not count.'
                        )
                    else:
                        entry = repo.get('runs', challenge['run_id'])
                        week = (
                            entry.get('week_number', entry['number'])
                            if entry else '?'
                        )
                        scope = (
                            'Next qualifying game only'
                            if challenge.get('scope') == 'next_game'
                            else 'Entire week'
                        )
                        st.caption(f'Week {week} · {scope}')

                    reward = {
                        'tag': 'Franchise Tag',
                        'upgrade': 'Next available same-player card upgrade',
                    }.get(challenge.get('reward'), 'Player protection')
                    st.caption('Reward: ' + reward)

                    if (
                        status in ['active', 'awaiting_manual']
                        and not challenge.get('metric')
                    ):
                        st.caption(
                            'Requires evidence and offseason confirmation.'
                        )

    st.caption('Progress uses saved game stats only.')


def show_tracker(repo, fid, franchise, run):
    steps = [
        ('🏆', 'MVP'), ('🎡', 'Wheels'), ('❄️', 'Cold Bat'),
        ('📦', 'Moves'), ('⚾', 'Rebuild'), ('🛡️', 'Validate'),
    ]
    state = franchise['state']
    current = None
    complete = False

    if run and run.get('ended_at'):
        if state in [State.ENDED, State.MVP]:
            current = 0
        elif state in [State.ELIMINATION, State.MELTDOWN]:
            current = 1
        elif state == State.WHEEL:
            job = (
                franchise['queue'][0]
                if franchise.get('queue') else {}
            )
            if job.get('wheel_id') == 'mvp':
                current = 0
            elif job.get('wheel_id') == 'cold_bat':
                current = 2
            elif run.get('cold_bat_decision'):
                current = 3
            else:
                current = 1
        elif state == State.MOVES:
            cold_enabled = bool(
                repo.get('wheels', f'{fid}:cold_bat')
            )
            current = (
                2
                if cold_enabled and not run.get('cold_bat_decision')
                else 3
            )
        elif state == State.REBUILD:
            current = 4
        elif state == State.VALIDATION:
            current = 5
        elif state == State.READY:
            complete = True

    st.markdown('### Between-week tracker')
    if complete:
        st.caption('Offseason complete · Ready for the next week.')
    elif current is None:
        st.caption('Unlocks when this week ends.')
    else:
        st.caption('Your current stage is highlighted.')

    cells = []
    for index, (icon, name) in enumerate(steps):
        if complete or (current is not None and index < current):
            style, status = 'done', 'Complete'
        elif index == current:
            style, status = 'current', 'Current'
        else:
            style, status = '', 'Pending'

        cells.append(
            '<div class="broadcast-step ' + style + '">'
            '<div class="broadcast-step-icon">' + icon
            + '</div><div class="broadcast-step-name">' + name
            + '</div><div class="broadcast-step-status">' + status
            + '</div></div>'
        )

    st.markdown(
        '<div class="broadcast-tracker">'
        + ''.join(cells) + '</div>',
        unsafe_allow_html=True,
    )


def edit_game_details(repo, fid, games):
    if not games:
        st.caption('No saved games yet.')
        return

    runs = {
        entry['id']: entry for entry in repo.list('runs', fid)
    }
    seasons = {
        season['id']: season for season in repo.list('seasons', fid)
    }
    labels = {}
    for game in games:
        entry = runs.get(game['run_id'])
        week = (
            entry.get('week_number', entry['number'])
            if entry else '?'
        )
        season = (
            seasons.get(entry.get('season_id'))
            if entry else None
        )
        prefix = f"Season {season['number']} · " if season else ''
        labels[game['id']] = (
            prefix + f"Week {week} · Game {game['number']} "
            + f"· {game['result']}"
        )

    gid = st.selectbox(
        'Choose a saved game', list(labels), format_func=labels.get,
        key='game_details_target:' + fid,
    )
    selected = repo.get('games', gid)

    with st.form('game_details:' + gid):
        opponent = st.text_input(
            'Opponent name', value=selected.get('opponent') or ''
        )
        include = st.checkbox(
            'Include scores',
            value=selected.get('team_score') is not None,
        )
        a, b = st.columns(2)
        own = a.number_input(
            'Your score', min_value=0,
            value=int(selected.get('team_score') or 0),
        )
        opp = b.number_input(
            'Opponent score', min_value=0,
            value=int(selected.get('opponent_score') or 0),
        )
        notes = st.text_area(
            'Game notes', value=selected.get('notes') or ''
        )
        if st.form_submit_button('Save game details'):
            with repo.transaction():
                current = repo.get('games', gid)
                valid = (
                    not include
                    or (
                        own != opp
                        and (own > opp) == (current['result'] == 'W')
                    )
                )
                if not valid:
                    st.error('Scores must match the saved W/L result.')
                else:
                    before = dict(current)
                    current.update(
                        opponent=opponent.strip(),
                        team_score=int(own) if include else None,
                        opponent_score=int(opp) if include else None,
                        notes=notes,
                    )
                    repo.put('games', current)
                    audit(
                        repo, fid, 'edit_game_details', before, current,
                        'Update opponent, scores, or game notes',
                        current['run_id'],
                    )
            if valid:
                st.rerun()


def render(repo, f):
    fid = f['id']
    run = (
        repo.get('runs', f['current_run'])
        if f['current_run'] else None
    )
    players = repo.list('players', fid)
    games = repo.list('games', fid)
    moves = repo.list('moves', fid)
    pending = [
        move for move in moves
        if move['status'] in ['pending', 'deferred']
    ]
    cfg = settings(repo, fid)

    add_styles()
    show_featured(repo, fid, f, run, players)

    threshold = next(
        (
            number
            for number in sorted(int(key) for key in cfg['milestones'])
            if not run or number > run['wins']
        ),
        None,
    )
    metrics = [
        (
            '⚾ WEEK RECORD',
            f"{run['wins']}–{run['losses']}" if run else '—',
        ),
        (
            '🏆 FRANCHISE RECORD',
            f"{sum(g['result'] == 'W' for g in games)}–"
            f"{sum(g['result'] == 'L' for g in games)}",
        ),
        ('📦 BANKED MOVES', len(pending)),
        (
            '🎡 NEXT MILESTONE',
            f'{threshold} wins' if threshold else 'All earned',
        ),
    ]
    for column, (label, value) in zip(st.columns(4), metrics):
        with column:
            st.markdown(
                '<div class="broadcast-score">'
                '<div class="broadcast-score-label">'
                + escape(label)
                + '</div><div class="broadcast-score-value">'
                + escape(value) + '</div></div>',
                unsafe_allow_html=True,
            )

    st.write('')
    state = f['state']
    if state == State.ACTIVE and run:
        remaining = max(run['max_losses'] - run['losses'], 0)
        detail = (
            f'Week in progress · {remaining} '
            + ('loss remaining' if remaining == 1 else 'losses remaining')
        )
        label, page = '⚾ ENTER NEXT GAME', 'pages/3_Game_Entry.py'
    elif state == State.WHEEL:
        detail = 'A required wheel is waiting for you.'
        label, page = '🎡 OPEN WHEEL ROOM', 'pages/4_Wheel_Room.py'
    elif state in [State.SETUP, State.READY]:
        detail = 'Review your roster, then start the next week.'
        label, page = '⚾ REVIEW ROSTER', 'pages/2_Roster_Manager.py'
    else:
        detail = 'Continue your between-week offseason.'
        label, page = '➡️ CONTINUE OFFSEASON', 'pages/6_Offseason.py'

    with st.container(border=True):
        a, b = st.columns([2, 1])
        with a:
            st.markdown(
                '<div class="broadcast-next">'
                '<strong>NEXT UP</strong><span>'
                + escape(detail) + '</span></div>',
                unsafe_allow_html=True,
            )
        with b:
            if st.button(
                label, type='primary', use_container_width=True,
                key='dashboard_next:' + fid,
            ):
                st.switch_page(page)

    if state in [State.SETUP, State.READY]:
        if st.button(
            'Validate and start next week',
            key='dashboard_start:' + fid,
        ):
            start_run(repo, fid)
            st.rerun()

    run_games = sorted(
        [
            game for game in games
            if run and game['run_id'] == run['id']
        ],
        key=lambda game: game['number'],
    )
    if run_games:
        last = run_games[-1]['result']
        streak = 0
        for game in reversed(run_games):
            if game['result'] != last:
                break
            streak += 1

        streak_text = (
            f'🔥 {streak}-game winning streak'
            if last == 'W'
            else f'⚾ {streak}-game losing streak'
        )
        if run and threshold:
            remaining = threshold - run['wins']
            streak_text += (
                f" · {remaining} more "
                f"{'win' if remaining == 1 else 'wins'} "
                'until the next milestone'
            )
        st.caption(streak_text)

    if run and threshold:
        st.progress(min(max(run['wins'] / threshold, 0.0), 1.0))

    stats = repo.list('stats', fid)
    st.subheader('Clubhouse Leaders')
    st.caption('This week · Tied players share a place.')
    if run:
        show_leaders(
            players, leader_totals(stats, run['id']),
            'Waiting for the first mark',
        )
    else:
        st.caption('Start a week to see your clubhouse leaders.')

    week_tab, offseason_tab, franchise_tab, manage_tab = st.tabs([
        '⚾ This Week',
        '🎡 Offseason',
        '🏆 Franchise',
        '✏️ Manage',
    ])

    with week_tab:
        show_challenges(repo, fid, run)

        st.markdown('### Recent games')
        recent = list(reversed(run_games))[:5]
        if not recent:
            st.caption('Your first saved game will appear here.')
        else:
            table([
                {
                    'Game': game['number'],
                    'Result': 'Win' if game['result'] == 'W' else 'Loss',
                    'Score': (
                        f"{game['team_score']}–{game['opponent_score']}"
                        if game.get('team_score') is not None
                        and game.get('opponent_score') is not None
                        else 'Not recorded'
                    ),
                    'Opponent': game.get('opponent') or '—',
                }
                for game in recent
            ])
            noted = [game for game in recent if game.get('notes')]
            if noted:
                with st.expander('Recent game notes'):
                    for game in noted:
                        st.markdown(f"**Game {game['number']}**")
                        st.write(game['notes'])

    with offseason_tab:
        show_tracker(repo, fid, f, run)
        if state not in [State.ACTIVE, State.SETUP, State.READY]:
            navigate('Continue offseason', 'Offseason')

        st.markdown('### 📦 Banked moves')
        if pending:
            table([
                {
                    'Move': move['description'],
                    'Action': move['type'].replace('_', ' ').title(),
                    'Status': (
                        'Saved for later'
                        if move['status'] == 'deferred'
                        else 'Waiting for offseason'
                    ),
                }
                for move in pending
            ])
            navigate('Open Banked Moves', 'Banked Moves')
        else:
            st.caption('No banked moves waiting.')

        spins = repo.list('spins', fid)
        if spins:
            st.caption('Latest wheel: ' + spins[-1]['result']['text'])

    with franchise_tab:
        st.markdown('### 🏆 All-Time Franchise Leaders')
        st.caption(
            'Saved stats across every week and season, '
            'including former players.'
        )
        show_leaders(
            players, leader_totals(stats), 'No saved stats yet'
        )

        with st.expander('Player status & reserve pool'):
            rows = []
            for player in players:
                status = badges(repo, fid, player)
                if status:
                    rows.append({
                        'Player': player['name'],
                        'OVR': player['ovr'],
                        'Status': status,
                    })
            table(rows)
            navigate('Open Roster Manager', 'Roster Manager')

    with manage_tab:
        st.markdown('### Edit saved game details')
        st.caption(
            'Update opponent names, scores, and notes. '
            'Changes are saved with an audit record.'
        )
        edit_game_details(repo, fid, games)

        st.markdown('### Other tools')
        navigate('Game and stat corrections / backups', 'Settings')
        navigate('Manage roster', 'Roster Manager')
