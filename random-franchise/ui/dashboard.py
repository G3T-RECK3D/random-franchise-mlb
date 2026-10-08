import streamlit as st
from models.domain import State
from services.game_engine import start_run
from services.franchise_service import settings
from services.stat_engine import aggregate
from ui.common import navigate,table,badges

def challenge_progress(repo, fid, challenge):
    """Read the same saved stat scope used by challenge evaluation."""
    if challenge['status'] == 'waiting_next_run' or not challenge.get('metric'):
        return None
    player = repo.get('players', challenge['player_id'])
    if not player:
        return None
    rid = challenge['run_id']
    game_id = None
    if challenge.get('scope') == 'next_game':
        games = repo.list('games', fid, rid)
        source = repo.get('games', challenge['source_game']) if challenge.get('source_game') else None
        games = [g for g in games if not source or g['number'] > source['number']]
        if not games:
            return 0
        game_id = min(games, key=lambda g: g['number'])['id']
    return aggregate(repo, fid, player, rid, game_id).get(challenge['metric'], 0)


def show_challenges(repo, fid, run):
    st.subheader('Challenge progress')
    st.caption('Progress updates from saved game stats. Unsaved drafts are not included.')
    challenges = [c for c in repo.list('challenges', fid)
        if c['status'] in ['active', 'awaiting_manual', 'waiting_next_run']
        or (run and c['run_id'] == run['id'] and c['status'] in ['passed', 'failed'])]
    if not challenges:
        st.info('No challenges to track right now.')
        return
    labels = {'h': 'hits', 'hr': 'HR', 'rbi': 'RBI', 'so': 'strikeouts',
              'outs': 'outs recorded', 'w': 'wins', 'sv': 'saves'}
    statuses = {'active': 'In progress', 'passed': 'Completed', 'failed': 'Not achieved',
                'awaiting_manual': 'Needs confirmation', 'waiting_next_run': 'Starts next run'}
    for challenge in challenges:
        player = repo.get('players', challenge['player_id'])
        with st.container(border=True):
            st.subheader(player['name'] if player else 'Player unavailable')
            st.write(challenge['description'])
            status = challenge['status']
            total = challenge_progress(repo, fid, challenge)
            if total is not None:
                goal = challenge.get('threshold', 1)
                unit = labels.get(challenge['metric'], challenge['metric'])
                st.write(f"**{total:g} / {goal:g} {unit}** · {statuses.get(status, status)}")
                st.progress(min(max(float(total) / goal, 0.0), 1.0) if goal > 0 else 1.0)
                if status == 'active':
                    remaining = max(goal - total, 0)
                    st.caption(f'{remaining:g} more {unit} needed.' if remaining else 'Goal reached in saved stats; check the challenge status.')
            else:
                st.write(statuses.get(status, status))
                if status in ['active', 'awaiting_manual'] and not challenge.get('metric'):
                    st.caption('This challenge requires evidence and confirmation during offseason.')
            if status == 'waiting_next_run':
                st.caption('Current-run stats do not count toward this upcoming challenge.')
            else:
                scope = 'next qualifying game only' if challenge.get('scope') == 'next_game' else 'whole run'
                target_run = repo.get('runs', challenge['run_id'])
                st.caption(f"Run {target_run['number'] if target_run else '?'} · {scope}")
            reward = 'Franchise Tag' if challenge.get('reward') == 'tag' else 'Player protection'
            st.caption('Reward: ' + reward)
            pending_tag = repo.get('moves', 'challenge:' + challenge['id'])
            if status == 'passed' and pending_tag and pending_tag['status'] == 'pending':
                st.info('Challenge completed. Choose a tag replacement in Banked Moves during offseason.')


def render(repo,f):
    fid=f['id'];run=repo.get('runs',f['current_run']) if f['current_run'] else None
    with st.container(border=True):
        st.caption("FRANCHISE HEADQUARTERS")
        st.header(f['name'])
        st.write(f['event'])
        if run:
            st.caption(f"Run {run['number']} · Your next chapter")
    games=repo.list('games',fid)
    a,b,c,d=st.columns(4)
    a.metric('Run record',f"{run['wins']}–{run['losses']}" if run else 'Not started')
    b.metric('Franchise record',f"{sum(g['result']=='W' for g in games)}–{sum(g['result']=='L' for g in games)}")
    pending=[m for m in repo.list('moves',fid) if m['status'] in ['pending','deferred']]
    c.metric('📦 Next-run moves',len(pending))
    threshold=next((n for n in sorted(int(x) for x in settings(repo,fid)['milestones']) if not run or n>run['wins']),None)
    d.metric('Next milestone',f'{threshold} wins' if threshold else 'All earned')
    if f['state']==State.ACTIVE:navigate('▶ Enter Next Game','Game Entry')
    elif f['state']==State.WHEEL:navigate('🎡 Spin required wheel','Wheel Room')
    elif f['state'] in [State.SETUP,State.READY]:
        navigate('Build / inspect roster','Roster Manager')
        if st.button('Validate and start next run',type='primary'):
            start_run(repo,fid);st.rerun()
    else:navigate('Continue offseason','Offseason')
    st.subheader('Franchise status')
    table([{'Player':p['name'],'Status':badges(repo,fid,p)} for p in repo.list('players',fid) if badges(repo,fid,p)])
    show_challenges(repo, fid, run)
    st.subheader('From the dugout')
    recent = sorted(
        [g for g in games if run and g['run_id'] == run['id']],
        key=lambda g: g['number'],
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
    st.subheader('📦 Next Run Moves')
    table([{'Move':m['description'],'Type':m['type'],'Status':m['status']} for m in pending[:8]])
    spins=repo.list('spins',fid)
    if spins:st.info('Latest wheel: '+spins[-1]['result']['text'])
