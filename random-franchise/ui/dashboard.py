import html

import streamlit as st

from models.domain import State
from services.game_engine import start_run
from services.franchise_service import settings, audit
from services.stat_engine import aggregate
from ui.common import navigate, table, badges


def challenge_progress(repo, fid, challenge):
    """Read the same saved stat scope used by challenge evaluation."""
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
        game_id = min(
            games, key=lambda game: game['number']
        )['id']

    return aggregate(
        repo, fid, player, rid, game_id
    ).get(challenge['metric'], 0)


def show_challenges(repo, fid, run):
    st.subheader('Challenge progress')
    st.caption(
        'Progress updates from saved game stats. '
        'Unsaved drafts are not included.'
    )

    challenges = [
        challenge
        for challenge in repo.list('challenges', fid)
        if challenge['status'] in [
            'active', 'awaiting_manual', 'waiting_next_run'
        ]
        or (
            run
            and challenge['run_id'] == run['id']
            and challenge['status'] in ['passed', 'failed']
        )
    ]

    if not challenges:
        st.info('No challenges to track right now.')
        return

    labels = {
        'h': 'hits',
        'hr': 'HR',
        'rbi': 'RBI',
        'so': 'strikeouts',
        'outs': 'outs recorded',
        'w': 'wins',
        'sv': 'saves',
    }
    statuses = {
        'active': 'In progress',
        'passed': 'Completed',
        'failed': 'Not achieved',
        'awaiting_manual': 'Needs confirmation',
        'waiting_next_run': 'Starts next week',
    }

    for challenge in challenges:
        player = repo.get('players', challenge['player_id'])

        with st.container(border=True):
            st.subheader(
                player['name'] if player else 'Player unavailable'
            )
            st.write(challenge['description'])

            status = challenge['status']
            total = challenge_progress(repo, fid, challenge)

            if total is not None:
                goal = challenge.get('threshold', 1)
                unit = labels.get(
                    challenge['metric'], challenge['metric']
                )
                st.write(
                    f"**{total:g} / {goal:g} {unit}** · "
                    + statuses.get(status, status)
                )
                st.progress(
                    min(max(float(total) / goal, 0.0), 1.0)
                    if goal > 0 else 1.0
                )

                if status == 'active':
                    remaining = max(goal - total, 0)
                    st.caption(
                        f'{remaining:g} more {unit} needed.'
                        if remaining
                        else 'Goal reached in saved stats; '
                             'check the challenge status.'
                    )
            else:
                st.write(statuses.get(status, status))
                if (
                    status in ['active', 'awaiting_manual']
                    and not challenge.get('metric')
                ):
                    st.caption(
                        'This challenge requires evidence and '
                        'confirmation during offseason.'
                    )

            if status == 'waiting_next_run':
                st.caption(
                    'Current-week stats do not count toward '
                    'this upcoming challenge.'
                )
            else:
                scope = (
                    'next qualifying game only'
                    if challenge.get('scope') == 'next_game'
                    else 'whole week'
                )
                target_run = repo.get('runs', challenge['run_id'])
                week = (
                    target_run.get(
                        'week_number', target_run['number']
                    )
                    if target_run else '?'
                )
                st.caption(f'Week {week} · {scope}')

            reward = {
                'tag': 'Franchise Tag',
                'upgrade': 'Next available same-player card upgrade',
            }.get(challenge.get('reward'), 'Player protection')
            st.caption('Reward: ' + reward)

            pending_reward = repo.get(
                'moves', 'challenge:' + challenge['id']
            )
            if (
                status == 'passed'
                and pending_reward
                and pending_reward['status'] == 'pending'
            ):
                st.info(
                    'Challenge completed. Resolve the earned reward '
                    'in Banked Moves during offseason.'
                )


def leader_totals(stat_rows, run_id=None):
    """Sum only the counters needed by the leader cards."""
    totals = {}

    for row in stat_rows:
        if run_id is not None and row.get('run_id') != run_id:
            continue

        player_id = row['player_id']
        counters = totals.setdefault(
            player_id, {'hr': 0, 'rbi': 0, 'so': 0}
        )
        line = row.get('line', {})
        for field in counters:
            counters[field] += line.get(field, 0)

    return totals


def show_leader_cards(players, totals, empty_message):
    categories = [
        ('hitter', 'hr', 'Home runs', 'HR'),
        ('hitter', 'rbi', 'Runs batted in', 'RBI'),
        ('pitcher', 'so', 'Strikeouts', 'K'),
    ]

    # Distinguish different card entries with the same player name.
    name_counts = {}
    for player in players:
        name = player['name'].strip().casefold()
        name_counts[name] = name_counts.get(name, 0) + 1

    def player_label(player):
        name = player['name']
        if name_counts.get(name.strip().casefold(), 0) > 1:
            card = (
                player.get('series')
                or player.get('version')
                or 'Card'
            )
            return f"{name} ({player['ovr']} OVR · {card})"
        return name

    columns = st.columns(3)

    for column, (kind, field, label, unit) in zip(
        columns, categories
    ):
        grouped = {}

        for player in players:
            if player['kind'] != kind:
                continue

            value = totals.get(player['id'], {}).get(field, 0)
            if value > 0:
                grouped.setdefault(value, []).append(
                    player_label(player)
                )

        # Each distinct positive total is one place.
        top_values = sorted(grouped, reverse=True)[:3]

        with column:
            with st.container(border=True):
                if not top_values:
                    st.metric(label, 0)
                    st.write(empty_message)
                    continue

                best = top_values[0]
                leaders = sorted(
                    grouped[best], key=str.casefold
                )
                st.metric(label, best)
                st.write(', '.join(leaders))

                if len(leaders) > 1:
                    st.caption('Tied for first')

                if len(top_values) > 1:
                    st.divider()

                for place, value in enumerate(
                    top_values[1:], start=2
                ):
                    names = sorted(
                        grouped[value], key=str.casefold
                    )
                    medal = '🥈' if place == 2 else '🥉'
                    place_label = (
                        f'Tied {place}'
                        if len(names) > 1 else str(place)
                    )
                    st.caption(
                        f"{medal} {place_label} · "
                        + ', '.join(names)
                        + f' — {value:g} {unit}'
                    )


def render(repo, f):
    fid = f['id']
    run = (
        repo.get('runs', f['current_run'])
        if f['current_run'] else None
    )

    st.markdown(
        '<div style="'
        'background:linear-gradient(120deg,#990019,#171717);'
        'border-left:6px solid #ff334f;'
        'border-radius:14px;padding:28px;margin-bottom:20px;'
        'color:white;">'
        '<div style="font-size:12px;letter-spacing:3px;'
        'font-weight:bold;color:#ffb3bf;">'
        'FRANCHISE HEADQUARTERS</div>'
        '<div style="font-size:34px;font-weight:bold;'
        'margin:12px 0;">'
        + html.escape(f['name'])
        + '</div><div style="color:#eeeeee;">'
        + html.escape(f['event'])
        + '</div></div>',
        unsafe_allow_html=True,
    )

    if run:
        week = run.get('week_number', run['number'])
        st.caption(f'Week {week} · Your next chapter')

    games = repo.list('games', fid)
    players = repo.list('players', fid)

    run_games = sorted(
        [
            game for game in games
            if run and game['run_id'] == run['id']
        ],
        key=lambda game: game['number'],
    )

    if run_games:
        last_result = run_games[-1]['result']
        streak = 0

        for game in reversed(run_games):
            if game['result'] != last_result:
                break
            streak += 1

        if last_result == 'W':
            st.success(
                f'🔥 On a roll: {streak}-game winning streak'
            )
        else:
            st.info(
                f'⚾ Time to bounce back: '
                f'{streak}-game losing streak'
            )

    pending = [
        move for move in repo.list('moves', fid)
        if move['status'] in ['pending', 'deferred']
    ]

    threshold = next(
        (
            number
            for number in sorted(
                int(key)
                for key in settings(repo, fid)['milestones']
            )
            if not run or number > run['wins']
        ),
        None,
    )

    def scoreboard_card(column, label, value, featured=False):
        background = '#35101a' if featured else '#191c24'
        with column:
            st.markdown(
                '<div style="'
                f'background:{background};'
                'border:1px solid #49303a;'
                'border-top:4px solid #ff334f;'
                'border-radius:12px;padding:18px;'
                'min-height:130px;box-sizing:border-box;">'
                '<div style="color:#c7c9d3;font-size:13px;'
                'font-weight:600;margin-bottom:12px;">'
                + html.escape(label)
                + '</div>'
                '<div style="color:white;font-size:34px;'
                'font-weight:800;line-height:1.2;">'
                + html.escape(str(value))
                + '</div></div>',
                unsafe_allow_html=True,
            )

    a, b, c, d = st.columns(4)
    scoreboard_card(
        a,
        '⚾ WEEK RECORD',
        f"{run['wins']}–{run['losses']}" if run else '—',
        featured=True,
    )
    scoreboard_card(
        b,
        '🏆 FRANCHISE RECORD',
        f"{sum(game['result'] == 'W' for game in games)}–"
        f"{sum(game['result'] == 'L' for game in games)}",
    )
    scoreboard_card(c, '📦 BANKED MOVES', len(pending))
    scoreboard_card(
        d,
        '🎡 NEXT MILESTONE',
        f'{threshold} wins' if threshold else 'All earned',
    )

    st.write('')

    if run and threshold:
        remaining = threshold - run['wins']
        st.markdown(
            f"**🎡 {remaining} more "
            f"{'win' if remaining == 1 else 'wins'} "
            "until your next milestone wheel**"
        )
        st.progress(
            min(max(run['wins'] / threshold, 0.0), 1.0)
        )
    elif run:
        st.caption(
            '🏆 Every configured win milestone has been reached.'
        )

    if f['state'] == State.ACTIVE:
        if st.button(
            '⚾ ENTER NEXT GAME',
            type='primary',
            use_container_width=True,
        ):
            st.switch_page('pages/3_Game_Entry.py')
    elif f['state'] == State.WHEEL:
        navigate('🎡 Spin required wheel', 'Wheel Room')
    elif f['state'] in [State.SETUP, State.READY]:
        navigate('Build / inspect roster', 'Roster Manager')
        if st.button(
            'Validate and start next week',
            type='primary',
        ):
            start_run(repo, fid)
            st.rerun()
    else:
        navigate('Continue offseason', 'Offseason')

    # Read saved stats once for both sets of leader cards.
    stat_rows = repo.list('stats', fid)

    st.subheader('Clubhouse Leaders')
    st.caption(
        'Current-week stats · Places use the top three distinct '
        'positive totals. Tied players share a place.'
    )

    if run:
        show_leader_cards(
            players,
            leader_totals(stat_rows, run['id']),
            'Waiting for the first mark',
        )
    else:
        st.caption(
            'Start a week to see your clubhouse leaders.'
        )

    with st.expander(
        '🏆 All-Time Franchise Leaders',
        expanded=True,
    ):
        st.caption(
            'Saved stats across every week and season, including '
            'former players. Tied players share a place.'
        )
        show_leader_cards(
            players,
            leader_totals(stat_rows),
            'No saved stats yet',
        )

    st.subheader('Franchise status')
    status_rows = []
    for player in players:
        status = badges(repo, fid, player)
        if status:
            status_rows.append({
                'Player': player['name'],
                'Status': status,
            })
    table(status_rows)

    show_challenges(repo, fid, run)

    st.subheader('From the dugout')
    recent = sorted(
        [
            game for game in games
            if run and game['run_id'] == run['id']
        ],
        key=lambda game: game['number'],
        reverse=True,
    )[:5]

    if not recent:
        st.caption('Your first saved game will appear here.')

    for game in recent:
        with st.container(border=True):
            outcome = 'WIN' if game['result'] == 'W' else 'LOSS'
            st.write(f"Game {game['number']} · {outcome}")
            if game.get('opponent'):
                st.caption('Opponent: ' + game['opponent'])
            if game.get('notes'):
                st.write(game['notes'])

    with st.expander('Edit saved game details'):
        if not games:
            st.info('No saved games yet.')
        else:
            runs_by_id = {
                entry['id']: entry
                for entry in repo.list('runs', fid)
            }
            game_labels = {}

            for game in games:
                entry = runs_by_id.get(game['run_id'])
                week = (
                    entry.get('week_number', entry['number'])
                    if entry else '?'
                )
                season = (
                    repo.get('seasons', entry['season_id'])
                    if entry and entry.get('season_id')
                    else None
                )
                season_label = (
                    f"Season {season['number']} · "
                    if season else ''
                )
                game_labels[game['id']] = (
                    season_label
                    + f"Week {week} · Game {game['number']} "
                    + f"· {game['result']}"
                )

            selected_id = st.selectbox(
                'Choose a saved game',
                list(game_labels),
                format_func=game_labels.get,
                key='game_details_target:' + fid,
            )
            selected = repo.get('games', selected_id)

            with st.form('game_details:' + selected_id):
                opponent = st.text_input(
                    'Opponent name',
                    value=selected.get('opponent') or '',
                )
                include_scores = st.checkbox(
                    'Include scores',
                    value=selected.get('team_score') is not None,
                )
                a, b = st.columns(2)
                own = a.number_input(
                    'Your score',
                    min_value=0,
                    value=int(selected.get('team_score') or 0),
                )
                opp = b.number_input(
                    'Opponent score',
                    min_value=0,
                    value=int(selected.get('opponent_score') or 0),
                )
                notes = st.text_area(
                    'Game notes',
                    value=selected.get('notes') or '',
                )

                if st.form_submit_button('Save game details'):
                    with repo.transaction():
                        current = repo.get('games', selected_id)
                        scores_valid = (
                            not include_scores
                            or (
                                own != opp
                                and (own > opp)
                                == (current['result'] == 'W')
                            )
                        )

                        if not scores_valid:
                            st.error(
                                'Scores must match the saved W/L result.'
                            )
                        else:
                            before = dict(current)
                            current.update(
                                opponent=opponent.strip(),
                                team_score=(
                                    int(own) if include_scores else None
                                ),
                                opponent_score=(
                                    int(opp) if include_scores else None
                                ),
                                notes=notes,
                            )
                            repo.put('games', current)
                            audit(
                                repo,
                                fid,
                                'edit_game_details',
                                before,
                                current,
                                'Update opponent, scores, or game notes',
                                current['run_id'],
                            )

                    if scores_valid:
                        st.rerun()

    st.subheader('📦 Next Week Moves')
    table([
        {
            'Move': move['description'],
            'Type': move['type'],
            'Status': move['status'],
        }
        for move in pending[:8]
    ])

    spins = repo.list('spins', fid)
    if spins:
        st.info('Latest wheel: ' + spins[-1]['result']['text'])
