import secrets

from models.domain import RuleError, uid, now
from services.stat_engine import aggregate
from services.franchise_tag_service import grant


HITTER_GOALS = [
    ('hr', 2, 'Hit 2 home runs'),
    ('h', 4, 'Collect 4 hits'),
    ('extra_base_hits', 3, 'Record 3 extra-base hits'),
    ('rbi', 4, 'Drive in 4 RBI'),
    ('times_on_base', 5, 'Reach base 5 times through hits, walks, or HBP'),
]

DEVELOPMENT_LIMIT_PER_SEASON = 2

OPEN_STATUSES = [
    'waiting_next_run',
    'active',
    'awaiting_manual',
]


def metric_value(totals, metric):
    if metric == 'extra_base_hits':
        return (
            totals.get('doubles', 0)
            + totals.get('triples', 0)
            + totals.get('hr', 0)
        )
    if metric == 'times_on_base':
        return (
            totals.get('h', 0)
            + totals.get('bb', 0)
            + totals.get('hbp', 0)
        )
    return totals.get(metric, 0)


def create(
    repo, fid, run_id, pid, description,
    metric=None, threshold=1, scope='next_game',
    reward='protection', game_id=None,
):
    player = repo.get('players', pid)
    if not player or player['franchise_id'] != fid:
        raise RuleError('Challenge target not in this franchise.')

    identifier = uid()
    repo.put('challenges', dict(
        id=identifier,
        franchise_id=fid,
        run_id=run_id,
        player_id=pid,
        description=description,
        metric=metric,
        threshold=threshold,
        scope=scope,
        reward=reward,
        source_game=game_id,
        created_at=now(),
        status=(
            'waiting_next_run'
            if scope == 'next_run'
            else 'active'
        ),
    ))
    return identifier


def development_progress(repo, challenge):
    """Retain support for previously assigned three-game challenges."""
    excluded = set(challenge.get('excluded_game_ids', []))
    games = [
        game
        for game in repo.list('games', challenge['franchise_id'])
        if game['id'] not in excluded
        and not game.get('recovered')
    ][:challenge.get('game_limit', 3)]

    game_ids = {game['id'] for game in games}
    totals = {}

    for stat in repo.list('stats', challenge['franchise_id']):
        if (
            stat['player_id'] == challenge['player_id']
            and stat['game_id'] in game_ids
        ):
            for field, value in stat['line'].items():
                totals[field] = totals.get(field, 0) + value

    passed = any(
        metric_value(totals, metric) >= target
        for metric, target in challenge.get('goals', {}).items()
    )

    return {
        'games_used': len(games),
        'game_limit': challenge.get('game_limit', 3),
        'totals': totals,
        'passed': passed,
        'closed': len(games) >= challenge.get('game_limit', 3),
    }


def evaluate(repo, fid, run_id, game_id):
    game = repo.get('games', game_id)
    if (
        not game
        or game['franchise_id'] != fid
        or game['run_id'] != run_id
    ):
        raise RuleError('Select a valid game.')

    for challenge in repo.list('challenges', fid):
        if challenge['status'] not in [
            'active', 'passed', 'failed', 'awaiting_manual',
        ]:
            continue

        if challenge['scope'] == 'three_games':
            progress = development_progress(repo, challenge)
            if progress['passed']:
                challenge['status'] = 'passed'
            elif progress['closed']:
                challenge['status'] = 'failed'
            else:
                challenge['status'] = 'active'

            repo.put('challenges', challenge)
            settle(repo, challenge, progress['passed'])
            continue

        if challenge.get('run_id') != run_id:
            continue

        source = (
            repo.get('games', challenge['source_game'])
            if challenge.get('source_game')
            else None
        )
        games = repo.list('games', fid, run_id)
        candidates = [
            candidate for candidate in games
            if not source
            or candidate['number'] > source['number']
        ]
        if not candidates:
            continue

        if challenge['scope'] == 'next_game':
            relevant = candidates[0]
            if relevant['id'] != game_id:
                continue
            closed = True
        else:
            relevant = game
            closed = bool(repo.get('runs', run_id)['ended_at'])

        if challenge.get('metric'):
            player = repo.get('players', challenge['player_id'])
            if not player:
                continue

            totals = aggregate(
                repo, fid, player, run_id,
                relevant['id']
                if challenge['scope'] == 'next_game'
                else None,
            )
            passed = (
                metric_value(totals, challenge['metric'])
                >= challenge['threshold']
            )

            if passed or closed:
                challenge['status'] = 'passed' if passed else 'failed'
            else:
                challenge['status'] = 'active'

            repo.put('challenges', challenge)
            settle(repo, challenge, passed)

        elif closed:
            challenge['status'] = 'awaiting_manual'
            repo.put('challenges', challenge)


def settle(repo, challenge, passed):
    key = f"challenge:{challenge['id']}"
    previous = repo.get('rewards', key)

    if passed and not previous:
        if challenge['reward'] == 'upgrade':
            player = repo.get('players', challenge['player_id'])
            repo.put('moves', dict(
                id=key,
                franchise_id=challenge['franchise_id'],
                run_id=challenge['run_id'],
                game_id=None,
                type='upgrade',
                target=challenge['player_id'],
                description=(
                    'Development upgrade: '
                    + player['name']
                    + ' — next available higher-rated Event-legal card'
                ),
                constraints={},
                status='pending',
                critical=False,
                created_at=now(),
                source='development',
            ))

        elif challenge['reward'] == 'tag':
            result = grant(
                repo,
                challenge['franchise_id'],
                challenge['player_id'],
                source=challenge['description'],
            )
            if result == 'cap_decision_required':
                repo.put('moves', dict(
                    id=key,
                    franchise_id=challenge['franchise_id'],
                    run_id=challenge['run_id'],
                    game_id=None,
                    type='tag',
                    target=challenge['player_id'],
                    description=(
                        'Tag cap decision: ' + challenge['description']
                    ),
                    constraints={},
                    status='pending',
                    critical=True,
                    created_at=now(),
                    source='challenge',
                ))

        else:
            player = repo.get('players', challenge['player_id'])
            player['protected'] = True
            repo.put('players', player)

        repo.put('rewards', dict(
            id=key,
            franchise_id=challenge['franchise_id'],
            run_id=challenge['run_id'],
            type=challenge['reward'],
            player_id=challenge['player_id'],
            status='earned',
        ))

    elif not passed and previous:
        if previous['status'] != 'correction_review':
            previous['status'] = 'correction_review'
            repo.put('rewards', previous)


def confirm_manual(repo, fid, cid, passed, evidence):
    from services.franchise_service import audit

    with repo.transaction():
        challenge = repo.get('challenges', cid)
        if (
            not challenge
            or challenge['franchise_id'] != fid
            or challenge['status'] != 'awaiting_manual'
            or not evidence.strip()
        ):
            raise RuleError(
                'Select a pending manual challenge and provide evidence.'
            )

        before = dict(challenge)
        challenge.update(
            status='passed' if passed else 'failed',
            evidence=evidence,
        )
        repo.put('challenges', challenge)
        settle(repo, challenge, passed)
        audit(
            repo, fid, 'challenge_evidence',
            before, challenge, evidence, challenge['run_id'],
        )


def _development_season(challenge, runs_by_id):
    """Use the season in which the challenge was earned."""
    if challenge.get('development_season_id'):
        return challenge['development_season_id']

    source_run = runs_by_id.get(
        challenge.get('breakout_run') or challenge.get('run_id')
    )
    return source_run.get('season_id') if source_run else None


def _development_allowed(repo, fid, season_id):
    challenges = [
        challenge
        for challenge in repo.list('challenges', fid)
        if challenge.get('reward') == 'upgrade'
    ]

    # Existing challenges also block new assignments until they finish.
    if any(
        challenge['status'] in OPEN_STATUSES
        for challenge in challenges
    ):
        return False

    runs_by_id = {
        run['id']: run for run in repo.list('runs', fid)
    }
    assigned_this_season = sum(
        _development_season(challenge, runs_by_id) == season_id
        for challenge in challenges
    )

    # Failed challenges count as attempts too.
    return assigned_this_season < DEVELOPMENT_LIMIT_PER_SEASON


def _player_can_develop(repo, fid, run_id, player_id):
    challenges = repo.list('challenges', fid)

    if any(
        challenge['player_id'] == player_id
        and challenge.get('reward') == 'upgrade'
        and (
            challenge['status'] in OPEN_STATUSES
            or challenge.get('breakout_run') == run_id
        )
        for challenge in challenges
    ):
        return False

    if any(
        move.get('target') == player_id
        and move['type'] == 'upgrade'
        and move['status'] in ['pending', 'deferred']
        for move in repo.list('moves', fid)
    ):
        return False

    return True


def assign_development(
    repo, fid, run_id, player_id,
    game_id=None,
    reason='Breakout performance',
    goal=None,
):
    """Assign a next-week goal subject to franchise development limits."""
    with repo.transaction():
        player = repo.get('players', player_id)
        run = repo.get('runs', run_id)
        franchise = repo.get('franchises', fid)

        if (
            not player
            or player['franchise_id'] != fid
            or not run
            or run['franchise_id'] != fid
            or player_id not in run['roster_ids']
        ):
            raise RuleError('Choose a player from this week’s roster.')

        season_id = run.get('season_id')
        season = (
            repo.get('seasons', season_id) if season_id else None
        )
        if (
            not franchise
            or not season
            or season['franchise_id'] != fid
            or franchise.get('current_season') != season_id
            or season.get('status') != 'active'
        ):
            raise RuleError(
                'Development must be earned in the current active season.'
            )

        if game_id:
            game = repo.get('games', game_id)
            if (
                not game
                or game['franchise_id'] != fid
                or game['run_id'] != run_id
            ):
                raise RuleError('Invalid development source game.')

        if not _development_allowed(repo, fid, season_id):
            return None

        if not _player_can_develop(repo, fid, run_id, player_id):
            return None

        pitcher_role = None

        if player['kind'] == 'hitter':
            if goal is None:
                selected = secrets.choice(HITTER_GOALS)
            else:
                selected = next(
                    (
                        item for item in HITTER_GOALS
                        if item[0] == goal
                    ),
                    None,
                )
                if selected is None:
                    raise RuleError('Unknown hitter development goal.')

            metric, threshold, goal_text = selected

        else:
            if goal not in [None, 'so']:
                raise RuleError('Unknown pitcher development goal.')

            # Use the role from the breakout appearance when available.
            source_stats = [
                stat
                for stat in repo.list('stats', fid, run_id)
                if stat['player_id'] == player_id
                and game_id
                and stat['game_id'] == game_id
            ]

            is_starter = (
                bool(source_stats[0]['line'].get('starts', 0))
                if source_stats
                else player['area'] == 'rotation'
            )

            pitcher_role = 'starter' if is_starter else 'reliever'
            metric = 'so'
            threshold = 6 if is_starter else 4
            goal_text = f'Record {threshold} strikeouts'

        cid = create(
            repo, fid, run_id, player_id,
            'Development: '
            + goal_text
            + ' across the entire next week/run to earn '
            'the next available higher-rated Event-legal '
            'card of this player.',
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
            development_season_id=season_id,
            development_reason=reason,
            development_rules_version=2,
        )
        if pitcher_role:
            challenge['development_pitcher_role'] = pitcher_role

        repo.put('challenges', challenge)
        return cid


def unlock_development(repo, fid, run_id, game_id):
    """Award at most one challenge from a qualifying saved game."""
    with repo.transaction():
        run = repo.get('runs', run_id)
        game = repo.get('games', game_id)
        franchise = repo.get('franchises', fid)

        if (
            not run
            or run['franchise_id'] != fid
            or not game
            or game['franchise_id'] != fid
            or game['run_id'] != run_id
        ):
            raise RuleError('Invalid development source game.')

        season_id = run.get('season_id')
        if (
            not franchise
            or not season_id
            or franchise.get('current_season') != season_id
            or game.get('recovered')
        ):
            return

        if not _development_allowed(repo, fid, season_id):
            return

        candidates = []

        for stat in repo.list('stats', fid, run_id):
            if stat['game_id'] != game_id:
                continue

            player = repo.get('players', stat['player_id'])
            if (
                not player
                or player['franchise_id'] != fid
                or not _player_can_develop(
                    repo, fid, run_id, player['id'],
                )
            ):
                continue

            line = stat['line']
            if player['kind'] == 'hitter':
                breakout = (
                    line.get('hr', 0) >= 1
                    or line.get('h', 0) >= 2
                )

            elif line.get('starts', 0):
                breakout = (
                    line.get('outs', 0) >= 6
                    and line.get('er', 0) == 0
                    and line.get('so', 0) >= 3
                )

            else:
                breakout = (
                    line.get('outs', 0) >= 3
                    and line.get('r', 0) == 0
                    and line.get('so', 0) >= 2
                )

            if breakout:
                candidates.append(player['id'])

        if candidates:
            # Avoid favoring whoever appears first in the stat-entry table.
            player_id = secrets.choice(candidates)
            assign_development(
                repo, fid, run_id, player_id,
                game_id=game_id,
                reason='Saved breakout stat line',
            )
