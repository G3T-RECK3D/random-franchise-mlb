"""Restore historical weeks without replaying game rewards."""

import hashlib
import json
from datetime import date

from models.domain import RuleError, uid, now
from services.franchise_service import audit, settings
from services.roster_service import add_player, locked
from services.stat_engine import HITTER, PITCHER, validate_line


def import_completed_week(repo, fid, season_id, payload):
    with repo.transaction():
        franchise = repo.get('franchises', fid)
        season = repo.get('seasons', season_id)

        if (
            not franchise
            or not season
            or season['franchise_id'] != fid
        ):
            raise RuleError('Select a valid franchise and season.')

        if not isinstance(payload, dict):
            raise RuleError('Historical import must be a JSON object.')

        week_number = payload.get('week_number')
        if type(week_number) is not int or week_number < 1:
            raise RuleError('Week number must be a positive integer.')

        ended_reason = payload.get('ended_reason', 'loss_limit')
        if ended_reason not in ['loss_limit', 'event_ended']:
            raise RuleError(
                'Week ending reason must be loss_limit or event_ended.'
            )

        fingerprint = hashlib.sha256(
            json.dumps(
                payload,
                sort_keys=True,
                allow_nan=False,
            ).encode('utf-8')
        ).hexdigest()

        runs = repo.list('runs', fid)
        existing = [
            run for run in runs
            if run.get('season_id') == season_id
            and run.get('week_number') == week_number
        ]

        if existing:
            if (
                len(existing) == 1
                and existing[0].get('import_fingerprint') == fingerprint
            ):
                return existing[0]['id']

            raise RuleError(
                'This season already contains that week. '
                'A different import cannot overwrite it.'
            )

        if locked(repo, fid):
            raise RuleError(
                'Restore historical weeks before starting an active week.'
            )

        cards = payload.get('players')
        games = payload.get('games')

        if not isinstance(cards, list) or not cards:
            raise RuleError('Include the historical player cards.')

        if not isinstance(games, list) or not games:
            raise RuleError('Include the historical games.')

        card_map = {}
        current_players = repo.list('players', fid)

        for card in cards:
            if not isinstance(card, dict):
                raise RuleError('Each card must be a JSON object.')

            card_key = card.get('key')
            card_uuid = card.get('card_uuid')

            if (
                not isinstance(card_key, str)
                or not card_key
                or card_key in card_map
                or not isinstance(card_uuid, str)
                or not card_uuid
            ):
                raise RuleError(
                    'Cards need distinct keys and a verified card UUID.'
                )

            # Match both card identity and stat role.
            # This permits separate hitting/pitching entries for Ohtani.
            matches = [
                player for player in current_players
                if player.get('card_uuid') == card_uuid
                and player.get('kind') == card.get('kind')
            ]

            if len(matches) > 1:
                raise RuleError(
                    'Multiple existing entries match this card and role: '
                    + card.get('name', card_key)
                )

            if matches:
                player = matches[0]

                if player['name'] != card.get('name'):
                    raise RuleError('Existing card identity does not match.')
            else:
                data = {
                    key: value
                    for key, value in card.items()
                    if key != 'key'
                }

                data.update(
                    area='minors',
                    position=data.get('primary', 'C'),
                    eligibility='unknown',
                    protected=False,
                    hot_seat=False,
                    historical_only=True,
                    notes=(
                        'Recovered historical card; '
                        'not added to active roster.'
                    ),
                )

                pid = add_player(repo, fid, data)
                player = repo.get('players', pid)
                current_players.append(player)

            card_map[card_key] = player

        rid = uid()
        wins = 0
        losses = 0
        dates = []
        used_ids = set()

        for number, item in enumerate(games, 1):
            if not isinstance(item, dict):
                raise RuleError('Each game must be a JSON object.')

            if losses >= 2:
                raise RuleError(
                    'A historical week cannot continue after two losses.'
                )

            result = item.get('result')
            if result not in ['W', 'L']:
                raise RuleError('Every game needs a W or L result.')

            played = item.get('date')

            try:
                date.fromisoformat(played)
            except (TypeError, ValueError):
                raise RuleError(
                    'Every game needs a date in YYYY-MM-DD format.'
                )

            if dates and played < dates[-1]:
                raise RuleError(
                    'List historical games in chronological order.'
                )

            dates.append(played)

            own = item.get('team_score')
            opponent_score = item.get('opponent_score')

            if type(own) is not int or type(opponent_score) is not int:
                raise RuleError('Enter integer scores for both teams.')

            # Permit a reported 0–0 result only when its box score
            # is explicitly unavailable.
            score_unavailable = (
                item.get('stats_unavailable') is True
                and own == 0
                and opponent_score == 0
            )

            if (
                min(own, opponent_score) < 0
                or (
                    not score_unavailable
                    and (
                        own == opponent_score
                        or (own > opponent_score) != (result == 'W')
                    )
                )
            ):
                raise RuleError(
                    'Historical scores must agree with the result.'
                )

            gid = uid()
            lines = item.get('lines')

            if not isinstance(lines, list):
                raise RuleError('Game stat lines must be a list.')

            if not lines and item.get('stats_unavailable') is not True:
                raise RuleError(
                    'Include stat lines or mark the box score as unavailable.'
                )

            if lines and score_unavailable:
                raise RuleError(
                    'A reported 0–0 game with an unavailable box score '
                    'must not include player stat lines.'
                )

            seen = set()

            for row in lines:
                if not isinstance(row, dict):
                    raise RuleError('Each stat entry must be a JSON object.')

                player = card_map.get(row.get('player_key'))

                if not player or player['id'] in seen:
                    raise RuleError(
                        'Use distinct players from the imported cards.'
                    )

                seen.add(player['id'])
                used_ids.add(player['id'])

                supplied = row.get('line')

                if not isinstance(supplied, dict):
                    raise RuleError('Each player needs a stat-line object.')

                keys = HITTER if player['kind'] == 'hitter' else PITCHER

                if set(supplied) - set(keys):
                    raise RuleError('Stat line contains an unknown field.')

                if supplied.get('games') != 1:
                    raise RuleError(
                        'Each participant must have games set to 1.'
                    )

                missing = [key for key in keys if key not in supplied]
                normalized = validate_line(player['kind'], supplied)

                repo.put('stats', dict(
                    id=f"{gid}:{player['id']}",
                    franchise_id=fid,
                    run_id=rid,
                    player_id=player['id'],
                    game_id=gid,
                    line=normalized,
                    flags={},
                    recovered=True,
                    unavailable_fields=missing,
                ))

            repo.put('games', dict(
                id=gid,
                franchise_id=fid,
                run_id=rid,
                number=number,
                result=result,
                opponent=item.get('opponent', ''),
                team_score=own,
                opponent_score=opponent_score,
                date=played,
                notes=item.get('notes', ''),
                created_at=now(),
                recovered=True,
                stats_unavailable=item.get('stats_unavailable') is True,
                score_unavailable=score_unavailable,
                date_inferred=item.get('date_inferred') is True,
            ))

            wins += result == 'W'
            losses += result == 'L'

        if losses != 2 and ended_reason != 'event_ended':
            raise RuleError(
                'A historical week must contain two losses '
                'or be marked as ended when the Event closed.'
            )

        run = dict(
            id=rid,
            franchise_id=fid,
            number=max(
                (run['number'] for run in runs),
                default=0,
            ) + 1,
            season_id=season_id,
            week_number=week_number,
            event=season['event'],
            wins=wins,
            losses=losses,
            max_losses=2,
            settings=settings(repo, fid),
            roster_ids=sorted(used_ids),
            started_at=dates[0],
            ended_at=dates[-1],
            ended_reason=ended_reason,
            mvp=None,
            offseason_step='historical_complete',
            recovered=True,
            import_fingerprint=fingerprint,
        )

        repo.put('runs', run)

        audit(
            repo,
            fid,
            'import_historical_week',
            None,
            run,
            'Restore historical games without replaying wheels or rewards.',
            rid,
        )

        return rid


def move_historical_week(repo, fid, run_id, destination_season_id):
    """Move an imported historical week without changing games or stats."""
    with repo.transaction():
        franchise = repo.get('franchises', fid)
        run = repo.get('runs', run_id)
        destination = repo.get('seasons', destination_season_id)

        if (
            not franchise
            or not run
            or run['franchise_id'] != fid
            or not destination
            or destination['franchise_id'] != fid
        ):
            raise RuleError(
                'Select a valid historical week and destination season.'
            )

        if (
            not run.get('recovered')
            or run.get('offseason_step') != 'historical_complete'
            or not run.get('ended_at')
            or franchise.get('current_run') == run_id
        ):
            raise RuleError(
                'Only completed historical imports can be moved.'
            )

        if run.get('season_id') == destination_season_id:
            raise RuleError('This week already belongs to that season.')

        week_number = run.get('week_number', run['number'])

        if any(
            other['id'] != run_id
            and other.get('season_id') == destination_season_id
            and other.get('week_number', other['number']) == week_number
            for other in repo.list('runs', fid)
        ):
            raise RuleError(
                'The destination season already contains that week number.'
            )

        before = dict(run)

        run.update(
            season_id=destination_season_id,
            event=destination['event'],
        )

        repo.put('runs', run)

        audit(
            repo,
            fid,
            'move_historical_week',
            before,
            run,
            'Correct the season assigned to an imported historical week.',
            run_id,
        )

        return run_id
