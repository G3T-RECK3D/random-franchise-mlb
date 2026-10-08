from models.domain import State, RuleError, uid, now, ACTIVE_AREAS
from services.franchise_service import settings, audit
from services.roster_validator import validate
from services.stat_engine import validate_line
from services.challenge_service import evaluate
from services.franchise_tag_service import grant


def enqueue(franchise, wheel_id, source, game_id=None, target=None, depth=0):
    franchise['queue'].append(dict(id=uid(), wheel_id=wheel_id, source=source, game_id=game_id,
                                   target=target, depth=depth))


def start_run(repo, fid):
    with repo.transaction():
        f = repo.get('franchises', fid)
        if f['state'] not in [State.SETUP, State.READY, State.VALIDATION]:
            raise RuleError('Finish the current workflow before starting a run.')
        errors = validate(repo, fid).errors
        if errors:
            raise RuleError('\n'.join(errors))
        cfg = settings(repo, fid)
        rid = uid()
        active = [p['id'] for p in repo.list('players', fid) if p['area'] in ACTIVE_AREAS]
        repo.put('runs', dict(id=rid, franchise_id=fid, number=len(repo.list('runs', fid)) + 1,
            event=f['event'], wins=0, losses=0, max_losses=cfg['max_losses'], settings=cfg,
            roster_ids=active, started_at=now(), ended_at=None, mvp=None, offseason_step=None))
        f.update(current_run=rid, state=State.ACTIVE, queue=[], return_state=State.ACTIVE)
        repo.put('franchises', f)
        for c in repo.list('challenges', fid):
            if c['status'] == 'waiting_next_run':
                c.update(run_id=rid, status='active', source_game=None)
                repo.put('challenges', c)
        snapshot(repo, fid, rid, 'start')
        return rid


def snapshot(repo, fid, rid, phase):
    identifier = f'{rid}:{phase}'
    if not repo.get('snapshots', identifier):
        repo.put('snapshots', dict(id=identifier, franchise_id=fid, run_id=rid, phase=phase,
            created_at=now(), players=repo.list('players', fid)))


def milestone_sync(repo, f, run, game_id):
    for threshold, wheel in run['settings']['milestones'].items():
        key = f"milestone:{run['id']}:{threshold}"
        reward = repo.get('rewards', key)
        if run['wins'] >= int(threshold) and (not reward or reward['status'] == 'revoked'):
            repo.put('rewards', dict(id=key, franchise_id=f['id'], run_id=run['id'], game_id=game_id,
                                     type=wheel, threshold=int(threshold), status='earned'))
            enqueue(f, wheel, key, game_id)
        elif run['wins'] >= int(threshold) and reward and reward.get('game_id') == game_id:
            if not any(j['source'] == key for j in f['queue']) and not any(s['job']['source'] == key for s in repo.list('spins', f['id'])):
                enqueue(f, wheel, key, game_id)
        elif run['wins'] < int(threshold) and reward and reward['status'] == 'earned':
            reward['status'] = 'revoked'
            repo.put('rewards', reward)
            f['queue'] = [j for j in f['queue'] if j['source'] != key]


def _route(repo, f, run, game):
    if run['losses'] >= run['max_losses']:
        run['ended_at'] = run['ended_at'] or now()
        f['state'] = State.ENDED
        f['return_state'] = State.ENDED
        snapshot(repo, f['id'], run['id'], 'end')
    else:
        run['ended_at'] = None
        if game['result'] == 'L':
            enqueue(f, 'hot_seat', 'loss', game['id'])
        f['return_state'] = State.ACTIVE
        f['state'] = State.WHEEL if f['queue'] else State.ACTIVE
    repo.put('runs', run)
    repo.put('franchises', f)


def _save_lines(repo, fid, run, game, lines):
    seen = set()
    for item in lines:
        pid = item['player_id']
        p = repo.get('players', pid)
        if pid in seen or not p or p['franchise_id'] != fid or pid not in run['roster_ids']:
            raise RuleError('Stat lines must reference distinct players in the run roster.')
        seen.add(pid)
        line = validate_line(p['kind'], item['line'])
        flags = item.get('flags', {})
        if flags.get('no_hitter') or flags.get('perfect_game'):
            if p['kind'] != 'pitcher' or line['outs'] < 9 or line['ha'] != 0:
                raise RuleError('No-hitter/perfect game needs a pitcher with at least 9 outs and zero hits allowed.')
            if flags.get('perfect_game') and (line['bb'] or line['r']):
                raise RuleError('Perfect game requires zero walks and runs.')
        repo.put('stats', dict(id=f"{game['id']}:{pid}", franchise_id=fid, run_id=run['id'],
                              player_id=pid, game_id=game['id'], line=line, flags=flags))
        if flags.get('no_hitter') or flags.get('perfect_game'):
            status = grant(repo, fid, pid, source='Manually confirmed no-hitter/perfect game')
            key = f"auto_tag:{game['id']}:{pid}"
            if status == 'cap_decision_required' and not repo.get('moves', key):
                repo.put('moves', dict(id=key, franchise_id=fid, run_id=run['id'], game_id=game['id'],
                    target=pid, source='no_hitter', type='tag', constraints={}, description='Automatic pitcher tag: resolve cap decision',
                    status='pending', critical=True, created_at=now()))


def record_game(repo, fid, request_id, result, lines=None, opponent='', team_score=None, opponent_score=None, date=None, notes=''):
    with repo.transaction():
        previous = repo.get('games', request_id)
        if previous:
            if previous['franchise_id'] != fid:
                raise RuleError('Submission ID belongs to another franchise.')
            return previous['id']
        f = repo.get('franchises', fid)
        run = repo.get('runs', f['current_run']) if f['current_run'] else None
        if f['state'] != State.ACTIVE or not run or run['ended_at']:
            raise RuleError('Game entry is blocked until the required workflow is finished.')
        roster_check = validate(repo, fid, check_tasks=False)
        if not roster_check.valid:
            raise RuleError('Fix active roster arrangements before recording a game: ' + '; '.join(roster_check.errors))
        if result not in ['W', 'L']:
            raise RuleError('Choose W or L.')
        if team_score is not None or opponent_score is not None:
            if team_score is None or opponent_score is None or min(team_score, opponent_score) < 0:
                raise RuleError('Enter both nonnegative scores or leave both blank.')
            if team_score == opponent_score or (team_score > opponent_score) != (result == 'W'):
                raise RuleError('Score must agree with win/loss result.')
        game = dict(id=request_id, franchise_id=fid, run_id=run['id'], number=len(repo.list('games', fid, run['id'])) + 1,
            result=result, opponent=opponent, team_score=team_score, opponent_score=opponent_score,
            date=str(date or now()[:10]), notes=notes, created_at=now())
        repo.put('games', game)
        _save_lines(repo, fid, run, game, lines or [])
        run['wins' if result == 'W' else 'losses'] += 1
        milestone_sync(repo, f, run, request_id)
        _route(repo, f, run, game)
        evaluate(repo, fid, run['id'], request_id)
        return request_id


def correct_game(repo, fid, gid, lines, reason, result=None):
    """Stats can always be corrected. Outcome correction is limited to an unprocessed latest game.

    Historical wheel outcomes are never rewound. Dependent outcome edits require
    a new explicit administrative workflow in V2; refusing is safer than replaying spins.
    """
    with repo.transaction():
        game = repo.get('games', gid)
        if not game or game['franchise_id'] != fid or not reason.strip():
            raise RuleError('Valid game and correction reason required.')
        before = dict(game=game, stats=[s for s in repo.list('stats', fid, game['run_id']) if s['game_id'] == gid])
        run = repo.get('runs', game['run_id'])
        f = repo.get('franchises', fid)
        changed = result is not None and result != game['result']
        if changed:
            if result not in ['W', 'L']:
                raise RuleError('Choose W or L.')
            if f['current_run'] != run['id'] or repo.list('games', fid, run['id'])[-1]['id'] != gid:
                raise RuleError('Outcome corrections are limited to the latest game of the current run.')
            if any(s.get('game_id') == gid for s in repo.list('spins', fid)) or run.get('offseason_step'):
                raise RuleError('Dependent wheels/offseason already processed. Stats correction remains available; outcome rewind is unsupported in V1.')
            f['queue'] = [j for j in f['queue'] if j.get('game_id') != gid]
            run['wins' if game['result'] == 'W' else 'losses'] -= 1
            run['wins' if result == 'W' else 'losses'] += 1
            game.update(result=result, team_score=None, opponent_score=None)
            milestone_sync(repo, f, run, gid)
            _route(repo, f, run, game)
        repo.put('games', game)
        for row in before['stats']:
            repo.delete('stats', row['id'])
        _save_lines(repo, fid, run, game, lines)
        evaluate(repo, fid, run['id'], gid)
        audit(repo, fid, 'correct_game', before,
              dict(game=game, stats=[s for s in repo.list('stats', fid, run['id']) if s['game_id'] == gid]), reason, run['id'])
