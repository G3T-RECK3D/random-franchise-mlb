from models.domain import RuleError, uid, now
from services.stat_engine import aggregate
from services.franchise_tag_service import grant

# Quantitative V1 challenges use stat fields. Situational feats require evidence.
def create(repo, fid, run_id, pid, description, metric=None, threshold=1, scope='next_game', reward='protection', game_id=None):
    if not repo.get('players', pid) or repo.get('players', pid)['franchise_id'] != fid:
        raise RuleError('Challenge target not in this franchise.')
    identifier = uid()
    repo.put('challenges', dict(id=identifier, franchise_id=fid, run_id=run_id, player_id=pid,
        description=description, metric=metric, threshold=threshold, scope=scope, reward=reward,
        source_game=game_id, created_at=now(), status='waiting_next_run' if scope == 'next_run' else 'active'))
    return identifier

def evaluate(repo, fid, run_id, game_id):
    game = repo.get('games', game_id)
    for c in repo.list('challenges', fid, run_id):
        if c['status'] not in ['active', 'passed', 'failed', 'awaiting_manual']:
            continue
        games = repo.list('games', fid, run_id)
        candidates = [g for g in games if not c.get('source_game') or g['number'] > repo.get('games', c['source_game'])['number']]
        if not candidates:
            continue
        if c['scope'] == 'next_game':
            relevant = candidates[0]
            if relevant['id'] != game_id:
                continue
            closed = True
        else:
            relevant = game
            closed = bool(repo.get('runs', run_id)['ended_at'])
        if c.get('metric'):
            p = repo.get('players', c['player_id'])
            totals = aggregate(repo, fid, p, run_id, relevant['id'] if c['scope'] == 'next_game' else None)
            passed = totals.get(c['metric'], 0) >= c['threshold']
            if passed or closed:
                c['status'] = 'passed' if passed else 'failed'
                repo.put('challenges', c)
                settle(repo, c, passed)
        elif closed:
            c['status'] = 'awaiting_manual'
            repo.put('challenges', c)

def settle(repo, c, passed):
    key = f"challenge:{c['id']}"
    previous = repo.get('rewards', key)
    # Re-evaluation does not repeat granted benefits. Corrections remain audited.
    if passed and not previous:
        if c['reward'] == 'upgrade':
            player = repo.get('players', c['player_id'])
            repo.put('moves', dict(
                id=key,
                franchise_id=c['franchise_id'],
                run_id=c['run_id'],
                game_id=None,
                type='upgrade',
                target=c['player_id'],
                description=(
                    'Development upgrade: ' + player['name']
                    + ' — next available higher-rated Event-legal card'
                ),
                constraints={},
                status='pending',
                critical=False,
                created_at=now(),
                source='development',
            ))
        elif c['reward'] == 'tag':
            result = grant(repo, c['franchise_id'], c['player_id'], source=c['description'])
            if result == 'cap_decision_required':
                repo.put('moves', dict(id=key, franchise_id=c['franchise_id'], run_id=c['run_id'], game_id=None,
                    type='tag', target=c['player_id'], description='Tag cap decision: ' + c['description'],
                    constraints={}, status='pending', critical=True, created_at=now(), source='challenge'))
        else:
            p = repo.get('players', c['player_id'])
            p['protected'] = True
            repo.put('players', p)
        repo.put('rewards', dict(id=key, franchise_id=c['franchise_id'], run_id=c['run_id'],
                                type=c['reward'], player_id=c['player_id'], status='earned'))
    elif not passed and previous:
        previous['status'] = 'correction_review'
        repo.put('rewards', previous)


def confirm_manual(repo, fid, cid, passed, evidence):
    from services.franchise_service import audit
    with repo.transaction():
        c = repo.get('challenges', cid)
        if not c or c['franchise_id'] != fid or c['status'] != 'awaiting_manual' or not evidence.strip():
            raise RuleError('Select a pending manual challenge and provide evidence.')
        before = dict(c)
        c.update(status='passed' if passed else 'failed', evidence=evidence)
        repo.put('challenges', c)
        settle(repo, c, passed)
        audit(repo, fid, 'challenge_evidence', before, c, evidence, c['run_id'])

def unlock_development(repo, fid, run_id, game_id):
    """Unlock one development challenge after a saved breakout game."""
    challenges = repo.list('challenges', fid)
    moves = repo.list('moves', fid)

    for stat in repo.list('stats', fid, run_id):
        if stat['game_id'] != game_id:
            continue

        player = repo.get('players', stat['player_id'])
        if not player:
            continue

        line = stat['line']
        if player['kind'] == 'hitter':
            extra_base_hits = (
                line['doubles'] + line['triples'] + line['hr']
            )
            breakout = (
                line['hr'] >= 2
                or (line['h'] >= 3 and extra_base_hits >= 1)
            )
            metric, threshold = 'hr', 3
            goal = 'Hit 3 home runs next run'
        else:
            if line['starts']:
                breakout = (
                    line['outs'] >= 9
                    and line['er'] == 0
                    and line['so'] >= 4
                )
            else:
                breakout = (
                    line['outs'] >= 6
                    and line['r'] == 0
                    and line['so'] >= 3
                )
            metric, threshold = 'so', 8
            goal = 'Record 8 strikeouts next run'

        if not breakout:
            continue

        already_open = any(
            c['player_id'] == player['id']
            and c.get('reward') == 'upgrade'
            and c['status'] in [
                'waiting_next_run', 'active', 'awaiting_manual'
            ]
            for c in challenges
        )
        upgrade_waiting = any(
            m.get('target') == player['id']
            and m['type'] == 'upgrade'
            and m['status'] in ['pending', 'deferred']
            for m in moves
        )
        earned_this_run = any(
            c['player_id'] == player['id']
            and c.get('reward') == 'upgrade'
            and c.get('breakout_run') == run_id
            for c in challenges
        )
        if already_open or upgrade_waiting or earned_this_run:
            continue

        cid = create(
            repo, fid, run_id, player['id'],
            'Development: ' + goal
            + ' to earn the next available higher-rated '
            'Event-legal card of this player.',
            metric=metric,
            threshold=threshold,
            scope='next_run',
            reward='upgrade',
            game_id=game_id,
        )
        challenge = repo.get('challenges', cid)
        challenge.update(
            breakout_run=run_id,
            breakout_game=game_id,
        )
        repo.put('challenges', challenge)
        challenges.append(challenge)
