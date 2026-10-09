import random
from models.domain import RuleError, State, now, uid
from services.game_engine import enqueue
from services.franchise_service import settings
from services.roster_service import target_pool, protected
from services.stat_engine import aggregate
from services.challenge_service import create

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
    f = repo.get('franchises', fid)
    return f['queue'][0] if f['queue'] else None


def _targets(repo, fid, wedge):
    eligibility = wedge.get('eligibility', {})
    pool = target_pool(repo, fid, eligibility.get('kind'))
    if wedge.get('effect') in ['hot_seat', 'protect', 'challenge', 'arrangement']:
        pool = [p for p in repo.list('players', fid) if p['area'] in ['lineup', 'bench', 'rotation', 'bullpen'] and (not eligibility.get('kind') or p['kind'] == eligibility['kind'])]
    if wedge.get('effect') == 'unprotect':
        pool = [p for p in repo.list('players', fid) if p.get('protected')]
    if eligibility.get('area'):
        pool = [p for p in pool if p['area'] == eligibility['area']]
    if eligibility.get('hot_seat'):
        pool = [p for p in pool if p.get('hot_seat')]
    if eligibility.get('failed_challenge'):
        failed = {c['player_id'] for c in repo.list('challenges', fid) if c['status'] == 'failed'}
        pool = [p for p in pool if p['id'] in failed]
    return pool


def _performance(repo, fid, p):
    f = repo.get('franchises', fid)
    t = aggregate(repo, fid, p, f['current_run'])
    return t.get('ops', 0) if p['kind'] == 'hitter' else -t.get('era', 0)


def available(repo, fid, job):
    if job['wheel_id'] == 'trade_market':
        return trade_market_options()

    if job['wheel_id'] == 'trade_position':
        kind = job.get('trade_context', {}).get('kind')
        return trade_position_options(kind)

    wheel = repo.get('wheels', f"{fid}:{job['wheel_id']}")
    if not wheel:
        raise RuleError('Wheel configuration missing.')
    options = []
    if job['wheel_id'] == 'dfa_target':
        pool = sorted(target_pool(repo, fid), key=lambda p: (_performance(repo, fid, p), p['ovr']))[:3]
        return [dict(id=p['id'], text='DFA ' + p['name'], weight=1, active=True, effect='dfa',
                     selector='fixed', target_id=p['id'], eligibility={'needs_target': True}, description='Bottom-three eligible player') for p in pool]
    for w in wheel['wedges']:
        if not settings(repo, fid).get('special_wheels', True) and w.get('follow_up') in ['premium', 'tag_hitter', 'tag_pitcher']:
            continue
        if not w.get('active', True) or w.get('weight', 1) <= 0:
            continue
        if job.get('depth', 0) >= 4 and (w.get('follow_up') or w.get('effect') == 'extra_spin'):
            continue  # bounded recursive bonus chains
        e = w.get('eligibility', {})
        if e.get('kind') and job.get('target'):
            p = repo.get('players', job['target'])
            if p and p['kind'] != e['kind']:
                continue
        if e.get('needs_target') and len(_targets(repo, fid, w)) < w.get('quantity', 1):
            continue
        if e.get('needs_bench') and not any(p['area'] == 'bench' for p in repo.list('players', fid)):
            continue
        if e.get('needs_protection') and not any(p.get('protected') for p in repo.list('players', fid)):
            continue
        options.append(dict(w))
    return options


def _choose_target(repo, fid, wedge, job):
    pool = _targets(repo, fid, wedge)
    if wedge.get('target_id'):
        return next((p for p in pool if p['id'] == wedge['target_id']), None)
    if job.get('target'):
        target = repo.get('players', job['target'])
        if target and (wedge.get('effect') not in ['dfa', 'demote', 'trade'] or not protected(repo, fid, target)):
            return target
    if not pool:
        return None
    selector = wedge.get('selector', 'random')
    if selector == 'lowest':
        return min(pool, key=lambda p: p['ovr'])
    if selector == 'highest':
        return max(pool, key=lambda p: p['ovr'])
    if selector == 'worst':
        return min(pool, key=lambda p: (_performance(repo, fid, p), p['ovr']))
    if selector == 'bottom3':
        pool = sorted(pool, key=lambda p: (_performance(repo, fid, p), p['ovr']))[:3]
    return random.SystemRandom().choice(pool)


def _bank(repo, fid, job, spin, wedge, target):
    key = f"move:{spin['id']}"
    kind = wedge.get('effect', 'acquire')
    repo.put('moves', dict(id=key, franchise_id=fid, run_id=spin['run_id'], game_id=job.get('game_id'),
        created_at=now(), source=job['source'], spin_id=spin['id'], type=kind,
        target=target['id'] if target else None, description=wedge['text'],
        constraints={'instruction': wedge.get('description', wedge['text']), 'branch': list(job.get('constraints', [])),
                     'quantity': wedge.get('quantity', 1)}, status='pending',
        critical=kind in ['dfa', 'demote', 'trade', 'tag'], resolution_notes=''))


def spin(repo, fid, job_id):
    with repo.transaction():
        existing = repo.get('spins', job_id)
        if existing:
            if existing['franchise_id'] != fid:
                raise RuleError('Spin belongs to another franchise.')
            return existing
        f = repo.get('franchises', fid)
        job = current_job(repo, fid)
        if f['state'] != State.WHEEL or not job or job['id'] != job_id:
            raise RuleError('This spin is not the current required action.')
        options = available(repo, fid, job)
        # Impossible nested branch: preserve parent result and only void this child.
        if not options:
            outcome = dict(id='impossible', text='No eligible options — branch deferred', effect='deferred')
        else:
            outcome = random.SystemRandom().choices(options, weights=[w.get('weight', 1) for w in options], k=1)[0]
        target = _choose_target(repo, fid, outcome, job)
        record = dict(id=job_id, franchise_id=fid, run_id=f['current_run'], game_id=job.get('game_id'),
            wheel_id=job['wheel_id'], result=outcome, available=options, target=target['id'] if target else None,
            created_at=now(), reroll_reason='Impossible child only' if not options else job.get('reroll_reason'),
            admin_note='', job=dict(job), parent_spin=job.get('parent_spin'))
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
def _queue_trade_step(repo, fid, franchise, job, saved_spin,
                      wheel_id, context):
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
        f = repo.get('franchises', fid)
        job = current_job(repo, fid)
        if not job or job['id'] != job_id:
            return  # repeated Continue is harmless
        s = repo.get('spins', job_id)
        if not s:
            raise RuleError('Spin the wheel first.')
        w = s['result']
        effect = w.get('effect', 'acquire')
        if effect == 'arrangement' and not acknowledged:
            raise RuleError('Apply the legal arrangement in Roster Manager and confirm it before continuing.')
        f['queue'].pop(0)
        target = repo.get('players', s['target']) if s.get('target') else None
        follow = w.get('follow_up')
        if follow:
            children = w.get('quantity', 1)
            for _ in range(children):
                enqueue(f, follow, job['source'], job.get('game_id'), job.get('target'), job.get('depth', 0) + 1)
                f['queue'][-1]['constraints'] = job.get('constraints', []) + [w['text']]
                f['queue'][-1]['parent_spin'] = s['id']
            # Keep nested branch before unrelated milestone jobs.
            new = f['queue'][-children:]
            f['queue'] = new + f['queue'][:-children]
        elif effect == 'extra_spin':
            for _ in range(w.get('quantity', 1)):
                enqueue(f, job['wheel_id'], job['source'], job.get('game_id'), job.get('target'), job.get('depth', 0) + 1)
        elif effect == 'protect' and 'Next Run' in w['text']:
            _bank(repo, fid, job, s, w, target)
        elif effect in ['hot_seat', 'protect', 'unprotect']:
            if target:
                target['hot_seat' if effect == 'hot_seat' else 'protected'] = effect != 'unprotect'
                repo.put('players', target)
                if effect == 'hot_seat' and w.get('quantity', 1) > 1:
                    extra = [p for p in _targets(repo, fid, w) if p['id'] != target['id']][:w['quantity'] - 1]
                    for p in extra:
                        p['hot_seat'] = True
                        repo.put('players', p)
        elif effect == 'challenge' and target:
            create(repo, fid, f['current_run'], target['id'], w['text'], w.get('metric'), w.get('threshold', 1),
                   w.get('scope', 'next_game'), w.get('reward', 'protection'), job.get('game_id'))
        elif effect == 'tag' and target:
            from services.franchise_tag_service import grant
            if grant(repo, fid, target['id'], source=w['text']) == 'cap_decision_required':
                _bank(repo, fid, job, s, w, target)
        elif effect == 'arrangement':
            from services.franchise_service import audit
            audit(repo, fid, 'manual_wheel_arrangement', None, w, 'Creator confirms legal in-game arrangement', f['current_run'])
        elif effect not in ['none', 'challenge']:
            _bank(repo, fid, job, s, w, target)
            if effect == 'deferred':
                m = repo.get('moves', f"move:{s['id']}")
                m.update(status='deferred', critical=False)
                repo.put('moves', m)
        f['state'] = State.WHEEL if f['queue'] else f['return_state']
        repo.put('franchises', f)


def retry_impossible_branch(repo, fid, job_id):
    """Only an impossible nested child may be retried, and only once eligible options exist."""
    with repo.transaction():
        f = repo.get('franchises', fid)
        job = current_job(repo, fid)
        original = repo.get('spins', job_id)
        if not job or job['id'] != job_id or not original or original['result']['id'] != 'impossible' or not job.get('parent_spin'):
            raise RuleError('Only an impossible nested branch has retry permission.')
        if not available(repo, fid, job):
            raise RuleError('This branch still has no eligible options. Defer it instead.')
        replacement = dict(job, id=uid(), reroll_reason='Retry of impossible nested branch', retried_spin=job_id)
        f['queue'][0] = replacement
        repo.put('franchises', f)
        return replacement['id']
