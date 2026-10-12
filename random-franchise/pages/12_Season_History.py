import html
import json

import streamlit as st
import streamlit.components.v1 as components

from models.domain import RuleError, now
from services.franchise_service import audit
from services.stat_engine import (
    aggregate_season,
    mvp_score,
    PITCHER_BASELINE_ER_PER_THREE_INNINGS,
)
from ui.common import run_page, table
from ui.wheel_room import card_url, stadium_url


def season_header(season):
    background = stadium_url()
    status = (
        'CURRENT SEASON'
        if season['status'] == 'active'
        else 'COMPLETED SEASON'
    )

    st.markdown(
        '<div style="padding:28px;border:1px solid #744639;'
        'border-top:4px solid #ff334f;border-radius:14px;'
        'margin:12px 0 20px;background-color:#171b26;'
        'background-image:linear-gradient(90deg,rgba(9,13,22,.94),'
        'rgba(9,13,22,.35)),url(&quot;'
        + background
        + '&quot;);background-size:cover;background-position:center;">'
        '<div style="color:#efc778;font-size:11px;font-weight:800;'
        'letter-spacing:3px;">SEASON '
        + str(season['number'])
        + ' • '
        + status
        + '</div>'
        '<div style="color:#fff0ce;font-size:32px;font-weight:900;'
        'margin-top:10px;">'
        + html.escape(season['name'])
        + '</div>'
        '<div style="color:#d3d9e5;font-size:13px;margin-top:8px;">'
        'The players, performances, and weeks that built this season.'
        '</div></div>',
        unsafe_allow_html=True,
    )


def stat_summary(candidate):
    totals = candidate['totals']

    if candidate['player']['kind'] == 'hitter':
        return (
            f"{totals['h']} H · {totals['hr']} HR · "
            f"{totals['rbi']} RBI · {totals['ops']:.3f} OPS"
        )

    return (
        f"{totals['ip']} IP · {totals['so']} K · "
        f"{totals['era']:.2f} ERA · {totals['whip']:.2f} WHIP"
    )


def assign_ranks(candidates):
    """Equal scores share a rank: for example, 1, 1, 3."""
    counts = {}

    for candidate in candidates:
        key = round(candidate['score'], 10)
        counts[key] = counts.get(key, 0) + 1

    previous = None
    rank = 0

    for index, candidate in enumerate(candidates, 1):
        key = round(candidate['score'], 10)

        if key != previous:
            rank = index

        candidate['rank'] = rank
        candidate['tied'] = counts[key] > 1
        previous = key


def rank_label(candidate):
    prefix = 'Tied #' if candidate.get('tied') else '#'
    return prefix + str(candidate['rank'])


def candidate_rows(candidates):
    return [
        {
            'Rank': rank_label(candidate),
            'Player': candidate['player']['name'],
            'Type': candidate['player']['kind'].title(),
            'Card': (
                str(candidate['player'].get('ovr', ''))
                + ' · '
                + str(
                    candidate['player'].get('series')
                    or candidate['player'].get('version')
                    or ''
                )
            ),
            'Season Value': round(candidate['score'], 2),
            'Performance': stat_summary(candidate),
        }
        for candidate in candidates
    ]


def trophy_display(featured, candidates, awarded=False):
    player = featured['player']

    other_candidates = [
        candidate
        for candidate in candidates
        if candidate['player']['id'] != player['id']
    ][:2]

    image = card_url(player)
    initials = ''.join(
        word[0] for word in player['name'].split()[:2]
    ).upper()

    art = (
        '<div class="fallback">'
        + html.escape(initials)
        + '</div>'
    )

    if image:
        art += (
            '<img src="'
            + html.escape(image, quote=True)
            + '" alt="'
            + html.escape(player['name'], quote=True)
            + '" onerror="this.style.display=\'none\'">'
        )

    heading = 'SEASON MVP' if awarded else 'SEASON MVP WATCH'

    note = (
        'Your saved season award.'
        if awarded
        else (
            'Top overall candidate • '
            'Final Season MVP has not been selected.'
        )
    )

    runners = ''

    for candidate in other_candidates:
        other = candidate['player']

        # These ranks describe scores, not saved runner-up awards.
        label = rank_label(candidate) + ' OVERALL CANDIDATE'

        runners += (
            '<div class="runner">'
            '<div class="eyebrow">'
            + label
            + '</div><div class="runner-name">'
            + html.escape(other['name'])
            + '</div><div class="small">'
            + html.escape(stat_summary(candidate))
            + '<br>Season Value '
            + f"{candidate['score']:.2f}"
            + '</div></div>'
        )

    metadata = (
        str(player.get('ovr', ''))
        + ' OVR · '
        + str(
            player.get('series')
            or player.get('version')
            or 'Card'
        )
    )

    body = (
        '<div class="trophy">'
        '<div class="feature">'
        '<div class="copy">'
        '<div class="eyebrow">🏆 '
        + heading
        + '</div><h1>'
        + html.escape(player['name'])
        + '</h1><div class="card-meta">'
        + html.escape(metadata)
        + '</div><div class="stats">'
        + html.escape(stat_summary(featured))
        + '</div><div class="value">Season Value '
        + f"{featured['score']:.2f}"
        + '</div><div class="small">'
        + html.escape(note)
        + '</div></div><div class="art">'
        + art
        + '</div></div>'
        + (
            '<div class="runners">' + runners + '</div>'
            if runners
            else ''
        )
        + '</div>'
    )

    css = """
    <style>
    body {
        margin: 0;
        font-family: Arial, sans-serif;
        color: #f4f0e6;
    }

    .trophy {
        padding: 26px;
        border: 1px solid #a98449;
        border-top: 4px solid #efc778;
        border-radius: 14px;
        background:
            radial-gradient(
                ellipse at right,
                #a4482338,
                transparent 65%
            ),
            linear-gradient(135deg, #27202c, #0c121c);
    }

    .feature {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 22px;
    }

    .copy {
        flex: 1;
        min-width: 0;
    }

    .eyebrow {
        color: #efc778;
        font-size: 10px;
        font-weight: bold;
        letter-spacing: 2px;
    }

    h1 {
        font-size: 36px;
        line-height: 1.1;
        color: #fff0ce;
        margin: 14px 0;
        overflow-wrap: anywhere;
    }

    .card-meta,
    .small {
        color: #bac5d6;
        font-size: 12px;
        line-height: 1.6;
    }

    .stats {
        font-size: 17px;
        font-weight: bold;
        margin: 18px 0 10px;
        line-height: 1.5;
    }

    .value {
        color: #efc778;
        font-size: 14px;
        margin-bottom: 12px;
    }

    .art {
        position: relative;
        flex: 0 0 145px;
        width: 145px;
        height: 210px;
        display: grid;
        place-items: center;
    }

    .art img {
        position: absolute;
        inset: 0;
        width: 100%;
        height: 100%;
        object-fit: contain;
        filter: drop-shadow(0 8px 16px #0008);
    }

    .fallback {
        width: 125px;
        height: 175px;
        border: 1px solid #efc778;
        border-radius: 9px;
        display: grid;
        place-items: center;
        font-size: 35px;
        color: #efc778;
        background: #1d2433;
    }

    .runners {
        display: flex;
        gap: 14px;
        margin-top: 22px;
        border-top: 1px solid #66533b;
        padding-top: 18px;
    }

    .runner {
        flex: 1;
        min-width: 0;
    }

    .runner-name {
        font-size: 17px;
        font-weight: bold;
        margin: 8px 0;
        color: #f4eedf;
    }

    @media(max-width:600px) {
        .trophy {
            padding: 18px;
        }

        h1 {
            font-size: 27px;
        }

        .art {
            flex-basis: 95px;
            width: 95px;
            height: 145px;
        }

        .fallback {
            width: 90px;
            height: 130px;
            font-size: 26px;
        }

        .stats {
            font-size: 14px;
        }

        .runners {
            flex-direction: column;
        }
    }
    </style>
    """

    components.html(css + body, height=440, scrolling=True)


def mvp_controls(repo, f, season, selected, eligible_players):
    fid = f['id']
    st.subheader('Select Season MVP')

    if season['status'] == 'active':
        st.info(
            'Select the final Season MVP after this season is completed.'
        )

    elif not eligible_players:
        st.info('Restore player stats before selecting a Season MVP.')

    else:
        candidate_ids = sorted(
            eligible_players,
            key=lambda pid: (
                eligible_players[pid]['name'],
                eligible_players[pid].get('ovr', 0),
                pid,
            ),
        )

        options = [None] + candidate_ids
        saved_mvp = season.get('mvp')

        def candidate_label(pid):
            if pid is None:
                return 'Choose a Season MVP'

            player = eligible_players[pid]

            return (
                player['name']
                + ' · '
                + str(player.get('ovr', ''))
                + ' OVR · '
                + player.get('series', '')
                + ' · '
                + player.get('version', '')
            )

        with st.form('season_mvp:' + fid + ':' + selected):
            chosen_mvp = st.selectbox(
                'Season MVP',
                options,
                index=(
                    options.index(saved_mvp)
                    if saved_mvp in options
                    else 0
                ),
                format_func=candidate_label,
            )

            reason = st.text_input(
                'Selection notes / reason',
                placeholder='Example: Led the season in HR, RBI, and OPS.',
            )

            confirmed_mvp = st.checkbox(
                'I confirm this MVP selection for the displayed season.'
            )

            st.caption(
                'Records the season award. It does not grant protection, '
                'a franchise tag, or an extra wheel spin.'
            )

            if st.form_submit_button(
                'Save Season MVP',
                type='primary',
            ):
                try:
                    if chosen_mvp is None:
                        raise RuleError('Choose a Season MVP.')

                    if not confirmed_mvp:
                        raise RuleError('Confirm the season and MVP choice.')

                    if not reason.strip():
                        raise RuleError('Enter a selection reason.')

                    with repo.transaction():
                        current_season = repo.get('seasons', selected)

                        if (
                            not current_season
                            or current_season['franchise_id'] != fid
                            or current_season['status'] == 'active'
                        ):
                            raise RuleError(
                                'Select a completed season in this franchise.'
                            )

                        player = repo.get('players', chosen_mvp)

                        if (
                            not player
                            or player['franchise_id'] != fid
                            or not aggregate_season(
                                repo, fid, player, selected
                            ).get('games', 0)
                        ):
                            raise RuleError(
                                'Choose a player with saved stats '
                                'in this season.'
                            )

                        before = dict(current_season)

                        current_season.update(
                            mvp=chosen_mvp,
                            mvp_selected_at=now(),
                            mvp_notes=reason.strip(),
                        )

                        repo.put('seasons', current_season)

                        audit(
                            repo,
                            fid,
                            'select_season_mvp',
                            before,
                            current_season,
                            reason.strip(),
                        )

                except RuleError as exc:
                    st.error(str(exc))

                else:
                    st.rerun()


def recovery_controls(repo, f, season, selected, seasons, weeks):
    fid = f['id']
    season_ids = [item['id'] for item in seasons]
    choices = {item['id']: item for item in seasons}

    with st.expander('Restore a completed historical week'):
        from services.historical_import import import_completed_week

        st.write(
            f"Import destination: Season {season['number']} "
            f"— {season['name']}"
        )

        st.caption(
            'Restores games and player stats without replaying wheels '
            'or rewards. Missing statistics remain marked as unavailable.'
        )

        upload = st.file_uploader(
            'Historical week JSON',
            type=['json'],
            key='historical_upload:' + fid + ':' + selected,
        )

        confirmed = st.checkbox(
            'I verified the selected season and week being restored.',
            key='historical_confirm:' + fid + ':' + selected,
        )

        if st.button(
            'Import historical week',
            disabled=upload is None or not confirmed,
            key='historical_import:' + fid + ':' + selected,
        ):
            try:
                payload = json.loads(
                    upload.getvalue().decode('utf-8-sig')
                )
                import_completed_week(repo, fid, selected, payload)

            except (ValueError, UnicodeError) as exc:
                st.exception(exc)

            except RuleError as exc:
                st.error(str(exc))

            else:
                st.rerun()

    with st.expander('Correct the season of an imported week'):
        from services.historical_import import move_historical_week

        imported = [
            week
            for week in weeks
            if week.get('recovered')
            and week.get('offseason_step') == 'historical_complete'
            and week['id'] != f.get('current_run')
        ]

        destinations = [
            sid for sid in season_ids if sid != selected
        ]

        if not imported:
            st.info('No imported historical weeks in this season to move.')

        elif not destinations:
            st.info('Another season is needed to move a week.')

        else:
            imported_by_id = {
                week['id']: week for week in imported
            }

            moving_id = st.selectbox(
                'Imported week to move',
                list(imported_by_id),
                format_func=lambda rid: (
                    f"Week {imported_by_id[rid]['week_number']} · "
                    f"{imported_by_id[rid]['wins']}–"
                    f"{imported_by_id[rid]['losses']}"
                ),
                key='move_week:' + fid + ':' + selected,
            )

            destination = st.selectbox(
                'Move to season',
                destinations,
                format_func=lambda sid: (
                    f"Season {choices[sid]['number']} · "
                    f"{choices[sid]['name']}"
                ),
                key='move_destination:' + fid + ':' + selected,
            )

            confirmed_move = st.checkbox(
                'I confirm moving this week and its stats to this season.',
                key='move_confirm:' + fid + ':' + selected,
            )

            if st.button(
                'Move imported week',
                disabled=not confirmed_move,
                key='move_apply:' + fid + ':' + selected,
            ):
                try:
                    move_historical_week(
                        repo, fid, moving_id, destination
                    )

                except RuleError as exc:
                    st.error(str(exc))

                else:
                    st.rerun()


def render(repo, f):
    fid = f['id']

    seasons = sorted(
        repo.list('seasons', fid),
        key=lambda item: item['number'],
    )

    if not seasons:
        st.info('No seasons have been created yet.')
        return

    season_ids = [season['id'] for season in seasons]
    choices = {season['id']: season for season in seasons}
    current = f.get('current_season')

    selected = st.selectbox(
        'Season to view',
        season_ids,
        index=season_ids.index(current) if current in season_ids else 0,
        format_func=lambda sid: (
            f"Season {choices[sid]['number']} · {choices[sid]['name']}"
        ),
        key='season_history:' + fid,
    )

    season = choices[selected]

    weeks = sorted(
        [
            run
            for run in repo.list('runs', fid)
            if run.get('season_id') == selected
        ],
        key=lambda run: run.get('week_number', run['number']),
    )

    week_ids = {week['id'] for week in weeks}

    games = [
        game
        for game in repo.list('games', fid)
        if game['run_id'] in week_ids
    ]

    players = repo.list('players', fid)
    player_map = {player['id']: player for player in players}

    season_header(season)

    a, b, c = st.columns(3)

    a.metric(
        'Season record',
        f"{sum(g['result'] == 'W' for g in games)}–"
        f"{sum(g['result'] == 'L' for g in games)}",
    )
    b.metric('Games recorded', len(games))
    c.metric('Weeks recorded', len(weeks))

    hitters = []
    pitchers = []
    candidates = []
    eligible_players = {}

    for player in players:
        totals = aggregate_season(repo, fid, player, selected)

        if not totals.get('games', 0):
            continue

        eligible_players[player['id']] = player

        card_label = (
            str(player.get('ovr', ''))
            + ' · '
            + str(
                player.get('series')
                or player.get('version')
                or ''
            )
        )

        # Use the exact function used by Weekly MVP.
        score = mvp_score(player['kind'], totals)

        if player['kind'] == 'hitter':
            hitters.append({
                'Player': player['name'],
                'Card': card_label,
                'Season Value': score,
                'GP': totals['games'],
                'PA': totals['pa'],
                'H': totals['h'],
                'HR': totals['hr'],
                'RBI': totals['rbi'],
                'Runs': totals['r'],
                'AVG': f"{totals['avg']:.3f}",
                'OPS': f"{totals['ops']:.3f}",
            })

        else:
            pitchers.append({
                'Player': player['name'],
                'Card': card_label,
                'Season Value': score,
                'GP': totals['games'],
                'IP': totals['ip'],
                'K': totals['so'],
                'ER': totals['er'],
                'ERA': f"{totals['era']:.2f}",
                'WHIP': f"{totals['whip']:.2f}",
                'Wins': totals['w'],
                'Saves': totals['sv'],
            })

        participated = (
            totals.get('pa', 0) > 0
            if player['kind'] == 'hitter'
            else totals.get('outs', 0) > 0
        )

        if participated:
            candidates.append({
                'player': player,
                'totals': totals,
                'score': score,
            })

    hitters.sort(
        key=lambda row: row['Season Value'],
        reverse=True,
    )
    pitchers.sort(
        key=lambda row: row['Season Value'],
        reverse=True,
    )
    candidates.sort(
        key=lambda row: (
            -row['score'],
            row['player']['name'].casefold(),
        ),
    )

    assign_ranks(candidates)

    trophy_tab, stats_tab, weeks_tab, manage_tab = st.tabs([
        '🏆 Trophy case',
        '📊 Season stats',
        '📅 Weekly results',
        '⚙️ Manage season',
    ])

    with trophy_tab:
        saved = next(
            (
                candidate
                for candidate in candidates
                if candidate['player']['id'] == season.get('mvp')
            ),
            None,
        )

        featured = saved or (
            candidates[0] if candidates else None
        )

        if featured:
            trophy_display(
                featured,
                candidates,
                awarded=bool(saved),
            )

        else:
            st.info(
                'Restore or enter games to bring '
                'this season’s trophy case to life.'
            )

        if season.get('mvp') and not saved:
            award_player = player_map.get(season['mvp'])

            if award_player:
                st.success(
                    'Saved Season MVP: ' + award_player['name']
                )
            else:
                st.warning('The saved MVP player entry is unavailable.')

        if season.get('mvp_notes'):
            st.caption('Award notes: ' + season['mvp_notes'])

        st.caption(
            'Featured candidates are suggestions. '
            'Your saved Season MVP is always your choice. '
            'Hitters and pitchers share the Weekly MVP scoring system. '
            'Rankings use saved stats; missing box scores can affect them.'
        )

        st.markdown('**Overall Season MVP candidates**')
        table(candidate_rows(candidates[:5]))

        with st.expander('Past Season MVPs'):
            completed = [
                item
                for item in seasons
                if item['status'] != 'active'
            ]

            if not completed:
                st.info('Completed seasons will appear here.')

            else:
                columns = st.columns(3)

                for index, item in enumerate(completed):
                    with columns[index % 3]:
                        st.markdown(f"**Season {item['number']}**")
                        st.caption(item['name'])

                        winner = player_map.get(item.get('mvp'))

                        if winner:
                            image = card_url(winner)

                            if image:
                                st.image(image, width=110)

                            st.write('🏆 ' + winner['name'])

                        else:
                            st.caption(
                                'MVP not selected'
                                if not item.get('mvp')
                                else 'MVP entry unavailable'
                            )

    with stats_tab:
        st.subheader('Season statistics')

        st.caption(
            'Saved stats from all weeks in the selected season. '
            'Each card entry retains its own statistics.'
        )

        hitting_tab, pitching_tab = st.tabs([
            'Hitting',
            'Pitching',
        ])

        with hitting_tab:
            table(hitters)

        with pitching_tab:
            table(pitchers)

        with st.expander('Overall MVP leaderboard'):
            table(candidate_rows(candidates))

        with st.expander('How Season Value is calculated'):
            st.write(
                'Uses the same mvp_score function as Weekly MVP, applied '
                'to all saved stats in this season. Values accumulate '
                'across weeks; they are not per-game averages.'
            )

            st.write(
                'Hitters: 0.5 × singles + 0.8 × doubles + 1.1 × triples '
                '+ 1.4 × home runs + 0.3 × (walks + HBP) '
                '− 0.25 × (hitless at-bats + sacrifice flies) '
                '+ 0.2 × steals − 0.3 × caught stealing.'
            )

            baseline = PITCHER_BASELINE_ER_PER_THREE_INNINGS

            st.write(
                f'Pitchers: outs × {baseline:g} ÷ 9 − earned runs. '
                f'The current house baseline is {baseline:g} earned '
                'runs per three innings.'
            )

            st.caption(
                'Custom estimated run value, not WAR. Actual innings and '
                'ERA stay unchanged. Runs and RBI remain visible but '
                'are not added again to the hitter score. Ties remain ties. '
                'Changing the ranking does not replace a saved Season MVP.'
            )

    with weeks_tab:
        st.subheader('Weekly results')
        rows = []

        for week in weeks:
            weekly_mvp = player_map.get(week.get('mvp'))

            rows.append({
                'Week': week.get('week_number', week['number']),
                'Wins': week['wins'],
                'Losses': week['losses'],
                'Status': (
                    'Completed'
                    if week['ended_at']
                    else 'In progress'
                ),
                'Weekly MVP': (
                    weekly_mvp['name']
                    if weekly_mvp
                    else 'Not selected'
                ),
            })

        table(rows)

        with st.expander('Saved game results'):
            week_numbers = {
                week['id']: week.get('week_number', week['number'])
                for week in weeks
            }

            table([
                {
                    'Week': week_numbers[game['run_id']],
                    'Game': game['number'],
                    'Date': game.get('date', ''),
                    'Result': game['result'],
                    'Your score': game.get('team_score'),
                    'Opponent score': game.get('opponent_score'),
                    'Opponent': game.get('opponent', ''),
                }
                for game in sorted(
                    games,
                    key=lambda game: (
                        week_numbers[game['run_id']],
                        game['number'],
                    ),
                )
            ])

    with manage_tab:
        st.caption(
            f"Managing Season {season['number']} · {season['name']}"
        )

        mvp_controls(
            repo,
            f,
            season,
            selected,
            eligible_players,
        )

        recovery_controls(
            repo,
            f,
            season,
            selected,
            seasons,
            weeks,
        )


run_page('Season History', render, obs=False)
