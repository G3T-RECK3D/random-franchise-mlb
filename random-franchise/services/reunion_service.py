"""Find former cards eligible for a Reunion Signing reward."""

from models.domain import ACTIVE_AREAS
from services.franchise_service import settings
from services.roster_validator import card_event_eligible


def reunion_pool(repo, fid):
    franchise = repo.get('franchises', fid)
    if not franchise:
        return []

    current_season_id = franchise.get('current_season')
    current_season = (
        repo.get('seasons', current_season_id)
        if current_season_id else None
    )
    if (
        not current_season
        or current_season.get('franchise_id') != fid
    ):
        return []

    current_number = current_season['number']

    previous_season_ids = {
        season['id']
        for season in repo.list('seasons', fid)
        if season['number'] < current_number
    }

    previous_run_ids = {
        run['id']
        for run in repo.list('runs', fid)
        if run.get('season_id') in previous_season_ids
    }

    former_player_ids = {
        stat['player_id']
        for stat in repo.list('stats', fid)
        if stat.get('run_id') in previous_run_ids
        and stat.get('line', {}).get('games', 0) > 0
    }

    reserved_player_ids = {
        move.get('target')
        for move in repo.list('moves', fid)
        if move.get('type') == 'reunion'
        and move.get('status') in ['pending', 'deferred']
    }

    # A persisted spin reserves its card before Continue is clicked.
    for job in franchise.get('queue', []):
        saved_spin = repo.get('spins', job['id'])
        if (
            saved_spin
            and saved_spin.get('franchise_id') == fid
            and saved_spin.get('result', {}).get('effect') == 'reunion'
        ):
            reserved_player_ids.add(saved_spin.get('target'))

    cfg = settings(repo, fid)

    return [
        player
        for player in repo.list('players', fid)
        if player['id'] in former_player_ids
        and player['id'] not in reserved_player_ids
        and player['area'] not in ACTIVE_AREAS
        and player.get('kind') in ['hitter', 'pitcher']
        and card_event_eligible(player, cfg)
    ]
