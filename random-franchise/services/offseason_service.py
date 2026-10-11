from models.domain import State, RuleError, now, ACTIVE_AREAS, POSITIONS
from services.game_engine import enqueue, snapshot
from services.roster_service import (
    locked,
    remove_player,
    add_player,
    arrange,
    protected,
    target_pool,
)
from services.franchise_tag_service import grant
from services.franchise_service import audit, settings
from services.roster_validator import (
    validate,
    legal_positions,
    card_event_errors,
)


def confirm_end(repo, fid):
    with repo.transaction():
        f = repo.get('franchises', fid)
        if not f or f['state'] != State.ENDED:
            raise RuleError('No ended week to confirm.')

        run = repo.get('runs', f.get('current_run'))
        if not run or run['franchise_id'] != fid:
            raise RuleError('The ended week could not be found.')

        run['offseason_step'] = 'mvp'
        f['state'] = State.MVP

        repo.put('runs', run)
        repo.put('franchises', f)


def select_mvp(repo, fid, pid):
    with repo.transaction():
        f = repo.get('franchises', fid)
        if not f or f['state'] != State.MVP:
            raise RuleError('Confirm the ended week before choosing MVP.')

        run = repo.get('runs', f.get('current_run'))
        if not run or pid not in run['roster_ids']:
            raise RuleError('Select a player from the ended week.')

        player = repo.get('players', pid)
        if not player or player['franchise_id'] != fid:
            raise RuleError('The selected player is unavailable.')

        run.update(mvp=pid, offseason_step='elimination')
        player['protected'] = True

        repo.put('players', player)
        repo.put('runs', run)

        enqueue(f, 'mvp', 'run_mvp', target=pid)
        f.update(state=State.WHEEL, return_state=State.ELIMINATION)
        repo.put('franchises', f)


def progress(repo, fid):
    with repo.transaction():
        f = repo.get('franchises', fid)
        if not f:
            raise RuleError('Franchise not found.')

        run = repo.get('runs', f.get('current_run'))
        if not run:
            raise RuleError('No current week was found.')

        if f['state'] == State.ELIMINATION:
            enqueue(f, 'elimination', 'run_end')
            f.update(state=State.WHEEL, return_state=State.MELTDOWN)
            run['offseason_step'] = 'meltdown'

        elif f['state'] == State.MELTDOWN:
            mode = run['settings']['meltdown']

            if run['wins'] == 0 and run['losses'] == 2 and mode != 'none':
                enqueue(
                    f,
                    'meltdown' if mode == 'wheel' else 'elimination',
                    '0–2 meltdown',
                )
                f.update(state=State.WHEEL, return_state=State.MOVES)
            else:
                f['state'] = State.MOVES

            run['offseason_step'] = 'moves'

        elif f['state'] == State.MOVES:
            if any(
                move['status'] == 'pending' and move.get('critical')
                for move in repo.list('moves', fid)
            ):
                raise RuleError(
                    'Resolve all critical obligations before reconstruction.'
                )

            if any(
                challenge['status'] == 'awaiting_manual'
                for challenge in repo.list('challenges', fid)
            ):
                raise RuleError('Confirm manual challenge evidence first.')

            f['state'] = State.REBUILD
            run['offseason_step'] = 'rebuild'

        elif f['state'] == State.REBUILD:
            f['state'] = State.VALIDATION

        else:
            raise RuleError('Complete the current action first.')

        repo.put('runs', run)
        repo.put('franchises', f)


def _resolve_reunion(repo, fid, move, target_id, new_player, notes):
    """Restore the former card selected by the audited wheel spin."""
    pid = move.get('target')
    if not pid or (target_id is not None and target_id != pid):
        raise RuleError(
            'Reunion Signing must use the former card selected by the wheel.'
        )

    if new_player is not None:
        raise RuleError(
            'Reunion Signing uses an existing card. '
            'Do not submit incoming card JSON.'
        )

    spin_id = move.get('spin_id')
    saved_spin = repo.get('spins', spin_id) if spin_id else None
    if (
        not saved_spin
        or saved_spin['franchise_id'] != fid
        or saved_spin.get('target') != pid
        or saved_spin.get('result', {}).get('effect') != 'reunion'
    ):
        raise RuleError('This reunion reward has no matching audited spin.')

    player = repo.get('players', pid)
    if not player or player['franchise_id'] != fid:
        raise RuleError('The selected former card is unavailable.')

    rules = move.get('constraints', {})
    for field in ['kind', 'ovr', 'version', 'series', 'card_uuid']:
        if field in rules and player.get(field) != rules[field]:
            raise RuleError(
                'The selected card details changed after the spin. '
                'Restore the original card details or defer this reward.'
            )

    errors = card_event_errors(player, settings(repo, fid))
    if errors:
        raise RuleError(
            'The reunion card must meet the current Event rules. '
            + ' '.join(errors)
        )

    before_card = dict(player)

    if player['area'] not in ACTIVE_AREAS:
        player.update(
            area='minors',
            position=player['primary'],
            order=max(1, player.get('order', 1)),
        )

    player['historical_only'] = False
    player['last_reunion_at'] = now()
    player['last_reunion_move'] = move['id']
    repo.put('players', player)

    move['reunion_player_id'] = pid

    audit(
        repo,
        fid,
        'reunion_card_return',
        before_card,
        dict(player),
        notes,
        move.get('run_id'),
    )


def resolve_move(
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
):
    with repo.transaction():
        move = repo.get('moves', mid)
        if not move or move['franchise_id'] != fid:
            raise RuleError('Invalid move.')

        if move['status'] not in ['pending', 'deferred']:
            return

        if locked(repo, fid):
            raise RuleError(
                'Banked moves can only resolve after the week ends.'
            )

        f = repo.get('franchises', fid)
        if f['state'] not in [
            State.MOVES, State.REBUILD, State.VALIDATION,
        ]:
            raise RuleError(
                'Finish MVP and elimination before resolving moves.'
            )

        if not isinstance(notes, str) or not notes.strip() or not confirmed:
            raise RuleError(
                'Provide resolution notes and confirm the action.'
            )

        before = dict(move)

        if action in ['deferred', 'canceled']:
            if move.get('critical') and move['type'] != 'tag':
                raise RuleError(
                    'Critical consequences must be applied; '
                    'they cannot be skipped.'
                )
            move.update(status=action, critical=False)

        elif action == 'resolved':
            pid = target_id or move.get('target')

            if (
                move['type'] in ['dfa', 'demote', 'trade']
                and move.get('target')
                and pid != move['target']
            ):
                original = repo.get('players', move['target'])
                if (
                    original
                    and original['area'] in ACTIVE_AREAS
                    and not protected(repo, fid, original)
                ):
                    raise RuleError(
                        'Use the audited wheel target; retargeting is '
                        'allowed only if it becomes ineligible.'
                    )

            quantity = move.get('constraints', {}).get('quantity', 1)

            if move['type'] in ['cancel_elimination', 'save_dfa']:
                other = (
                    repo.get('moves', cancel_move_id)
                    if cancel_move_id else None
                )
                allowed = (
                    ['dfa']
                    if move['type'] == 'save_dfa'
                    else ['dfa', 'demote', 'trade']
                )

                if (
                    not other
                    or other['franchise_id'] != fid
                    or other['run_id'] != move['run_id']
                    or other['status'] != 'pending'
                    or other['type'] not in allowed
                ):
                    raise RuleError(
                        'Select an eligible pending consequence from this week.'
                    )

                other_before = dict(other)
                other.update(
                    status='canceled',
                    critical=False,
                    resolved_at=now(),
                    resolution_notes=(
                        'Canceled by reward ' + mid + ': ' + notes
                    ),
                )
                repo.put('moves', other)
                audit(
                    repo, fid, 'awarded_cancellation',
                    other_before, other, notes, move['run_id'],
                )

            elif move['type'] == 'reunion':
                _resolve_reunion(
                    repo, fid, move, target_id, new_player, notes,
                )

            elif move['type'] == 'call_up':
                player = repo.get('players', pid) if pid else None
                if (
                    not player
                    or player['franchise_id'] != fid
                    or player['area'] != 'minors'
                ):
                    raise RuleError(
                        'Choose an existing minor-league player.'
                    )

                area = (
                    'bench' if player['kind'] == 'hitter'
                    else 'rotation' if player['primary'] == 'SP'
                    else 'bullpen'
                )
                position = (
                    player['primary']
                    if player['kind'] == 'hitter'
                    else 'SP' if area == 'rotation'
                    else 'RP'
                )

                arrange(
                    repo, fid, pid, area, position, player['order'],
                )

            elif move['type'] in ['dfa', 'demote', 'trade']:
                pool = target_pool(repo, fid)

                if not pid or pid not in {p['id'] for p in pool}:
                    if not pool:
                        move.update(
                            status='invalid',
                            critical=False,
                            resolution_notes=(
                                'No eligible unprotected target: ' + notes
                            ),
                        )
                        repo.put('moves', move)
                        audit(
                            repo, fid, 'impossible_move',
                            before, move, notes,
                        )
                        return

                    raise RuleError(
                        'Choose an eligible, unprotected active player.'
                    )

                targets = [pid] + [
                    player['id'] for player in pool
                    if player['id'] != pid
                ][:quantity - 1]

                if len(targets) < quantity:
                    raise RuleError(
                        'Not enough eligible players for the required quantity.'
                    )

                if move['type'] == 'trade':
                    if not isinstance(new_player, dict):
                        raise RuleError('Enter one incoming trade card.')

                    outgoing = repo.get('players', pid)
                    rules = move.get('constraints', {})
                    required_kind = rules.get('kind', outgoing['kind'])

                    if (
                        outgoing['kind'] != required_kind
                        or new_player.get('kind') != required_kind
                    ):
                        raise RuleError(
                            'Trade hitters for hitters and pitchers for pitchers.'
                        )

                    if new_player.get('eligibility') != 'legal':
                        raise RuleError(
                            'The incoming card must be Event-legal.'
                        )

                    allowed_teams = rules.get('teams', [])
                    incoming_team = str(
                        new_player.get('team', '')
                    ).strip()

                    if (
                        allowed_teams
                        and incoming_team.casefold() not in {
                            team.casefold() for team in allowed_teams
                        }
                    ):
                        raise RuleError(
                            'Incoming team must match the market spin. '
                            'Allowed teams: ' + ', '.join(allowed_teams)
                        )

                    allowed_positions = rules.get('positions', [])
                    if (
                        allowed_positions
                        and new_player.get('primary')
                        not in allowed_positions
                    ):
                        raise RuleError(
                            'Incoming primary position must match the '
                            'position spin: ' + ', '.join(allowed_positions)
                        )

                    max_ovr = rules.get('max_ovr')
                    if max_ovr is not None:
                        incoming_ovr = new_player.get('ovr')
                        if (
                            type(incoming_ovr) is not int
                            or not 0 <= incoming_ovr <= max_ovr
                        ):
                            raise RuleError(
                                f'Incoming OVR must be {max_ovr} or lower.'
                            )

                for target in targets:
                    remove_player(
                        repo,
                        fid,
                        target,
                        'minors' if move['type'] == 'demote' else 'dfa',
                    )

                if move['type'] == 'trade':
                    add_player(repo, fid, new_player)

            elif move['type'] == 'tag':
                if (
                    not pid
                    or grant(
                        repo,
                        fid,
                        pid,
                        replace_tag,
                        source=move['description'],
                    ) == 'cap_decision_required'
                ):
                    raise RuleError(
                        'Choose a tag holder to replace, '
                        'or decline this new tag.'
                    )

            elif move['type'] == 'protect':
                player = repo.get('players', pid) if pid else None
                if not player or player['franchise_id'] != fid:
                    raise RuleError('Select a protection target.')

                player['protected'] = True
                if 'Next Run' in move['description']:
                    player['protection_until_run'] = (
                        repo.get('runs', f['current_run'])['number'] + 1
                    )
                repo.put('players', player)

            elif move['type'] == 'extra_spin':
                enqueue(f, 'front_office', move['id'])
                f.update(state=State.WHEEL, return_state=State.MOVES)
                repo.put('franchises', f)

            elif move['type'] == 'upgrade':
                earned_by = (
                    repo.get('players', move['target'])
                    if move.get('target') else None
                )
                if not earned_by or earned_by['franchise_id'] != fid:
                    raise RuleError(
                        'The player who earned this reward is unavailable.'
                    )

                recipient_id = target_id or earned_by['id']
                if recipient_id != earned_by['id']:
                    if move.get('source') != 'development':
                        raise RuleError(
                            'This upgrade cannot transfer to a teammate.'
                        )
                    if max_card_confirmed is not True:
                        raise RuleError(
                            'Confirm that the original player has no higher '
                            'Event-eligible card before choosing a teammate.'
                        )
                    move['upgrade_earned_by'] = earned_by['id']

                move['upgrade_recipient'] = recipient_id
                player = repo.get('players', recipient_id)
                if not player or player['franchise_id'] != fid:
                    raise RuleError('The upgrade player is unavailable.')

                if player['area'] not in ACTIVE_AREAS:
                    raise RuleError(
                        'The player must be on the active roster. '
                        'Defer the upgrade if they have been removed.'
                    )

                if not isinstance(new_player, dict):
                    raise RuleError(
                        'Enter one upgraded card as a JSON object.'
                    )

                if (
                    new_player.get('name', '').strip().casefold()
                    != player['name'].strip().casefold()
                ):
                    raise RuleError('The upgrade must be the same player.')

                if new_player.get('kind') != player['kind']:
                    raise RuleError(
                        'The upgraded card must have the same player type.'
                    )

                ovr = new_player.get('ovr')
                if (
                    type(ovr) is not int
                    or not player['ovr'] < ovr <= 99
                ):
                    raise RuleError(
                        'The upgraded OVR must be higher, up to 99.'
                    )

                if not str(new_player.get('version', '')).strip():
                    raise RuleError('Enter the upgraded card version.')

                if new_player.get('eligibility') != 'legal':
                    raise RuleError(
                        'Confirm that the upgraded card is Event-legal.'
                    )

                primary = new_player.get('primary')
                secondary = new_player.get('secondary', [])
                if (
                    primary not in POSITIONS
                    or not isinstance(secondary, list)
                    or any(pos not in POSITIONS for pos in secondary)
                ):
                    raise RuleError(
                        'Enter valid primary and secondary positions.'
                    )

                before_card = dict(player)
                upgraded = dict(player)

                for field in [
                    'version', 'ovr', 'primary', 'secondary',
                    'team', 'series', 'bat', 'throw', 'eligibility',
                ]:
                    if field in new_player:
                        upgraded[field] = new_player[field]

                if upgraded['position'] not in legal_positions(upgraded):
                    raise RuleError(
                        'The upgraded card cannot play the current assigned '
                        'position. Arrange the player legally first.'
                    )

                repo.put('players', upgraded)
                audit(
                    repo,
                    fid,
                    'development_card_upgrade',
                    before_card,
                    upgraded,
                    notes,
                    move['run_id'],
                )

            elif move['type'] == 'acquire':
                incoming = (
                    new_player if isinstance(new_player, list)
                    else [new_player] if new_player else []
                )
                if len(incoming) != quantity:
                    raise RuleError(
                        f'Provide {quantity} incoming card(s).'
                    )

                for card in incoming:
                    add_player(repo, fid, card)

            # Review/choice rewards are acknowledged with resolution notes.
            move['status'] = 'resolved'

        else:
            raise RuleError('Unknown resolution action.')

        move.update(resolution_notes=notes, resolved_at=now())
        repo.put('moves', move)

        audit(
            repo,
            fid,
            'resolve_move',
            before,
            move,
            notes,
            move.get('run_id'),
        )


def finish_validation(repo, fid):
    with repo.transaction():
        f = repo.get('franchises', fid)
        if not f or f['state'] != State.VALIDATION:
            raise RuleError('Proceed to roster validation first.')

        result = validate(repo, fid)
        if not result.valid:
            raise RuleError('\n'.join(result.errors))

        run = repo.get('runs', f.get('current_run'))
        if not run:
            raise RuleError('No current week was found.')

        snapshot(repo, fid, run['id'], 'rebuilt')
        current_number = run['number']

        for player in repo.list('players', fid):
            player.update(
                protected=bool(
                    player.get('protection_until_run', 0)
                    > current_number
                ),
                hot_seat=False,
            )
            repo.put('players', player)

        f['state'] = State.READY
        repo.put('franchises', f)
