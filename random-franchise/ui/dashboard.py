                st.caption(f"Run {target_run['number'] if target_run else '?'} · {scope}")
            reward = 'Franchise Tag' if challenge.get('reward') == 'tag' else 'Player protection'
            st.caption('Reward: ' + reward)
            pending_tag = repo.get('moves', 'challenge:' + challenge['id'])
            if status == 'passed' and pending_tag and pending_tag['status'] == 'pending':
                st.info('Challenge completed. Choose a tag replacement in Banked Moves during offseason.')


def headquarters_banner(f, run, run_games):
    ordered = sorted(run_games, key=lambda g: g['number'])
    streak = 0
    last = ordered[-1]['result'] if ordered else None
    for game in reversed(ordered):
        if game['result'] != last:
            break
        streak += 1
    streak_text = f"{streak}-game {'winning' if last == 'W' else 'losing'} streak" if last else 'A new chapter awaits'
    phase = {
        State.ACTIVE: 'IN SEASON', State.WHEEL: 'FRONT OFFICE DECISION',
        State.SETUP: 'BUILD YOUR CLUB', State.READY: 'READY FOR OPENING DAY',
    }.get(f['state'], 'OFFSEASON')
    name = html.escape(f['name'])
    event = html.escape(f.get('event', ''))
    run_label = f"RUN {run['number']}" if run else 'PRESEASON'
    st.markdown(f'''<style>
    .franchise-banner {{background:linear-gradient(120deg,#780d21,#27131c 60%,#141923);
      border:1px solid #823347;border-left:7px solid #e32946;border-radius:16px;
      padding:28px;margin:8px 0 24px;color:#fff;}}
    .franchise-banner .eyebrow {{font-size:12px;font-weight:700;letter-spacing:2px;color:#ffb9c5;}}
    .franchise-banner h2 {{font-size:clamp(25px,4vw,42px);line-height:1.15;margin:12px 0;color:#fff;}}
    .franchise-banner .event {{color:#e7d9df;font-size:15px;}}
    .franchise-banner .story {{margin-top:20px;padding-top:15px;border-top:1px solid #ffffff25;font-size:16px;}}
    </style><div class="franchise-banner">
    <div class="eyebrow">FRANCHISE HEADQUARTERS · {run_label} · {phase}</div>
    <h2>{name}</h2><div class="event">{event}</div>
    <div class="story">{streak_text}</div></div>''', unsafe_allow_html=True)


def next_action(repo, f, run):
    with st.container(border=True):
        st.subheader('Your next move')
        if f['state'] == State.ACTIVE:
            st.write('The roster is set. Take the field, then record your next game.')
            navigate('▶ Enter next game', 'Game Entry')
        elif f['state'] == State.WHEEL:
            st.write('A required wheel is waiting. Resolve it before your next game.')
            navigate('🎡 Open Wheel Room', 'Wheel Room')
        elif f['state'] in [State.SETUP, State.READY]:
            st.write('Prepare your club and validate the roster for opening day.')
            navigate('Inspect your roster', 'Roster Manager')
            if st.button('Validate and start next run', type='primary'):
                start_run(repo, f['id'])
                st.rerun()
        else:
            messages = {
                State.ENDED: 'The run is complete. Confirm the final record and begin your offseason.',
                State.MVP: 'Choose the player who defined this run and collect the MVP reward.',
                State.ELIMINATION: 'Process the elimination wheel before rebuilding the club.',
                State.MELTDOWN: 'Continue the offseason check. A Meltdown applies only if the run finished 0–2.',
                State.MOVES: 'Review your banked rewards and consequences before reconstructing the roster.',
                State.REBUILD: 'Arrange the roster for your next run.',
                State.VALIDATION: 'Check roster eligibility and composition before opening day.',
            }
            st.write(messages.get(f['state'], 'Continue your offseason workflow.'))
            navigate('Continue offseason', 'Offseason')


def clubhouse_leaders(repo, fid, run, players):
    st.subheader('Clubhouse leaders')
    st.caption('Current-run totals from saved game stats. Ties share the lead.')
    if not run:
        st.info('Start a run to build your player storylines.')
        return
    totals = [(p, aggregate(repo, fid, p, run['id'])) for p in players]
    columns = st.columns(3)
    for column, kind, metric, label in zip(columns,
            ['hitter', 'hitter', 'pitcher'], ['hr', 'rbi', 'so'], ['Home runs', 'Runs batted in', 'Strikeouts']):
        candidates = [(p, t.get(metric, 0)) for p, t in totals if p['kind'] == kind]
        high = max((value for p, value in candidates), default=0)
        leaders = [p['name'] for p, value in candidates if value == high] if high > 0 else []
        with column:
            with st.container(border=True):
                st.metric(label, high)
                st.write(', '.join(leaders) if leaders else 'Waiting for the first mark')


def recent_results(run_games):
    st.subheader('From the dugout')
    ordered = sorted(run_games, key=lambda g: g['number'], reverse=True)[:5]
    if not ordered:
        st.info('Your first saved game will start the run’s story here.')
        return
    for game in ordered:
        score = ''
        if game.get('team_score') is not None and game.get('opponent_score') is not None:
            score = f" · {game['team_score']}–{game['opponent_score']}"
        opponent = ' vs ' + str(game['opponent']) if game.get('opponent') else ''
        with st.container(border=True):
            icon = '🟢' if game['result'] == 'W' else '🔴'
            st.write(f"{icon} **Game {game['number']} · {game['result']}{score}**{opponent}")
            if game.get('date'):
                st.caption(game['date'])
            if game.get('notes'):
                st.write(game['notes'])


def render(repo,f):
    fid=f['id'];run=repo.get('runs',f['current_run']) if f['current_run'] else None
    games=repo.list('games',fid)
    players=repo.list('players',fid)
    run_games=[g for g in games if run and g['run_id']==run['id']]
    headquarters_banner(f, run, run_games)
    a,b,c,d=st.columns(4)
    a.metric('Run record',f"{run['wins']}–{run['losses']}" if run else 'Not started')
    b.metric('Franchise record',f"{sum(g['result']=='W' for g in games)}–{sum(g['result']=='L' for g in games)}")
    pending=[m for m in repo.list('moves',fid) if m['status'] in ['pending','deferred']]
    c.metric('📦 Next-run moves',len(pending))
    threshold=next((n for n in sorted(int(x) for x in settings(repo,fid)['milestones']) if not run or n>run['wins']),None)
    d.metric('Next milestone',f'{threshold} wins' if threshold else 'All earned')
    next_action(repo, f, run)
    clubhouse_leaders(repo, fid, run, players)
    show_challenges(repo, fid, run)
    st.subheader('Around the clubhouse')
    table([{'Player':p['name'],'Status':badges(repo,fid,p)} for p in players if badges(repo,fid,p)])
    recent_results(run_games)
    st.subheader('📦 Front office inbox')
    st.caption('Banked moves waiting for offseason resolution.')
    table([{'Move':m['description'],'Type':m['type'],'Status':m['status']} for m in pending[:8]])
