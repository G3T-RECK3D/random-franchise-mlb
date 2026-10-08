from models.domain import ACTIVE_AREAS, ValidationResult
from services.franchise_service import settings

def legal_positions(player):
    if player['kind'] == 'pitcher':
        return {player['primary']} | set(player.get('secondary', []))
    return {player['primary'], 'DH'} | set(player.get('secondary', []))

def validate(repo, fid, check_tasks=True):
    cfg = settings(repo, fid)
    active = [p for p in repo.list('players', fid) if p['area'] in ACTIVE_AREAS]
    errors = []
    lineup = [p for p in active if p['area'] == 'lineup']
    required = {'C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'DH'}
    if len(lineup) != 9 or {p['position'] for p in lineup} != required:
        errors.append('Lineup must have one player in each of C, 1B, 2B, 3B, SS, LF, CF, RF, DH.')
    if sorted(p['order'] for p in lineup) != list(range(1, 10)):
        errors.append('Batting order must use 1–9 exactly once.')
    for area, key in [('bench', 'bench_size'), ('rotation', 'rotation_size'), ('bullpen', 'bullpen_size')]:
        if len([p for p in active if p['area'] == area]) != cfg[key]:
            errors.append(f'{area.title()} requires {cfg[key]} players.')
    for area in ['rotation', 'bullpen']:
        orders = [p['order'] for p in active if p['area'] == area]
        if len(orders) != len(set(orders)):
            errors.append(f'{area.title()} orders must be unique.')
    for p in active:
        if p['area'] == 'lineup' and (p['kind'] != 'hitter' or p['position'] not in legal_positions(p)):
            errors.append(f"{p['name']}: illegal lineup assignment.")
        if p['area'] == 'bench' and p['kind'] != 'hitter':
            errors.append(f"{p['name']}: bench requires a hitter.")
        if p['area'] in ['rotation', 'bullpen'] and (p['kind'] != 'pitcher' or p['position'] not in legal_positions(p)):
            errors.append(f"{p['name']}: illegal pitching assignment.")
        if p['area'] == 'rotation' and p['position'] != 'SP':
            errors.append(f"{p['name']}: rotation must be SP.")
        if p['area'] == 'bullpen' and p['position'] != 'RP':
            errors.append(f"{p['name']}: bullpen must be RP.")
        if p.get('eligibility') != 'legal':
            errors.append(f"{p['name']}: Event eligibility is {p.get('eligibility', 'unknown')}.")
        for field in ['team', 'series', 'primary', 'bat', 'throw']:
            value = p.get(field, '')
            allowed, denied = cfg.get(f'allowed_{field}', []), cfg.get(f'disallowed_{field}', [])
            if (allowed and value not in allowed) or value in denied:
                errors.append(f"{p['name']}: {field} does not meet Event restrictions.")
    if cfg.get('ovr_cap') and active and sum(p['ovr'] for p in active) / len(active) > cfg['ovr_cap']:
        errors.append('Average active-roster OVR exceeds the configured cap (manual in-game verification still required).')
    if check_tasks and any(m['status'] == 'pending' and m.get('critical', False) for m in repo.list('moves', fid)):
        errors.append('Resolve critical offseason obligations first.')
    if check_tasks and any(c['status'] == 'awaiting_manual' for c in repo.list('challenges', fid)):
        errors.append('Confirm challenges requiring manual evidence first.')
    return ValidationResult(tuple(errors))
