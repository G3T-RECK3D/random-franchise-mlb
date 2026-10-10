import streamlit as st

from services.stat_engine import aggregate_season
from ui.common import run_page, table


def render(repo, f):
    fid = f['id']
    seasons = sorted(
        repo.list('seasons', fid),
        key=lambda season: season['number'],
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
            run for run in repo.list('runs', fid)
            if run.get('season_id') == selected
        ],
        key=lambda run: run.get('week_number', run['number']),
    )
    week_ids = {week['id'] for week in weeks}
    games = [
        game for game in repo.list('games', fid)
        if game['run_id'] in week_ids
    ]

    st.subheader(season['name'])
    st.caption(
        'Current season'
        if season['status'] == 'active'
        else 'Completed season'
    )

    a, b, c = st.columns(3)
    a.metric('Weeks recorded', len(weeks))
    b.metric('Games recorded', len(games))
    c.metric(
        'Season record',
        f"{sum(g['result'] == 'W' for g in games)}–"
        f"{sum(g['result'] == 'L' for g in games)}",
    )

    mvp = (
        repo.get('players', season['mvp'])
        if season.get('mvp')
        else None
    )
    if mvp:
        st.success('🏆 Season MVP: ' + mvp['name'])
    else:
        st.info('Season MVP has not been selected.')

    hitters = []
    pitchers = []

    for player in repo.list('players', fid):
        totals = aggregate_season(repo, fid, player, selected)
        if not totals.get('games', 0):
            continue

        if player['kind'] == 'hitter':
            score = (
                totals.get('tb', 0)
                + totals.get('bb', 0)
                + totals.get('hbp', 0)
                + totals.get('r', 0)
                + totals.get('rbi', 0)
                + totals.get('sb', 0)
                - totals.get('cs', 0)
            )
            hitters.append({
                'Player': player['name'],
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
            score = (
                totals.get('outs', 0)
                + totals.get('so', 0)
                - 3 * totals.get('er', 0)
                - totals.get('ha', 0)
                - totals.get('bb', 0)
            )
            pitchers.append({
                'Player': player['name'],
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

    hitters.sort(key=lambda row: row['Season Value'], reverse=True)
    pitchers.sort(key=lambda row: row['Season Value'], reverse=True)

    st.subheader('🏆 Season MVP candidates')
    st.caption(
        'Uses saved stats from every week in this season. '
        'Season Value uses the same contribution formula as Weekly MVP. '
        'Compare hitters and pitchers separately.'
    )

    if not hitters and not pitchers:
        st.info(
            'No player stats have been recorded for this season yet. '
            'Candidates will appear after games are entered or restored.'
        )
    else:
        st.markdown('**Top hitters**')
        table(hitters[:3])
        st.markdown('**Top pitchers**')
        table(pitchers[:3])

        with st.expander('All season hitting stats'):
            table(hitters)

        with st.expander('All season pitching stats'):
            table(pitchers)

    with st.expander('Restore a completed historical week'):
        import json
        from models.domain import RuleError
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
            except (ValueError, UnicodeError):
                st.error('The uploaded file is not valid JSON.')
            except RuleError as exc:
                st.error(str(exc))
            else:
                st.rerun()
    st.subheader('Weekly results')
    rows = []
    for week in weeks:
        weekly_mvp = (
            repo.get('players', week['mvp'])
            if week.get('mvp')
            else None
        )
        rows.append({
            'Week': week.get('week_number', week['number']),
            'Wins': week['wins'],
            'Losses': week['losses'],
            'Status': 'Completed' if week['ended_at'] else 'In progress',
            'Weekly MVP': (
                weekly_mvp['name'] if weekly_mvp else 'Not selected'
            ),
        })
    table(rows)


run_page('Season History', render, obs=False)
