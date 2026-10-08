import html
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
