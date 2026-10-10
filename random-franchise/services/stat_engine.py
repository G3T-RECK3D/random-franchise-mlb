from models.domain import RuleError

HITTER = ['games', 'pa', 'ab', 'h', 'doubles', 'triples', 'hr', 'rbi', 'r', 'bb', 'so', 'sb', 'cs', 'hbp', 'sf']
PITCHER = ['games', 'starts', 'outs', 'ha', 'r', 'er', 'bb', 'so', 'hra', 'w', 'l', 'sv', 'holds']

def validate_line(kind: str, line: dict) -> dict:
    keys = HITTER if kind == 'hitter' else PITCHER
    values = {}
    for key in keys:
        value = line.get(key, 0)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 or int(value) != value:
            raise RuleError(f'{key} must be a nonnegative integer.')
        values[key] = int(value)
    if values['games'] > 1:
        raise RuleError('One stat line is for at most one game.')
    if kind == 'hitter':
        if values['h'] > values['ab'] or values['doubles'] + values['triples'] + values['hr'] > values['h']:
            raise RuleError('Hits and extra-base hits are inconsistent.')
        if values['pa'] < values['ab'] + values['bb'] + values['hbp'] + values['sf'] or values['so'] > values['ab']:
            raise RuleError('Plate appearances / strikeouts are inconsistent.')
    elif values['er'] > values['r'] or values['hra'] > values['ha']:
        raise RuleError('Earned runs / home runs allowed are inconsistent.')
    return values

def calculate(kind: str, totals: dict) -> dict:
    result = dict(totals)
    def ratio(numerator, denominator):
        return numerator / denominator if denominator else 0.0
    if kind == 'hitter':
        ab, h = totals.get('ab', 0), totals.get('h', 0)
        bb, hbp, sf = (totals.get(k, 0) for k in ['bb', 'hbp', 'sf'])
        tb = h + totals.get('doubles', 0) + 2 * totals.get('triples', 0) + 3 * totals.get('hr', 0)
        result.update(avg=ratio(h, ab), obp=ratio(h + bb + hbp, ab + bb + hbp + sf), slg=ratio(tb, ab), tb=tb)
        result['ops'] = result['obp'] + result['slg']
    else:
        outs = totals.get('outs', 0)
        result.update(ip=f'{outs // 3}.{outs % 3}', era=ratio(totals.get('er', 0) * 27, outs),
                      whip=ratio((totals.get('ha', 0) + totals.get('bb', 0)) * 3, outs))
    return result

def aggregate(repo, franchise_id: str, player: dict, run_id=None, game_id=None) -> dict:
    keys = HITTER if player['kind'] == 'hitter' else PITCHER
    totals = {key: 0 for key in keys}
    for row in repo.list('stats', franchise_id, run_id):
        if row['player_id'] == player['id'] and (game_id is None or row['game_id'] == game_id):
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
