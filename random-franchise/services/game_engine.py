from models.domain import RuleError, uid, now
from services.stat_engine import aggregate
from services.franchise_tag_service import grant


OPEN_STATUSES = [
    'waiting_next_run',
    'active',
    'awaiting_manual',
]


def create(
    repo,
    fid,
    run_id,
    pid,
    description,
    metric=None,
    threshold=1,
    scope='next_game',
    reward='protection',
    game_id=None,
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
    """Count only the first three future saved team games."""
    excluded = set(challenge.get('excluded_game_ids', []))
    games = [
        game
        for game in repo.list(
            'games', challenge['franchise_id']
        )
        if game['id'] not in excluded
        and not game.get('recovered')
    ][:challenge.get('game_limit', 3)]

    game_ids = {game['id'] for game in games}
    totals = {}

    for stat in repo.list(
        'stats', challenge['franchise_id']
    ):
        if (
            stat['player_id'] == challenge['player_id']
            and stat['game_id'] in game_ids
        ):
            for field, value in stat['line'].items():
                totals[field] = totals.get(field, 0) + value

    goals = challenge.get('goals', {})
    passed = any(
        totals.get(field, 0) >= target
        for field, target in goals.items()
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
    if not game or game['franchise_id'] != fid:
        raise RuleError('Select a valid game.')

    # Three-game challenges can continue into another week.
    for challenge in repo.list('challenges', fid):
        if challenge['status'] not in [
            'active', 'passed', 'failed', 'awaiting_manual'
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

        # Preserve the behavior of older wheel challenges.
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
            closed = bool(
                repo.get('runs', run_id)['ended_at']
            )

        if challenge.get('metric'):
            player = repo.get(
                'players', challenge['player_id']
            )
            if not player:
                continue

            totals = aggregate(
                repo,
                fid,
                player,
                run_id,
                relevant['id']
                if challenge['scope'] == 'next_game'
                else None,
            )
            passed = (
                totals.get(challenge['metric'], 0)
                >= challenge['threshold']
            )

            if passed or closed:
                challenge['status'] = (
                    'passed' if passed else 'failed'
                )
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
            player = repo.get(
                'players', challenge['player_id']
            )
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
                    + ' — next available higher-rated '
                    'Event-legal card'
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
                        'Tag cap decision: '
                        + challenge['description']
                    ),
                    constraints={},
                    status='pending',
                    critical=True,
                    created_at=now(),
                    source='challenge',
                ))

        else:
            player = repo.get(
                'players', challenge['player_id']
            )
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
        # Flag corrected results; never repeat or silently undo rewards.
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
                'Select a pending manual challenge '
                'and provide evidence.'
            )

        before = dict(challenge)
        challenge.update(
            status='passed' if passed else 'failed',
            evidence=evidence,
        )
        repo.put('challenges', challenge)
        settle(repo, challenge, passed)
        audit(
            repo,
            fid,
            'challenge_evidence',
            before,
            challenge,
            evidence,
            challenge['run_id'],
        )


def assign_development(
    repo,
    fid,
    run_id,
    player_id,
    game_id=None,
    reason='Breakout performance',
):
    """Assign once; exclude every game already saved at assignment."""
    with repo.transaction():
        player = repo.get('players', player_id)
        run = repo.get('runs', run_id)

        if (
            not player
            or player['franchise_id'] != fid
            or not run
            or run['franchise_id'] != fid
            or player_id not in run['roster_ids']
        ):
            raise RuleError(
                'Choose a player from this week’s roster.'
            )

        if game_id:
            game = repo.get('games', game_id)
            if (
                not game
                or game['franchise_id'] != fid
                or game['run_id'] != run_id
            ):
                raise RuleError('Invalid development source game.')

        challenges = repo.list('challenges', fid)

        already_open = any(
            challenge['player_id'] == player_id
            and challenge.get('reward') == 'upgrade'
            and challenge['status'] in OPEN_STATUSES
            for challenge in challenges
        )
        earned_this_week = any(
            challenge['player_id'] == player_id
            and challenge.get('reward') == 'upgrade'
            and challenge.get('breakout_run') == run_id
            for challenge in challenges
        )
        upgrade_waiting = any(
            move.get('target') == player_id
            and move['type'] == 'upgrade'
            and move['status'] in ['pending', 'deferred']
            for move in repo.list('moves', fid)
        )

        if already_open or earned_this_week or upgrade_waiting:
            return None

        if player['kind'] == 'hitter':
            goals = {'hr': 2, 'h': 4}
            goal_text = 'Hit 2 home runs OR collect 4 hits'
        else:
            goals = {'so': 5}
            goal_text = 'Record 5 strikeouts'

        cid = create(
            repo,
            fid,
            run_id,
            player_id,
            'Development: '
            + goal_text
            + ' within the next 3 team games to earn '
            'the next available higher-rated Event-legal '
            'card of this player.',
            scope='three_games',
            reward='upgrade',
            game_id=game_id,
        )

        challenge = repo.get('challenges', cid)
        challenge.update(
            goals=goals,
            game_limit=3,
            excluded_game_ids=[
                game['id']
                for game in repo.list('games', fid)
            ],
            breakout_run=run_id,
            breakout_game=game_id,
            development_reason=reason,
        )
        repo.put('challenges', challenge)
        return cid


def unlock_development(repo, fid, run_id, game_id):
    """Check saved performances after each new game."""
    for stat in repo.list('stats', fid, run_id):
        if stat['game_id'] != game_id:
            continue

        player = repo.get('players', stat['player_id'])
        if not player:
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
            assign_development(
                repo,
                fid,
                run_id,
                player['id'],
                game_id=game_id,
                reason='Saved breakout stat line',
            )
