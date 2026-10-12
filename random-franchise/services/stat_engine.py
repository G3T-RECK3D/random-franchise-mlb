import math

from models.domain import RuleError


HITTER = [
    'games', 'pa', 'ab', 'h', 'doubles', 'triples', 'hr',
    'rbi', 'r', 'bb', 'so', 'sb', 'cs', 'hbp', 'sf',
]
PITCHER = [
    'games', 'starts', 'outs', 'ha', 'r', 'er', 'bb',
    'so', 'hra', 'w', 'l', 'sv', 'holds',
]

# House-rule MVP baseline: 2 earned runs per 3 innings.
PITCHER_BASELINE_ER_PER_THREE_INNINGS = 2.0

COLD_BAT_MIN_PA = 5
COLD_BAT_THRESHOLD = 90.0

# order: (expected OBP, expected SLG, OBP weight, SLG weight)
BATTING_EXPECTATIONS = {
    1: (0.400, 0.500, 0.65, 0.35),
    2: (0.400, 0.600, 0.50, 0.50),
    3: (0.380, 0.650, 0.45, 0.55),
    4: (0.360, 0.700, 0.35, 0.65),
    5: (0.360, 0.700, 0.35, 0.65),
    6: (0.340, 0.550, 0.45, 0.55),
    7: (0.340, 0.550, 0.45, 0.55),
    8: (0.320, 0.450, 0.50, 0.50),
    9: (0.320, 0.450, 0.50, 0.50),
}


def validate_line(kind: str, line: dict) -> dict:
    if kind not in ['hitter', 'pitcher']:
        raise RuleError('Choose a valid player type.')
    if not isinstance(line, dict):
        raise RuleError('Stat line must be a JSON object.')

    keys = HITTER if kind == 'hitter' else PITCHER
    values = {}

    for key in keys:
        value = line.get(key, 0)
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
            or int(value) != value
        ):
            raise RuleError(f'{key} must be a nonnegative integer.')
        values[key] = int(value)

    if values['games'] > 1:
        raise RuleError('One stat line is for at most one game.')

    if kind == 'hitter':
        if (
            values['h'] > values['ab']
            or values['doubles'] + values['triples'] + values['hr']
            > values['h']
        ):
            raise RuleError('Hits and extra-base hits are inconsistent.')

        if (
            values['pa']
            < values['ab'] + values['bb'] + values['hbp'] + values['sf']
            or values['so'] > values['ab']
        ):
            raise RuleError(
                'Plate appearances / strikeouts are inconsistent.'
            )

    elif (
        values['er'] > values['r']
        or values['hra'] > values['ha']
    ):
        raise RuleError(
            'Earned runs / home runs allowed are inconsistent.'
        )

    return values


def mvp_score(kind, totals):
    """Custom estimated run value; not WAR or an official run estimator."""
    if kind == 'hitter':
        hits = totals.get('h', 0)
        doubles = totals.get('doubles', 0)
        triples = totals.get('triples', 0)
        homers = totals.get('hr', 0)
        singles = hits - doubles - triples - homers
        hitless_ab = totals.get('ab', 0) - hits

        return (
            0.5 * singles
            + 0.8 * doubles
            + 1.1 * triples
            + 1.4 * homers
            + 0.3 * (
                totals.get('bb', 0) + totals.get('hbp', 0)
            )
            - 0.25 * (
                hitless_ab + totals.get('sf', 0)
            )
            + 0.2 * totals.get('sb', 0)
            - 0.3 * totals.get('cs', 0)
        )

    if kind == 'pitcher':
        # Nine outs = three innings, so nine outs earn 2 baseline points.
        expected_er = (
            totals.get('outs', 0)
            * PITCHER_BASELINE_ER_PER_THREE_INNINGS
            / 9
        )
        return expected_er - totals.get('er', 0)

    raise RuleError('Choose a valid player type.')


def calculate(kind: str, totals: dict) -> dict:
    result = dict(totals)

    def ratio(numerator, denominator):
        return numerator / denominator if denominator else 0.0

    if kind == 'hitter':
        ab = totals.get('ab', 0)
        hits = totals.get('h', 0)
        bb = totals.get('bb', 0)
        hbp = totals.get('hbp', 0)
        sf = totals.get('sf', 0)

        total_bases = (
            hits
            + totals.get('doubles', 0)
            + 2 * totals.get('triples', 0)
            + 3 * totals.get('hr', 0)
        )
        result.update(
            avg=ratio(hits, ab),
            obp=ratio(hits + bb + hbp, ab + bb + hbp + sf),
            slg=ratio(total_bases, ab),
            tb=total_bases,
        )
        result['ops'] = result['obp'] + result['slg']

    elif kind == 'pitcher':
        outs = totals.get('outs', 0)
        result.update(
            ip=f'{outs // 3}.{outs % 3}',
            era=ratio(totals.get('er', 0) * 27, outs),
            whip=ratio(
                (totals.get('ha', 0) + totals.get('bb', 0)) * 3,
                outs,
            ),
        )
    else:
        raise RuleError('Choose a valid player type.')

    result['mvp_score'] = mvp_score(kind, totals)
    return result


def aggregate(
    repo, franchise_id: str, player: dict,
    run_id=None, game_id=None,
) -> dict:
    keys = HITTER if player['kind'] == 'hitter' else PITCHER
    totals = {key: 0 for key in keys}

    for row in repo.list('stats', franchise_id, run_id):
        if (
            row['player_id'] == player['id']
            and (game_id is None or row['game_id'] == game_id)
        ):
            for key in keys:
                totals[key] += row['line'].get(key, 0)

    return calculate(player['kind'], totals)


def aggregate_season(repo, franchise_id, player, season_id):
    """Combine saved stats from all weeks belonging to one season."""
    season = repo.get('seasons', season_id)
    if not season or season['franchise_id'] != franchise_id:
        raise RuleError('Select a valid season for this franchise.')

    run_ids = {
        run['id']
        for run in repo.list('runs', franchise_id)
        if run.get('season_id') == season_id
    }

    keys = HITTER if player['kind'] == 'hitter' else PITCHER
    totals = {key: 0 for key in keys}

    for row in repo.list('stats', franchise_id):
        if (
            row['player_id'] == player['id']
            and row['run_id'] in run_ids
        ):
            for key in keys:
                totals[key] += row['line'].get(key, 0)

    return calculate(player['kind'], totals)


def _valid_run(repo, fid, run_id):
    run = repo.get('runs', run_id)
    if not run or run['franchise_id'] != fid:
        raise RuleError('Select a valid week for this franchise.')
    return run


def weekly_mvp_candidates(repo, fid, run_id):
    """Combined hitter/pitcher leaderboard from this week's saved stats."""
    run = _valid_run(repo, fid, run_id)
    candidates = []

    for player_id in dict.fromkeys(run.get('roster_ids', [])):
        player = repo.get('players', player_id)
        if not player or player['franchise_id'] != fid:
            continue

        totals = aggregate(repo, fid, player, run_id)
        participated = (
            totals.get('pa', 0) > 0
            if player['kind'] == 'hitter'
            else totals.get('outs', 0) > 0
        )
        if not participated:
            continue

        candidates.append({
            'player_id': player_id,
            'name': player['name'],
            'kind': player['kind'],
            'score': totals['mvp_score'],
            'totals': totals,
        })

    # Equal scores remain ties; name only gives stable display order.
    candidates.sort(
        key=lambda item: (-item['score'], item['name'].casefold())
    )
    return candidates


def _starting_assignments(repo, fid, run_id):
    snapshot = repo.get('snapshots', f'{run_id}:start')
    if (
        not snapshot
        or snapshot.get('franchise_id') != fid
        or snapshot.get('run_id') != run_id
    ):
        return {}

    return {
        player['id']: {
            'area': player.get('area'),
            'order': player.get('order'),
        }
        for player in snapshot.get('players', [])
    }


def _saved_assignment(row, starting_assignments):
    """Prefer game-time metadata; use the start snapshot for older lines."""
    if 'batting_order' in row or 'roster_area' in row:
        return row.get('roster_area'), row.get('batting_order'), 'saved'

    fallback = starting_assignments.get(row['player_id'], {})
    return fallback.get('area'), fallback.get('order'), 'snapshot'


def role_performance(repo, fid, run_id):
    """Compare lineup hitting stats with PA-weighted batting-role targets."""
    _valid_run(repo, fid, run_id)
    starting = _starting_assignments(repo, fid, run_id)
    grouped = {}

    for row in repo.list('stats', fid, run_id):
        player_id = row['player_id']
        player = repo.get('players', player_id)
        if (
            not player
            or player['franchise_id'] != fid
            or player['kind'] != 'hitter'
        ):
            continue

        area, order, source = _saved_assignment(row, starting)
        if (
            area != 'lineup'
            or type(order) is not int
            or order not in BATTING_EXPECTATIONS
        ):
            continue

        line = row['line']
        pa = line.get('pa', 0)
        if pa <= 0:
            continue

        if player_id not in grouped:
            grouped[player_id] = {
                'player': player,
                'totals': {key: 0 for key in HITTER},
                'weighted': [0.0, 0.0, 0.0, 0.0],
                'pa': 0,
                'orders': set(),
                'snapshot_pa': 0,
            }

        item = grouped[player_id]
        for key in HITTER:
            item['totals'][key] += line.get(key, 0)

        for index, value in enumerate(BATTING_EXPECTATIONS[order]):
            item['weighted'][index] += value * pa

        item['pa'] += pa
        item['orders'].add(order)
        if source == 'snapshot':
            item['snapshot_pa'] += pa

    results = []

    for player_id, item in grouped.items():
        pa = item['pa']
        expected_obp, expected_slg, obp_weight, slg_weight = [
            value / pa for value in item['weighted']
        ]
        totals = calculate('hitter', item['totals'])

        role_score = 100 * (
            obp_weight * totals['obp'] / expected_obp
            + slg_weight * totals['slg'] / expected_slg
        )

        enough_pa = pa >= COLD_BAT_MIN_PA
        candidate = enough_pa and role_score < COLD_BAT_THRESHOLD

        if not enough_pa:
            assessment = 'Too few plate appearances'
        elif role_score >= 100:
            assessment = 'Meets or exceeds expectations'
        elif role_score >= COLD_BAT_THRESHOLD:
            assessment = 'Slightly below expectations'
        else:
            assessment = 'Below expectations — Cold Bat candidate'

        results.append({
            'player_id': player_id,
            'name': item['player']['name'],
            'orders': sorted(item['orders']),
            'pa': pa,
            'obp': totals['obp'],
            'slg': totals['slg'],
            'expected_obp': expected_obp,
            'expected_slg': expected_slg,
            'obp_weight': obp_weight,
            'slg_weight': slg_weight,
            'role_score': role_score,
            'candidate': candidate,
            'assessment': assessment,
            'snapshot_pa': item['snapshot_pa'],
            'totals': totals,
        })

    results.sort(
        key=lambda item: (item['role_score'], item['name'].casefold())
    )
    return results


def cold_bat_candidates(repo, fid, run_id):
    """Only qualifying hitters meaningfully below role expectations."""
    return [
        item
        for item in role_performance(repo, fid, run_id)
        if item['candidate']
    ]
