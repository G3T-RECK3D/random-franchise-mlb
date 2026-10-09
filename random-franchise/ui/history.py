import streamlit as st
from services.stat_engine import aggregate
from ui.common import table

def render(repo,f):
    fid=f['id'];runs=repo.list('runs',fid);games=repo.list('games',fid);players=repo.list('players',fid)
    ended=[r for r in runs if r['ended_at']]
    a,b,c=st.columns(3)
    rank=lambda r:(r['wins'],-r['losses'])
    a.metric('Best run',f"{max(ended,key=rank)['wins']}–{max(ended,key=rank)['losses']}" if ended else '—')
    b.metric('Worst run',f"{min(ended,key=rank)['wins']}–{min(ended,key=rank)['losses']}" if ended else '—')
    streak=best=0
    for g in games:
        streak=streak+1 if g['result']=='W' else 0;best=max(best,streak)
    c.metric('Longest win streak',best)
    st.subheader('Event runs')
    table([{'Run':r['number'],'Event':r['event'],'W':r['wins'],'L':r['losses'],'Start':r['started_at'],'End':r['ended_at'],
            'MVP':repo.get('players',r['mvp'])['name'] if r['mvp'] else ''} for r in runs])
    st.subheader('🏆 MVP review')
    if runs:
        run_choices = sorted(
            runs, key=lambda item: item['number'], reverse=True
        )
        run_lookup = {item['id']: item for item in run_choices}
        selected_run_id = st.selectbox(
            'Run to review',
            list(run_lookup),
            format_func=lambda identifier: (
                f"Run {run_lookup[identifier]['number']} · "
                f"{run_lookup[identifier]['wins']}–"
                f"{run_lookup[identifier]['losses']}"
            ),
            key='history_mvp_run:' + fid,
        )
        selected_run = run_lookup[selected_run_id]

        saved_mvp = (
            repo.get('players', selected_run['mvp'])
            if selected_run.get('mvp') else None
        )
        if saved_mvp:
            st.success('Selected MVP: ' + saved_mvp['name'])
        elif selected_run.get('mvp'):
            st.info('The selected MVP’s player entry is unavailable.')
        else:
            st.info('No MVP has been selected for this run.')

        if not selected_run.get('ended_at'):
            st.caption('Run in progress—scores update as games are saved.')

        st.caption(
            'Run Value is a custom points score, not WAR. '
            'Hitter and pitcher scores are not calibrated against each other.'
        )

        participant_ids = {
            row['player_id']
            for row in repo.list('stats', fid, selected_run_id)
        }
        hitters = []
        pitchers = []

        for player_id in participant_ids:
            player = repo.get('players', player_id)
            if not player:
                continue
            totals = aggregate(repo, fid, player, selected_run_id)

            if player['kind'] == 'hitter':
                total_bases = (
                    totals.get('h', 0)
                    + totals.get('doubles', 0)
                    + 2 * totals.get('triples', 0)
                    + 3 * totals.get('hr', 0)
                )
                score = (
                    total_bases
                    + totals.get('bb', 0)
                    + totals.get('hbp', 0)
                    + totals.get('r', 0)
                    + totals.get('rbi', 0)
                    + totals.get('sb', 0)
                    - totals.get('cs', 0)
                )
                hitters.append({
                    'Player': player['name'],
                    'Run Value': score,
                    'PA': totals.get('pa', 0),
                    'H': totals.get('h', 0),
                    'HR': totals.get('hr', 0),
                    'RBI': totals.get('rbi', 0),
                    'Runs': totals.get('r', 0),
                    'OPS': f"{totals.get('ops', 0):.3f}",
                })
            else:
                outs = int(totals.get('outs', 0))
                score = (
                    outs
                    + totals.get('so', 0)
                    - 3 * totals.get('er', 0)
                    - totals.get('ha', 0)
                    - totals.get('bb', 0)
                )
                pitchers.append({
                    'Player': player['name'],
                    'Run Value': score,
                    'IP': f"{outs // 3}.{outs % 3}",
                    'K': totals.get('so', 0),
                    'ER': totals.get('er', 0),
                    'Hits allowed': totals.get('ha', 0),
                    'Walks': totals.get('bb', 0),
                })

        hitters.sort(
            key=lambda row: (-row['Run Value'], row['Player'])
        )
        pitchers.sort(
            key=lambda row: (-row['Run Value'], row['Player'])
        )

        st.markdown('**Top hitters**')
        table(hitters[:3])
        st.markdown('**Top pitchers**')
        table(pitchers[:3])

        with st.expander('Scoring formula'):
            st.write(
                'Hitters: total bases + walks + hit-by-pitch '
                '+ runs + RBI + steals − caught stealing.'
            )
            st.write(
                'Pitchers: outs + strikeouts − (3 × earned runs) '
                '− hits allowed − walks allowed.'
            )
    else:
        st.info('Start a run and save games to see MVP candidates.')
    st.subheader('Franchise leaders')
    hitter=sorted([{'Player':p['name'],**aggregate(repo,fid,p)} for p in players if p['kind']=='hitter'],key=lambda p:p['h'],reverse=True)
    pitcher=sorted([{'Player':p['name'],**aggregate(repo,fid,p)} for p in players if p['kind']=='pitcher'],key=lambda p:p['so'],reverse=True)
    table(hitter[:5]);table(pitcher[:5])
    st.subheader('Longest-tenured cards')
    table([{'Player':p['name'],'Acquired':p['acquired_at'],'Status':p['area']} for p in sorted(players,key=lambda p:p['acquired_at'])[:10]])
    for title,key in [('Games','games'),('Rewards and milestones','rewards'),('Roster changes and corrections','corrections'),
                      ('Banked rewards and punishments','moves'),('Franchise Tags','tags'),('Immutable wheel audit','spins'),('Roster snapshots','snapshots')]:
        with st.expander(title):
            for row in repo.list(key,fid):st.json(row,expanded=False)
