from models.domain import State, RuleError, uid, now, ACTIVE_AREAS
from services.franchise_service import settings, audit
from services.roster_validator import validate
from services.stat_engine import validate_line
from services.challenge_service import evaluate, unlock_development
from services.franchise_tag_service import grant


def enqueue(
    franchise, wheel_id, source,
    game_id=None, target=None, depth=0,
):
    franchise['queue'].append(dict(
        id=uid(),
        wheel_id=wheel_id,
        source=source,
        game_id=game_id,
        target=target,
        depth=depth,
    ))


def start_run(repo, fid):
    with repo.transaction():
        f = repo.get('franchises', fid)
        if f['state'] not in [
            State.SETUP, State.READY, State.VALIDATION,
        ]:
            raise RuleError(
                'Finish the current workflow before starting a week.'
            )

        season = (
            repo.get('seasons', f['current_season'])
            if f.get('current_season') else None
        )
        if (
            not season
            or season['franchise_id'] != fid
            or season['status'] != 'active'
        ):
            raise RuleError(
                'Set up an active season before starting a week.'
            )

        errors = validate(repo, fid).errors
        if errors:
            raise RuleError('\n'.join(errors))

        cfg = settings(repo, fid)
        rid = uid()
        runs = repo.list('runs', fid)
        season_runs = [
            run for run in runs
            if run.get('season_id') == season['id']
        ]

        number = max(
            (run['number'] for run in runs),
            default=0,
        ) + 1
        week_number = max(
            (run.get('week_number', 0) for run in season_runs),
            default=0,
        ) + 1

        active = [
            player['id']
            for player in repo.list('players', fid)
            if player['area'] in ACTIVE_AREAS
        ]

        repo.put('runs', dict(
            id=rid,
            franchise_id=fid,
            number=number,
            season_id=season['id'],
            week_number=week_number,
            event=season['event'],
            wins=0,
            losses=0,
            max_losses=cfg['max_losses'],
            settings=cfg,
            roster_ids=active,
            started_at=now(),
            ended_at=None,
            mvp=None,
            offseason_step=None,
        ))

        f.update(
            current_run=rid,
            event=season['event'],
            state=State.ACTIVE,
            queue=[],
            return_state=State.ACTIVE,
        )
        repo.put('franchises', f)

        for challenge in repo.list('challenges', fid):
            if challenge['status'] == 'waiting_next_run':
                challenge.update(
                    run_id=rid,
                    status='active',
                    source_game=None,
                )
                repo.put('challenges', challenge)

        snapshot(repo, fid, rid, 'start')
        return rid


def snapshot(repo, fid, rid, phase):
    identifier = f'{rid}:{phase}'
    if not repo.get('snapshots', identifier):
        repo.put('snapshots', dict(
            id=identifier,
            franchise_id=fid,
            run_id=rid,
            phase=phase,
            created_at=now(),
            players=repo.list('players', fid),
        ))


def milestone_sync(repo, f, run, game_id):
    for threshold, wheel in run['settings']['milestones'].items():
        key = f"milestone:{run['id']}:{threshold}"
        reward = repo.get('rewards', key)

        if (
            run['wins'] >= int(threshold)
            and (
                not reward
                or reward['status'] == 'revoked'
            )
        ):
            repo.put('rewards', dict(
                id=key,
                franchise_id=f['id'],
                run_id=run['id'],
                game_id=game_id,
                type=wheel,
                threshold=int(threshold),
                status='earned',
            ))
            enqueue(f, wheel, key, game_id)

        elif (
            run['wins'] >= int(threshold)
            and reward
            and reward.get('game_id') == game_id
        ):
            queued = any(
                job['source'] == key
                for job in f['queue']
            )
            spun = any(
                spin['job']['source'] == key
                for spin in repo.list('spins', f['id'])
            )
            if not queued and not spun:
                enqueue(f, wheel, key, game_id)

        elif (
            run['wins'] < int(threshold)
            and reward
            and reward['status'] == 'earned'
        ):
            reward['status'] = 'revoked'
            repo.put('rewards', reward)
            f['queue'] = [
                job for job in f['queue']
                if job['source'] != key
            ]


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


def _capture_assignments(repo, fid, run):
    """Record roster assignments when a new game is saved."""
    roster_ids = set(run['roster_ids'])
    return {
        player['id']: {
            'area': player['area'],
            'order': player.get('order'),
            'position': player.get('position'),
        }
        for player in repo.list('players', fid)
        if player['id'] in roster_ids
    }


def _line_assignment(game, pid, previous_rows, starting_players):
    """Never substitute today's roster for a historical game's roster."""
    previous = previous_rows.get(pid, {})

    if 'roster_area' in previous or 'batting_order' in previous:
        return {
            'roster_area': previous.get('roster_area'),
            'batting_order': previous.get('batting_order'),
            'assigned_position': previous.get('assigned_position'),
            'assignment_source': previous.get(
                'assignment_source', 'saved',
            ),
        }

    assignment = game.get('roster_assignments', {}).get(pid)
    source = 'game_save'

    if assignment is None:
        assignment = starting_players.get(pid)
        source = 'start_snapshot'

    if assignment is None:
        return {
            'roster_area': None,
            'batting_order': None,
            'assigned_position': None,
            'assignment_source': 'unavailable',
        }

    area = assignment.get('area')
    order = assignment.get('order')
    batting_order = (
        order
        if area == 'lineup'
        and type(order) is int
        and 1 <= order <= 9
        else None
    )

    return {
        'roster_area': area,
        'batting_order': batting_order,
        'assigned_position': assignment.get('position'),
        'assignment_source': source,
    }


def _save_lines(
    repo, fid, run, game, lines, previous_rows=None,
):
    seen = set()
    previous_rows = previous_rows or {}

    starting_snapshot = repo.get(
        'snapshots', f"{run['id']}:start",
    )
    starting_players = {}
    if (
        starting_snapshot
        and starting_snapshot.get('franchise_id') == fid
        and starting_snapshot.get('run_id') == run['id']
    ):
        starting_players = {
            player['id']: player
            for player in starting_snapshot.get('players', [])
        }

    for item in lines:
        pid = item['player_id']
        player = repo.get('players', pid)

        if (
            pid in seen
            or not player
            or player['franchise_id'] != fid
            or pid not in run['roster_ids']
        ):
            raise RuleError(
                'Stat lines must reference distinct players '
                'in the run roster.'
            )
        seen.add(pid)

        line = validate_line(player['kind'], item['line'])
        flags = item.get('flags', {})

        if flags.get('no_hitter') or flags.get('perfect_game'):
            if (
                player['kind'] != 'pitcher'
                or line['outs'] < 9
                or line['ha'] != 0
            ):
                raise RuleError(
                    'No-hitter/perfect game needs a pitcher '
                    'with at least 9 outs and zero hits allowed.'
                )
            if flags.get('perfect_game') and (
                line['bb'] or line['r']
            ):
                raise RuleError(
                    'Perfect game requires zero walks and runs.'
                )

        # Preserve recovery markers and other existing metadata.
        saved = dict(previous_rows.get(pid, {}))
        saved.update(
            id=f"{game['id']}:{pid}",
            franchise_id=fid,
            run_id=run['id'],
            player_id=pid,
            game_id=game['id'],
            line=line,
            flags=flags,
        )
        saved.update(
            _line_assignment(
                game, pid, previous_rows, starting_players,
            )
        )
        repo.put('stats', saved)

        if flags.get('no_hitter') or flags.get('perfect_game'):
            status = grant(
                repo,
                fid,
                pid,
                source='Manually confirmed no-hitter/perfect game',
            )
            key = f"auto_tag:{game['id']}:{pid}"

            if (
                status == 'cap_decision_required'
                and not repo.get('moves', key)
            ):
                repo.put('moves', dict(
                    id=key,
                    franchise_id=fid,
                    run_id=run['id'],
                    game_id=game['id'],
                    target=pid,
                    source='no_hitter',
                    type='tag',
                    constraints={},
                    description=(
                        'Automatic pitcher tag: resolve cap decision'
                    ),
                    status='pending',
                    critical=True,
                    created_at=now(),
                ))


def record_game(
    repo, fid, request_id, result,
    lines=None, opponent='',
    team_score=None, opponent_score=None,
    date=None, notes='',
):
    with repo.transaction():
        previous = repo.get('games', request_id)
        if previous:
            if previous['franchise_id'] != fid:
                raise RuleError(
                    'Submission ID belongs to another franchise.'
                )
            return previous['id']

        f = repo.get('franchises', fid)
        run = (
            repo.get('runs', f['current_run'])
            if f['current_run'] else None
        )

        if (
            f['state'] != State.ACTIVE
            or not run
            or run['ended_at']
        ):
            raise RuleError(
                'Game entry is blocked until the required '
                'workflow is finished.'
            )

        roster_check = validate(repo, fid, check_tasks=False)
        if not roster_check.valid:
            raise RuleError(
                'Fix active roster arrangements before recording a game: '
                + '; '.join(roster_check.errors)
            )

        if result not in ['W', 'L']:
            raise RuleError('Choose W or L.')

        if team_score is not None or opponent_score is not None:
            if (
                team_score is None
                or opponent_score is None
                or min(team_score, opponent_score) < 0
            ):
                raise RuleError(
                    'Enter both nonnegative scores or leave both blank.'
                )
            if (
                team_score == opponent_score
                or (team_score > opponent_score) != (result == 'W')
            ):
                raise RuleError(
                    'Score must agree with win/loss result.'
                )

        game = dict(
            id=request_id,
            franchise_id=fid,
            run_id=run['id'],
            number=len(repo.list('games', fid, run['id'])) + 1,
            result=result,
            opponent=opponent,
            team_score=team_score,
            opponent_score=opponent_score,
            date=str(date or now()[:10]),
            notes=notes,
            created_at=now(),
            roster_assignments=_capture_assignments(repo, fid, run),
        )
        repo.put('games', game)
        _save_lines(repo, fid, run, game, lines or [])

        run['wins' if result == 'W' else 'losses'] += 1

        milestone_sync(repo, f, run, request_id)
        _route(repo, f, run, game)
        evaluate(repo, fid, run['id'], request_id)
        unlock_development(repo, fid, run['id'], request_id)
        return request_id


def correct_game(repo, fid, gid, lines, reason, result=None):
    """Correct stats while preserving historical roster assignments."""
    with repo.transaction():
        game = repo.get('games', gid)
        if (
            not game
            or game['franchise_id'] != fid
            or not reason.strip()
        ):
            raise RuleError(
                'Valid game and correction reason required.'
            )

        before = dict(
            game=dict(game),
            stats=[
                stat
                for stat in repo.list('stats', fid, game['run_id'])
                if stat['game_id'] == gid
            ],
        )
        previous_rows = {
            stat['player_id']: stat for stat in before['stats']
        }

        run = repo.get('runs', game['run_id'])
        f = repo.get('franchises', fid)
        changed = result is not None and result != game['result']

        if changed:
            if result not in ['W', 'L']:
                raise RuleError('Choose W or L.')

            if (
                f['current_run'] != run['id']
                or repo.list('games', fid, run['id'])[-1]['id'] != gid
            ):
                raise RuleError(
                    'Outcome corrections are limited to the latest '
                    'game of the current run.'
                )

            if (
                any(
                    saved_spin.get('game_id') == gid
                    for saved_spin in repo.list('spins', fid)
                )
                or run.get('offseason_step')
            ):
                raise RuleError(
                    'Dependent wheels/offseason already processed. '
                    'Stats correction remains available; outcome '
                    'rewind is unsupported in V1.'
                )

            f['queue'] = [
                job for job in f['queue']
                if job.get('game_id') != gid
            ]

            run[
                'wins' if game['result'] == 'W' else 'losses'
            ] -= 1
            run['wins' if result == 'W' else 'losses'] += 1
            game.update(
                result=result,
                team_score=None,
                opponent_score=None,
            )

            milestone_sync(repo, f, run, gid)
            _route(repo, f, run, game)

        repo.put('games', game)

        for stat in before['stats']:
            repo.delete('stats', stat['id'])

        _save_lines(
            repo, fid, run, game, lines,
            previous_rows=previous_rows,
        )
        evaluate(repo, fid, run['id'], gid)

        audit(
            repo,
            fid,
            'correct_game',
            before,
            dict(
                game=game,
                stats=[
                    stat
                    for stat in repo.list('stats', fid, run['id'])
                    if stat['game_id'] == gid
                ],
            ),
            reason,
            run['id'],
        )
