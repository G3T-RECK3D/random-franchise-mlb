"""Resolve acquisition rewards using new cards, reserves, or card upgrades."""

from models.domain import State, RuleError, ACTIVE_AREAS, now
from services.franchise_service import audit
from services.roster_service import locked
from services.offseason_service import (
    resolve_move,
    trade_card_errors,
    _change_card,
    is_bench_upgrade,
)


def incoming_card_errors(repo, fid, move, card):
    """Check structured restrictions saved with the acquisition reward."""
    if not isinstance(card, dict):
        return ['Choose or enter an incoming card.']

    outgoing = {
        'kind': move.get('constraints', {}).get(
            'kind', card.get('kind')
        )
    }

    errors = trade_card_errors(repo, fid, move, outgoing, card)
    if is_bench_upgrade(move) and card.get('kind') != 'hitter':
        errors.append('Bench Upgrade can only be used for hitters.')
    return errors


def resolve_banked_move(
    repo,
    fid,
    mid,
    action,
    notes,
    target_id=None,
    new_player=None,
    replace_tag=None,
    confirmed=False,
    cancel_move_id=None,
    max_card_confirmed=False,
    incoming_player_id=None,
    no_lower_card_confirmed=False,
    next_card_confirmed=False,
    upgrade_player_id=None,
):
    # Ordinary moves continue through the existing offseason service.
    if upgrade_player_id is None and incoming_player_id is None:
        return resolve_move(
            repo,
            fid,
            mid,
            action,
            notes,
            target_id,
            new_player,
            replace_tag,
            confirmed,
            cancel_move_id,
            max_card_confirmed=max_card_confirmed,
            no_lower_card_confirmed=no_lower_card_confirmed,
            next_card_confirmed=next_card_confirmed,
        )

    with repo.transaction():
        move = repo.get('moves', mid)

        if not move or move['franchise_id'] != fid:
            raise RuleError('Invalid move.')

        if move['status'] not in ['pending', 'deferred']:
            return

        if move['type'] != 'acquire':
            if upgrade_player_id is not None:
                raise RuleError(
                    'Use card substitution only for an acquisition reward.'
                )

            return resolve_move(
                repo,
                fid,
                mid,
                action,
                notes,
                target_id,
                new_player,
                replace_tag,
                confirmed,
                cancel_move_id,
                max_card_confirmed=max_card_confirmed,
                incoming_player_id=incoming_player_id,
                no_lower_card_confirmed=no_lower_card_confirmed,
                next_card_confirmed=next_card_confirmed,
            )

        if action != 'resolved':
            raise RuleError(
                'Do not select an incoming card when deferring or canceling.'
            )

        if locked(repo, fid):
            raise RuleError('Banked moves resolve after the week ends.')

        franchise = repo.get('franchises', fid)

        if not franchise or franchise['state'] not in [
            State.MOVES,
            State.REBUILD,
            State.VALIDATION,
        ]:
            raise RuleError(
                'Finish MVP and elimination before resolving moves.'
            )

        if (
            not confirmed
            or not isinstance(notes, str)
            or not notes.strip()
        ):
            raise RuleError(
                'Provide resolution notes and confirm the action.'
            )

        if move.get('constraints', {}).get('quantity', 1) != 1:
            raise RuleError(
                'Existing-card options require a one-card reward.'
            )

        if (
            upgrade_player_id is not None
            and incoming_player_id is not None
        ):
            raise RuleError('Choose one acquisition method.')

        before_move = dict(move)
        pid = upgrade_player_id or incoming_player_id
        player = repo.get('players', pid)

        if not player or player['franchise_id'] != fid:
            raise RuleError('Choose a player in this franchise.')

        if upgrade_player_id is not None:
            if player['area'] not in ACTIVE_AREAS:
                raise RuleError(
                    'Choose an active player for a same-player upgrade.'
                )
            if is_bench_upgrade(move) and (
                player['area'] != 'bench' or player['kind'] != 'hitter'
            ):
                raise RuleError(
                    'Bench Upgrade may only upgrade a hitter currently '
                    'assigned to the bench.'
                )

            if not isinstance(new_player, dict):
                raise RuleError('Enter one upgraded card.')

            errors = incoming_card_errors(
                repo, fid, move, new_player
            )

            if errors:
                raise RuleError(' '.join(errors))

            # Existing validation requires the same player/type,
            # a higher OVR, Event eligibility, and a legal assignment.
            # No new player or stat rows are created.
            _change_card(
                repo,
                fid,
                move,
                player,
                new_player,
                notes,
                'up',
            )

            move.update(
                acquisition_method='upgrade_existing',
                upgrade_recipient=pid,
                incoming_player_id=pid,
            )

        else:
            if new_player is not None:
                raise RuleError(
                    'Select a reserve card or enter a new card, not both.'
                )

            if player['area'] != 'minors':
                raise RuleError(
                    'Choose an existing card from Minors.'
                )

            errors = incoming_card_errors(
                repo, fid, move, player
            )

            if errors:
                raise RuleError(' '.join(errors))

            before_card = dict(player)

            player.update(
                historical_only=False,
                last_acquisition_move=mid,
                last_acquisition_at=now(),
            )

            repo.put('players', player)

            audit(
                repo,
                fid,
                'acquire_existing_card',
                before_card,
                dict(player),
                notes,
                move.get('run_id'),
            )

            move.update(
                acquisition_method='existing_minors',
                incoming_player_id=pid,
            )

        move.update(
            status='resolved',
            resolution_notes=notes,
            resolved_at=now(),
        )

        repo.put('moves', move)

        audit(
            repo,
            fid,
            'resolve_move',
            before_move,
            dict(move),
            notes,
            move.get('run_id'),
        )
