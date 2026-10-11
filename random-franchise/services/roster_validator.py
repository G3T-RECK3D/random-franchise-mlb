from models.domain import ACTIVE_AREAS, ValidationResult
from services.franchise_service import settings


def legal_positions(player):
    if player['kind'] == 'pitcher':
        return {player['primary']} | set(player.get('secondary', []))
    return {player['primary'], 'DH'} | set(player.get('secondary', []))


def card_event_errors(player, cfg):
    """Check one card against the currently configured Event rules."""
    errors = []
    name = player.get('name', 'Unnamed player')

    if player.get('eligibility') != 'legal':
        errors.append(
            f"{name}: Event eligibility is "
            f"{player.get('eligibility', 'unknown')}."
        )

    for field in ['team', 'series', 'primary', 'bat', 'throw']:
        value = player.get(field, '')
        allowed = cfg.get(f'allowed_{field}', [])
        denied = cfg.get(f'disallowed_{field}', [])

        if (allowed and value not in allowed) or value in denied:
            errors.append(
                f"{name}: {field} does not meet Event restrictions."
            )

    return errors


def card_event_eligible(player, cfg):
    """Used when selecting former cards for Reunion Signing."""
    return not card_event_errors(player, cfg)


def validate(repo, fid, check_tasks=True):
    cfg = settings(repo, fid)
    active = [
        player
        for player in repo.list('players', fid)
        if player['area'] in ACTIVE_AREAS
    ]
    errors = []

    lineup = [
        player for player in active
        if player['area'] == 'lineup'
    ]
    required = {'C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'DH'}

    if (
        len(lineup) != 9
        or {player['position'] for player in lineup} != required
    ):
        errors.append(
            'Lineup must have one player in each of '
            'C, 1B, 2B, 3B, SS, LF, CF, RF, DH.'
        )

    if sorted(player['order'] for player in lineup) != list(range(1, 10)):
        errors.append('Batting order must use 1–9 exactly once.')

    for area, key in [
        ('bench', 'bench_size'),
        ('rotation', 'rotation_size'),
        ('bullpen', 'bullpen_size'),
    ]:
        if len([
            player for player in active
            if player['area'] == area
        ]) != cfg[key]:
            errors.append(
                f'{area.title()} requires {cfg[key]} players.'
            )

    for area in ['rotation', 'bullpen']:
        orders = [
            player['order']
            for player in active
            if player['area'] == area
        ]
        if len(orders) != len(set(orders)):
            errors.append(f'{area.title()} orders must be unique.')

    for player in active:
        if player['area'] == 'lineup' and (
            player['kind'] != 'hitter'
            or player['position'] not in legal_positions(player)
        ):
            errors.append(
                f"{player['name']}: illegal lineup assignment."
            )

        if player['area'] == 'bench' and player['kind'] != 'hitter':
            errors.append(
                f"{player['name']}: bench requires a hitter."
            )

        if player['area'] in ['rotation', 'bullpen'] and (
            player['kind'] != 'pitcher'
            or player['position'] not in legal_positions(player)
        ):
            errors.append(
                f"{player['name']}: illegal pitching assignment."
            )

        if (
            player['area'] == 'rotation'
            and player['position'] != 'SP'
        ):
            errors.append(
                f"{player['name']}: rotation must be SP."
            )

        if (
            player['area'] == 'bullpen'
            and player['position'] != 'RP'
        ):
            errors.append(
                f"{player['name']}: bullpen must be RP."
            )

        errors.extend(card_event_errors(player, cfg))

    if (
        cfg.get('ovr_cap')
        and active
        and sum(player['ovr'] for player in active) / len(active)
        > cfg['ovr_cap']
    ):
        errors.append(
            'Average active-roster OVR exceeds the configured cap '
            '(manual in-game verification still required).'
        )

    if check_tasks and any(
        move['status'] == 'pending'
        and move.get('critical', False)
        for move in repo.list('moves', fid)
    ):
        errors.append('Resolve critical offseason obligations first.')

    if check_tasks and any(
        challenge['status'] == 'awaiting_manual'
        for challenge in repo.list('challenges', fid)
    ):
        errors.append('Confirm challenges requiring manual evidence first.')

    return ValidationResult(tuple(errors))
