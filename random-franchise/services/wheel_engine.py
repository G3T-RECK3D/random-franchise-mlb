import random

from models.domain import RuleError, State, now, uid
from services.game_engine import enqueue
from services.franchise_service import settings
from services.roster_service import target_pool, protected
from services.stat_engine import aggregate
from services.challenge_service import create
from services.reunion_service import reunion_pool


def trade_position_options(kind):
    if kind == 'hitter':
        groups = {
            'Catcher': ['C'],
            'First Base': ['1B'],
            'Second Base': ['2B'],
            'Third Base': ['3B'],
            'Shortstop': ['SS'],
            'Left Field': ['LF'],
            'Center Field': ['CF'],
            'Right Field': ['RF'],
            'Designated Hitter': ['DH'],
            'Infield': ['1B', '2B', '3B', 'SS'],
            'Outfield': ['LF', 'CF', 'RF'],
            'Corner Infield': ['1B', '3B'],
            'Middle Infield': ['2B', 'SS'],
        }
    elif kind == 'pitcher':
        groups = {
            'Starting Pitcher': ['SP'],
            'Relief Pitcher': ['RP'],
            'Closing Pitcher': ['CP'],
            'Any Reliever': ['RP', 'CP'],
            'Any Pitcher': ['SP', 'RP', 'CP'],
        }
    else:
        raise RuleError('Trade target must be a hitter or pitcher.')

    return [
        dict(
            id='trade_position:' + str(index),
            text=label,
            weight=1,
            active=True,
            effect='trade_position',
            positions=positions,
            description='Incoming card primary position: '
                        + ', '.join(positions),
        )
        for index, (label, positions) in enumerate(groups.items())
    ]


def trade_market_options():
    divisions = {
        'AL East': [
            'Baltimore Orioles', 'Boston Red Sox', 'New York Yankees',
            'Tampa Bay Rays', 'Toronto Blue Jays',
        ],
        'AL Central': [
            'Chicago White Sox', 'Cleveland Guardians', 'Detroit Tigers',
            'Kansas City Royals', 'Minnesota Twins',
        ],
        'AL West': [
            'Athletics', 'Houston Astros', 'Los Angeles Angels',
            'Seattle Mariners', 'Texas Rangers',
        ],
        'NL East': [
            'Atlanta Braves', 'Miami Marlins', 'New York Mets',
            'Philadelphia Phillies', 'Washington Nationals',
        ],
        'NL Central': [
            'Chicago Cubs', 'Cincinnati Reds', 'Milwaukee Brewers',
            'Pittsburgh Pirates', 'St. Louis Cardinals',
        ],
        'NL West': [
            'Arizona Diamondbacks', 'Colorado Rockies',
            'Los Angeles Dodgers', 'San Diego Padres',
            'San Francisco Giants',
        ],
    }

    markets = {}
    for teams in divisions.values():
        for team in teams:
            markets[team] = [team]

    for division, teams in divisions.items():
        markets[division] = list(teams)

    for prefix, label in [
        ('AL', 'American League'),
        ('NL', 'National League'),
    ]:
        markets[label] = [
            team
            for division, teams in divisions.items()
            if division.startswith(prefix)
            for team in teams
        ]

    return [
        dict(
            id='trade_market:' + str(index),
            text=label,
            weight=1,
            active=True,
            effect='trade_market',
            teams=teams,
            description='Choose an incoming card from: '
                        + ', '.join(teams),
        )
        for index, (label, teams) in enumerate(markets.items())
    ]


def current_job(repo, fid):
    franchise = repo.get('franchises', fid)
    return franchise['queue'][0] if franchise['queue'] else None


def _targets(repo, fid, wedge):
    eligibility = wedge.get('eligibility', {})

    if wedge.get('effect') == 'reunion':
        pool = reunion_pool(repo, fid)
        if eligibility.get('kind'):
            pool = [
                player for player in pool
                if player['kind'] == eligibility['kind']
            ]
        return pool

    pool = target_pool(repo, fid, eligibility.get('kind'))

    if wedge.get('effect') in [
        'hot_seat', 'protect', 'challenge', 'arrangement',
    ]:
        pool = [
            player
            for player in repo.list('players', fid)
            if player['area'] in [
                'lineup', 'bench', 'rotation', 'bullpen',
            ]
            and (
                not eligibility.get('kind')
                or player['kind'] == eligibility['kind']
            )
        ]

    if wedge.get('effect') == 'unprotect':
        pool = [
            player for player in repo.list('players', fid)
            if player.get('protected')
        ]

    if eligibility.get('area'):
        pool = [
            player for player in pool
            if player['area'] == eligibility['area']
        ]

    if eligibility.get('hot_seat'):
        pool = [
            player for player in pool if player.get('hot_seat')
        ]

    if eligibility.get('failed_challenge'):
        failed = {
            challenge['player_id']
            for challenge in repo.list('challenges', fid)
            if challenge['status'] == 'failed'
        }
        pool = [
            player for player in pool if player['id'] in failed
        ]

    return pool


def _performance(repo, fid, player):
    franchise = repo.get('franchises', fid)
    totals = aggregate(repo, fid, player, franchise['current_run'])
    return (
        totals.get('ops', 0)
        if player['kind'] == 'hitter'
        else -totals.get('era', 0)
    )


def available(repo, fid, job):
    if job['wheel_id'] == 'trade_market':
        return trade_market_options()

    if job['wheel_id'] == 'trade_position':
        kind = job.get('trade_context', {}).get('kind')
        return trade_position_options(kind)

    wheel = repo.get('wheels', f"{fid}:{job['wheel_id']}")
    if not wheel:
        raise RuleError('Wheel configuration missing.')

    if job['wheel_id'] == 'dfa_target':
        pool = sorted(
            target_pool(repo, fid),
            key=lambda player: (
                _performance(repo, fid, player), player['ovr'],
            ),
        )[:3]
        return [
            dict(
                id=player['id'],
                text='DFA ' + player['name'],
                weight=1,
                active=True,
                effect='dfa',
                selector='fixed',
                target_id=player['id'],
                eligibility={'needs_target': True},
                description='Bottom-three eligible player',
            )
            for player in pool
        ]

    cfg = settings(repo, fid)
    options = []

    for wedge in wheel['wedges']:
        if (
            not cfg.get('special_wheels', True)
            and wedge.get('follow_up') in [
                'premium', 'tag_hitter', 'tag_pitcher',
            ]
        ):
            continue

        if (
            not wedge.get('active', True)
            or wedge.get('weight', 1) <= 0
        ):
            continue

        if job.get('depth', 0) >= 4 and (
            wedge.get('follow_up')
            or wedge.get('effect') == 'extra_spin'
        ):
            continue

        eligibility = wedge.get('eligibility', {})

        if wedge.get('effect') == 'reunion':
            if (
                wedge.get('quantity', 1) != 1
                or wedge.get('follow_up')
                or not _targets(repo, fid, wedge)
            ):
                continue
        elif eligibility.get('kind') and job.get('target'):
            player = repo.get('players', job['target'])
            if player and player['kind'] != eligibility['kind']:
                continue

        if (
            eligibility.get('needs_target')
            and len(_targets(repo, fid, wedge))
            < wedge.get('quantity', 1)
        ):
            continue

        if eligibility.get('needs_bench') and not any(
            player['area'] == 'bench'
            for player in repo.list('players', fid)
        ):
            continue

        if eligibility.get('needs_protection') and not any(
            player.get('protected')
            for player in repo.list('players', fid)
        ):
            continue

        options.append(dict(wedge))

    return options


def _choose_target(repo, fid, wedge, job):
    pool = _targets(repo, fid, wedge)

    # Reunion chooses from former cards, never an inherited active target.
    if wedge.get('effect') == 'reunion':
        return random.SystemRandom().choice(pool) if pool else None

    if wedge.get('target_id'):
        return next(
            (
                player for player in pool
                if player['id'] == wedge['target_id']
            ),
            None,
        )

    if job.get('target'):
        target = repo.get('players', job['target'])
        if target and (
            wedge.get('effect') not in ['dfa', 'demote', 'trade']
            or not protected(repo, fid, target)
        ):
            return target

    if not pool:
        return None

    selector = wedge.get('selector', 'random')
    if selector == 'lowest':
        return min(pool, key=lambda player: player['ovr'])
    if selector == 'highest':
        return max(pool, key=lambda player: player['ovr'])
    if selector == 'worst':
        return min(
            pool,
            key=lambda player: (
                _performance(repo, fid, player), player['ovr'],
            ),
        )
    if selector == 'bottom3':
        pool = sorted(
            pool,
            key=lambda player: (
                _performance(repo, fid, player), player['ovr'],
            ),
        )[:3]

    return random.SystemRandom().choice(pool)


def _bank(repo, fid, job, saved_spin, wedge, target):
    key = f"move:{saved_spin['id']}"
    if repo.get('moves', key):
        return

    kind = wedge.get('effect', 'acquire')
    constraints = {
        'instruction': wedge.get('description', wedge['text']),
        'branch': list(job.get('constraints', [])),
        'quantity': wedge.get('quantity', 1),
    }
    description = wedge['text']

    if kind == 'reunion':
        if not target or target['franchise_id'] != fid:
            raise RuleError('The selected reunion card is unavailable.')
        constraints.update(
            player_id=target['id'],
            card_uuid=target.get('card_uuid'),
            kind=target['kind'],
            ovr=target['ovr'],
            version=target.get('version', ''),
            series=target.get('series', ''),
        )
        description += (
            ' · ' + target['name']
            + ' · ' + str(target['ovr']) + ' OVR'
        )

    repo.put('moves', dict(
        id=key,
        franchise_id=fid,
        run_id=saved_spin['run_id'],
        game_id=job.get('game_id'),
        created_at=now(),
        source=job['source'],
        spin_id=saved_spin['id'],
        type=kind,
        target=target['id'] if target else None,
        description=description,
        constraints=constraints,
        status='pending',
        critical=kind in ['dfa', 'demote', 'trade', 'tag'],
        resolution_notes='',
    ))


def spin(repo, fid, job_id):
    with repo.transaction():
        existing = repo.get('spins', job_id)
        if existing:
            if existing['franchise_id'] != fid:
                raise RuleError('Spin belongs to another franchise.')
            return existing

        franchise = repo.get('franchises', fid)
        job = current_job(repo, fid)
        if (
            franchise['state'] != State.WHEEL
            or not job
            or job['id'] != job_id
        ):
            raise RuleError('This spin is not the current required action.')

        options = available(repo, fid, job)
        if not options:
            outcome = dict(
                id='impossible',
                text='No eligible options — branch deferred',
                effect='deferred',
            )
        else:
            outcome = random.SystemRandom().choices(
                options,
                weights=[wedge.get('weight', 1) for wedge in options],
                k=1,
            )[0]

        target = _choose_target(repo, fid, outcome, job)
        if outcome.get('effect') == 'reunion' and not target:
            raise RuleError('No eligible former card is available.')

        record = dict(
            id=job_id,
            franchise_id=fid,
            run_id=franchise['current_run'],
            game_id=job.get('game_id'),
            wheel_id=job['wheel_id'],
            result=outcome,
            available=options,
            target=target['id'] if target else None,
            created_at=now(),
            reroll_reason=(
                'Impossible child only'
                if not options else job.get('reroll_reason')
            ),
            admin_note='',
            job=dict(job),
            parent_spin=job.get('parent_spin'),
        )
        repo.put('spins', record)
        return record


def _bank_trade_result(repo, fid, saved_spin, context):
    original = context['original_result']
    key = 'move:' + context['original_spin_id']
    if repo.get('moves', key):
        return

    constraints = {
        'instruction': original.get('description', original['text']),
        'branch': list(context.get('branch', [])),
        'quantity': 1,
        'kind': context['kind'],
        'teams': list(context['teams']),
        'positions': list(context['positions']),
        'market_label': context['market_label'],
        'position_label': context['position_label'],
    }
    if context.get('max_ovr') is not None:
        constraints['max_ovr'] = context['max_ovr']

    repo.put('moves', dict(
        id=key,
        franchise_id=fid,
        run_id=saved_spin['run_id'],
        game_id=context.get('game_id'),
        created_at=now(),
        source=context['source'],
        spin_id=context['original_spin_id'],
        type='trade',
        target=context['target'],
        description=(
            original['text'] + ' · '
            + context['market_label'] + ' · '
            + context['position_label']
        ),
        constraints=constraints,
        status='pending',
        critical=True,
        resolution_notes='',
    ))


def _queue_trade_step(
    repo, fid, franchise, job, saved_spin, wheel_id, context,
):
    enqueue(
        franchise,
        wheel_id,
        job['source'],
        job.get('game_id'),
        context['target'],
        job.get('depth', 0) + 1,
    )
    next_job = franchise['queue'].pop()
    next_job['trade_context'] = dict(context)
    next_job['constraints'] = list(job.get('constraints', []))
    next_job['parent_spin'] = saved_spin['id']
    franchise['queue'].insert(0, next_job)


def continue_spin(repo, fid, job_id, acknowledged=False):
    with repo.transaction():
        franchise = repo.get('franchises', fid)
        job = current_job(repo, fid)
        if not job or job['id'] != job_id:
            return

        saved_spin = repo.get('spins', job_id)
        if not saved_spin:
            raise RuleError('Spin the wheel first.')

        wedge = saved_spin['result']
        effect = wedge.get('effect', 'acquire')

        if effect == 'arrangement' and not acknowledged:
            raise RuleError(
                'Apply the legal arrangement in Roster Manager '
                'and confirm it before continuing.'
            )

        target = (
            repo.get('players', saved_spin['target'])
            if saved_spin.get('target') else None
        )
        if effect == 'reunion' and (
            not target or target['franchise_id'] != fid
        ):
            raise RuleError('The selected reunion card is unavailable.')

        franchise['queue'].pop(0)
        follow = wedge.get('follow_up')

        if follow:
            children = wedge.get('quantity', 1)
            for _ in range(children):
                enqueue(
                    franchise, follow, job['source'],
                    job.get('game_id'), job.get('target'),
                    job.get('depth', 0) + 1,
                )
                franchise['queue'][-1]['constraints'] = (
                    job.get('constraints', []) + [wedge['text']]
                )
                franchise['queue'][-1]['parent_spin'] = saved_spin['id']

            new = franchise['queue'][-children:]
            franchise['queue'] = new + franchise['queue'][:-children]

        elif effect == 'trade_market':
            context = dict(job['trade_context'])
            context['teams'] = list(wedge['teams'])
            context['market_label'] = wedge['text']
            _queue_trade_step(
                repo, fid, franchise, job, saved_spin,
                'trade_position', context,
            )
            franchise['queue'][0]['constraints'].append(
                'Incoming market: ' + wedge['text']
            )

        elif effect == 'trade_position':
            context = dict(job['trade_context'])
            context['positions'] = list(wedge['positions'])
            context['position_label'] = wedge['text']
            _bank_trade_result(repo, fid, saved_spin, context)

        elif effect == 'trade':
            if not target:
                raise RuleError('This trade needs an outgoing player.')
            if wedge.get('quantity', 1) != 1:
                raise RuleError(
                    'The new trade sequence supports one outgoing player.'
                )

            title = wedge['text'].strip().casefold()
            forced = (
                'forced trade' in title
                or title in [
                    'trade random starter', 'future trade candidate',
                ]
                or job['wheel_id'] in ['elimination', 'meltdown']
            )
            context = {
                'original_spin_id': saved_spin['id'],
                'original_result': dict(wedge),
                'target': target['id'],
                'kind': target['kind'],
                'max_ovr': target['ovr'] if forced else None,
                'game_id': job.get('game_id'),
                'source': job['source'],
                'branch': list(job.get('constraints', [])),
            }
            _queue_trade_step(
                repo, fid, franchise, job, saved_spin,
                'trade_market', context,
            )
            franchise['queue'][0]['constraints'].append(
                'Original trade: ' + wedge['text']
            )

        elif effect == 'reunion':
            _bank(repo, fid, job, saved_spin, wedge, target)

        elif effect == 'extra_spin':
            for _ in range(wedge.get('quantity', 1)):
                enqueue(
                    franchise, job['wheel_id'], job['source'],
                    job.get('game_id'), job.get('target'),
                    job.get('depth', 0) + 1,
                )

        elif effect == 'protect' and 'Next Run' in wedge['text']:
            _bank(repo, fid, job, saved_spin, wedge, target)

        elif effect in ['hot_seat', 'protect', 'unprotect']:
            if target:
                field = 'hot_seat' if effect == 'hot_seat' else 'protected'
                target[field] = effect != 'unprotect'
                repo.put('players', target)

                if effect == 'hot_seat' and wedge.get('quantity', 1) > 1:
                    extra = [
                        player for player in _targets(repo, fid, wedge)
                        if player['id'] != target['id']
                    ][:wedge['quantity'] - 1]
                    for player in extra:
                        player['hot_seat'] = True
                        repo.put('players', player)

        elif effect == 'challenge' and target:
            create(
                repo, fid, franchise['current_run'], target['id'],
                wedge['text'], wedge.get('metric'),
                wedge.get('threshold', 1),
                wedge.get('scope', 'next_game'),
                wedge.get('reward', 'protection'),
                job.get('game_id'),
            )

        elif effect == 'tag' and target:
            from services.franchise_tag_service import grant

            if grant(
                repo, fid, target['id'], source=wedge['text'],
            ) == 'cap_decision_required':
                _bank(repo, fid, job, saved_spin, wedge, target)

        elif effect == 'arrangement':
            from services.franchise_service import audit

            audit(
                repo, fid, 'manual_wheel_arrangement', None, wedge,
                'Creator confirms legal in-game arrangement',
                franchise['current_run'],
            )

        elif effect not in ['none', 'challenge']:
            _bank(repo, fid, job, saved_spin, wedge, target)
            if effect == 'deferred':
                move = repo.get('moves', f"move:{saved_spin['id']}")
                move.update(status='deferred', critical=False)
                repo.put('moves', move)

        franchise['state'] = (
            State.WHEEL if franchise['queue']
            else franchise['return_state']
        )
        repo.put('franchises', franchise)


def retry_impossible_branch(repo, fid, job_id):
    """Retry an impossible child only after eligible options exist."""
    with repo.transaction():
        franchise = repo.get('franchises', fid)
        job = current_job(repo, fid)
        original = repo.get('spins', job_id)

        if (
            not job
            or job['id'] != job_id
            or not original
            or original['result']['id'] != 'impossible'
            or not job.get('parent_spin')
        ):
            raise RuleError(
                'Only an impossible nested branch has retry permission.'
            )

        if not available(repo, fid, job):
            raise RuleError(
                'This branch still has no eligible options. '
                'Defer it instead.'
            )

        replacement = dict(
            job,
            id=uid(),
            reroll_reason='Retry of impossible nested branch',
            retried_spin=job_id,
        )
        franchise['queue'][0] = replacement
        repo.put('franchises', franchise)
        return replacement['id']
