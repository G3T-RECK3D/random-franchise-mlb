from models.domain import State, RuleError, now, ACTIVE_AREAS, POSITIONS
from services.game_engine import enqueue, snapshot
from services.roster_service import (
    locked, remove_player, add_player, arrange, protected, target_pool,
)
from services.franchise_tag_service import grant
from services.franchise_service import audit, settings
from services.roster_validator import (
    validate, legal_positions, card_event_errors,
)
from services.stat_engine import cold_bat_candidates



def trade_policy(repo, move):
    """Classify a saved trade using the original, audited wheel outcome.

    Older trade rewards were mistakenly stored as critical=True. Do not
    modify their audited spins or rely solely on that legacy flag.
    """
    if move.get('type') != 'trade':
        return {
            'required': bool(move.get('critical')),
            'choose_outgoing': False,
        }

    constraints = move.get('constraints') or {}
    spin_id = move.get('spin_id')
    original_spin = repo.get('spins', spin_id) if spin_id else None
    if original_spin:
        title = original_spin.get('result', {}).get('text', '')
        original_wheel = original_spin.get('wheel_id') or original_spin.get(
            'job', {}
        ).get('wheel_id')
    else:
        title = move.get('description', '').split(' · ', 1)[0]
        original_wheel = None

    title = title.strip().casefold()

    # Elimination/meltdown consequences are always mandatory, even when a
    # future custom wheel happens to reuse a reward's display label.
    if original_wheel in ('elimination', 'meltdown'):
        return {'required': True, 'choose_outgoing': False}

    if title in ('trade opportunity', 'free trade'):
        return {
            'required': False,
            'choose_outgoing': title == 'free trade',
        }

    # New banked records explicitly preserve these details in constraints.
    if constraints.get('optional_trade') is True:
        return {
            'required': False,
            'choose_outgoing': bool(constraints.get('choose_outgoing')),
        }

    return {
        'required': bool(move.get('critical')),
        'choose_outgoing': False,
    }


def move_required(repo, move):
    """Return the effective required status, including legacy trade rewards."""
    if move.get('type') == 'trade':
        return trade_policy(repo, move)['required']
    return bool(move.get('critical'))


def is_bench_upgrade(move):
    """Recognize bench-only acquisitions, including already-banked rewards.

    Older saves have no reward_area marker; identify them by saved wheel name.
    """
    if move.get('type') != 'acquire':
        return False
    if move.get('constraints', {}).get('reward_area') == 'bench':
        return True
    return str(move.get('description', '')).strip().casefold() == 'bench upgrade'


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


def cold_bat_enabled(repo, fid):
    return repo.get('wheels', f'{fid}:cold_bat') is not None


def eligible_cold_bat_candidates(repo, fid, run_id):
    """Exclude players already removed or protected during offseason."""
    candidates = []
    for item in cold_bat_candidates(repo, fid, run_id):
        player = repo.get('players', item['player_id'])
        if (
            player
            and player['franchise_id'] == fid
            and player['kind'] == 'hitter'
            and player['area'] in ['lineup', 'bench']
            and not protected(repo, fid, player)
        ):
            candidates.append(item)
    return candidates


def decide_cold_bat(
    repo, fid, run_id, player_id=None,
    skip=False, reason='', confirmed=False,
):
    """Save one Cold Bat decision and queue at most one wheel per week."""
    with repo.transaction():
        f = repo.get('franchises', fid)
        run = repo.get('runs', run_id)

        if (
            not f
            or not run
            or run['franchise_id'] != fid
            or f.get('current_run') != run_id
            or not run.get('ended_at')
        ):
            raise RuleError('Select the current completed week.')

        # Repeated submission is harmless.
        if run.get('cold_bat_decision'):
            return run['cold_bat_decision']

        if f['state'] != State.MOVES or f.get('queue'):
            raise RuleError(
                'Finish required offseason wheels before reviewing Cold Bat.'
            )
        if not cold_bat_enabled(repo, fid):
            raise RuleError('The Cold Bat wheel has not been installed.')
        if not confirmed or not isinstance(reason, str) or not reason.strip():
            raise RuleError('Confirm the decision and enter a short reason.')

        candidates = eligible_cold_bat_candidates(repo, fid, run_id)
        by_id = {item['player_id']: item for item in candidates}

        if not skip and player_id not in by_id:
            raise RuleError(
                'Choose a qualifying, unprotected Cold Bat candidate '
                'or select the skip option.'
            )

        before = dict(run)
        decision = {
            'status': 'skipped' if skip else 'queued',
            'player_id': None if skip else player_id,
            'reason': reason.strip(),
            'decided_at': now(),
            'candidates': candidates,
        }

        if not skip:
            source = f'cold_bat:{run_id}'
            already_queued = any(
                job.get('source') == source for job in f['queue']
            )
            already_spun = any(
                spin.get('job', {}).get('source') == source
                for spin in repo.list('spins', fid, run_id)
            )
            if already_queued or already_spun:
                raise RuleError('This week already has a Cold Bat spin.')

            enqueue(f, 'cold_bat', source, target=player_id)
            decision['job_id'] = f['queue'][-1]['id']
            f.update(state=State.WHEEL, return_state=State.MOVES)

        run['cold_bat_decision'] = decision
        repo.put('runs', run)
        repo.put('franchises', f)
        audit(
            repo, fid, 'cold_bat_decision',
            before, dict(run), reason.strip(), run_id,
        )
        return decision


def _require_cold_bat_review(repo, fid, run):
    if (
        cold_bat_enabled(repo, fid)
        and not run.get('cold_bat_decision')
    ):
        raise RuleError(
            'Review Cold Bat candidates and confirm either '
            'a target or the skip option first.'
        )


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
            _require_cold_bat_review(repo, fid, run)
            if any(
                m['status'] == 'pending' and move_required(repo, m)
                for m in repo.list('moves', fid)
            ):
                raise RuleError(
                    'Resolve all critical obligations before reconstruction.'
                )
            if any(
                c['status'] == 'awaiting_manual'
                for c in repo.list('challenges', fid)
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


def _team_key(value):
    text = str(value).strip().casefold()
    teams = {
        'orioles': 'Baltimore Orioles',
        'red sox': 'Boston Red Sox',
        'yankees': 'New York Yankees',
        'rays': 'Tampa Bay Rays',
        'blue jays': 'Toronto Blue Jays',
        'white sox': 'Chicago White Sox',
        'guardians': 'Cleveland Guardians',
        'tigers': 'Detroit Tigers',
        'royals': 'Kansas City Royals',
        'twins': 'Minnesota Twins',
        'athletics': 'Athletics',
        'astros': 'Houston Astros',
        'angels': 'Los Angeles Angels',
        'mariners': 'Seattle Mariners',
        'rangers': 'Texas Rangers',
        'braves': 'Atlanta Braves',
        'marlins': 'Miami Marlins',
        'mets': 'New York Mets',
        'phillies': 'Philadelphia Phillies',
        'nationals': 'Washington Nationals',
        'cubs': 'Chicago Cubs',
        'reds': 'Cincinnati Reds',
        'brewers': 'Milwaukee Brewers',
        'pirates': 'Pittsburgh Pirates',
        'cardinals': 'St. Louis Cardinals',
        'diamondbacks': 'Arizona Diamondbacks',
        'rockies': 'Colorado Rockies',
        'dodgers': 'Los Angeles Dodgers',
        'padres': 'San Diego Padres',
        'giants': 'San Francisco Giants',
    }
    return teams.get(text, text).casefold()


def trade_card_errors(repo, fid, move, outgoing, incoming):
    if not isinstance(incoming, dict):
        return ['Choose or enter one incoming trade card.']

    rules = move.get('constraints', {})
    required_kind = rules.get('kind', outgoing['kind'])
    errors = []

    if (
        outgoing['kind'] != required_kind
        or incoming.get('kind') != required_kind
    ):
        errors.append('Trade hitters for hitters and pitchers for pitchers.')

    errors.extend(card_event_errors(incoming, settings(repo, fid)))

    allowed_teams = rules.get('teams', [])
    if allowed_teams and _team_key(incoming.get('team', '')) not in {
        _team_key(team) for team in allowed_teams
    }:
        errors.append(
            'Incoming team must match the market spin. Allowed teams: '
            + ', '.join(allowed_teams)
        )

    primary = incoming.get('primary')
    secondary = incoming.get('secondary', [])
    if (
        primary not in POSITIONS
        or not isinstance(secondary, list)
        or any(position not in POSITIONS for position in secondary)
    ):
        errors.append('Enter valid primary and secondary positions.')
    else:
        card_positions = {primary} | set(secondary)
        allowed_positions = set(rules.get('positions', []))
        if allowed_positions and not card_positions.intersection(
            allowed_positions
        ):
            errors.append(
                'An incoming primary or secondary position must match '
                'the position spin: ' + ', '.join(rules['positions'])
            )

    ovr = incoming.get('ovr')
    if type(ovr) is not int or not 0 <= ovr <= 99:
        errors.append('Incoming OVR must be an integer from 0 to 99.')
    elif rules.get('max_ovr') is not None and ovr > rules['max_ovr']:
        errors.append(f"Incoming OVR must be {rules['max_ovr']} or lower.")

    return errors


def _resolve_reunion(repo, fid, move, target_id, new_player, notes):
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
        raise RuleError(' '.join(errors))

    before_card = dict(player)
    if player['area'] not in ACTIVE_AREAS:
        player.update(
            area='minors',
            position=player['primary'],
            order=max(1, player.get('order', 1)),
        )
    player.update(
        historical_only=False,
        last_reunion_at=now(),
        last_reunion_move=move['id'],
    )
    repo.put('players', player)
    move['reunion_player_id'] = pid
    audit(
        repo, fid, 'reunion_card_return',
        before_card, dict(player), notes, move.get('run_id'),
    )


def _cold_bat_target(repo, fid, move, target_id):
    pid = move.get('target')
    if not pid or (target_id is not None and target_id != pid):
        raise RuleError('Use the selected Cold Bat player.')

    player = repo.get('players', pid)
    if not player or player['franchise_id'] != fid:
        raise RuleError('The Cold Bat player is unavailable.')
    return player


def _set_next_week_hot_seat(repo, fid, move, player, notes):
    run = repo.get('runs', move.get('run_id'))
    if not run or run['franchise_id'] != fid:
        raise RuleError('The source week is unavailable.')

    before = dict(player)
    player['hot_seat'] = True
    player['hot_seat_until_run'] = max(
        player.get('hot_seat_until_run', 0),
        run['number'] + 1,
    )
    repo.put('players', player)
    audit(
        repo, fid, 'cold_bat_hot_seat',
        before, dict(player), notes, run['id'],
    )


def _resolve_cold_bat(
    repo, fid, move, target_id, new_player, notes,
    no_lower_card_confirmed, next_card_confirmed,
):
    player = _cold_bat_target(repo, fid, move, target_id)

    if player['area'] not in ['lineup', 'bench']:
        move.update(status='invalid', critical=False)
        move['unavailable_reason'] = (
            'The selected player is no longer on the active hitting roster.'
        )
        return

    if protected(repo, fid, player):
        raise RuleError(
            'This player is now protected. Resolve the protection conflict '
            'before applying a Cold Bat consequence.'
        )

    if move['type'] == 'cold_bat_hot_seat':
        _set_next_week_hot_seat(repo, fid, move, player, notes)

    elif move['type'] == 'cold_bat_order':
        if player['area'] != 'lineup' or player['order'] not in [7, 8, 9]:
            raise RuleError(
                'Arrange this hitter in lineup spot 7, 8, or 9 '
                'in Roster Manager, then confirm this move.'
            )
        move['confirmed_order'] = player['order']

    elif move['type'] == 'cold_bat_bench':
        if player['area'] != 'bench':
            raise RuleError(
                'Move this hitter to the bench and arrange a legal '
                'replacement in Roster Manager, then confirm this move.'
            )
        move['confirmed_area'] = 'bench'

    elif move['type'] == 'downgrade':
        if no_lower_card_confirmed:
            if new_player is not None:
                raise RuleError(
                    'Do not submit a lower card when confirming none exists.'
                )
            _set_next_week_hot_seat(repo, fid, move, player, notes)
            move['fallback_applied'] = 'hot_seat'
        else:
            if not next_card_confirmed:
                raise RuleError(
                    'Verify the next available lower-rated Event-legal card.'
                )
            _change_card(repo, fid, move, player, new_player, notes, 'down')


def _change_card(repo, fid, move, player, incoming, notes, direction):
    if not isinstance(incoming, dict):
        raise RuleError('Enter one card as a JSON object.')
    if (
        incoming.get('name', '').strip().casefold()
        != player['name'].strip().casefold()
    ):
        raise RuleError('The card must be the same player.')
    if incoming.get('kind') != player['kind']:
        raise RuleError('The card must have the same player type.')

    ovr = incoming.get('ovr')
    valid_ovr = (
        type(ovr) is int
        and 0 <= ovr <= 99
        and (
            ovr > player['ovr']
            if direction == 'up'
            else ovr < player['ovr']
        )
    )
    if not valid_ovr:
        raise RuleError(
            'Enter a higher OVR, up to 99.'
            if direction == 'up'
            else 'Enter a lower OVR, from 0 to 99.'
        )
    if not str(incoming.get('version', '')).strip():
        raise RuleError('Enter the new card version.')

    primary = incoming.get('primary')
    secondary = incoming.get('secondary', [])
    if (
        primary not in POSITIONS
        or not isinstance(secondary, list)
        or any(pos not in POSITIONS for pos in secondary)
    ):
        raise RuleError('Enter valid primary and secondary positions.')

    before = dict(player)
    changed = dict(player)
    for field in [
        'version', 'ovr', 'primary', 'secondary',
        'team', 'series', 'bat', 'throw', 'eligibility',
    ]:
        if field in incoming:
            changed[field] = incoming[field]

    if incoming.get('eligibility') != 'legal':
        raise RuleError('Verify that the new card is Event-legal.')

    errors = card_event_errors(changed, settings(repo, fid))
    if errors:
        raise RuleError(' '.join(errors))

    if changed['position'] not in legal_positions(changed):
        raise RuleError(
            'The new card cannot play the current assigned position. '
            'Arrange the player legally first.'
        )

    # Old card artwork/UUID must not identify a different version.
    for field in ['card_uuid', 'card_image_url']:
        if incoming.get(field):
            changed[field] = incoming[field]
        else:
            changed.pop(field, None)

    repo.put('players', changed)
    audit(
        repo, fid,
        'card_upgrade' if direction == 'up' else 'card_downgrade',
        before, changed, notes, move.get('run_id'),
    )


def resolve_move(
    repo, fid, mid, action, notes,
    target_id=None,
    new_player=None,
    replace_tag=None,
    confirmed=False,
    cancel_move_id=None,
    max_card_confirmed=False,
    incoming_player_id=None,
    no_lower_card_confirmed=False,
    next_card_confirmed=False,
):
    with repo.transaction():
        move = repo.get('moves', mid)
        if not move or move['franchise_id'] != fid:
            raise RuleError('Invalid move.')
        if move['status'] not in ['pending', 'deferred']:
            return
        if locked(repo, fid):
            raise RuleError('Banked moves resolve after the week ends.')

        f = repo.get('franchises', fid)
        if f['state'] not in [
            State.MOVES, State.REBUILD, State.VALIDATION,
        ]:
            raise RuleError('Finish MVP and elimination before resolving moves.')
        if not isinstance(notes, str) or not notes.strip() or not confirmed:
            raise RuleError('Provide resolution notes and confirm the action.')
        if incoming_player_id is not None and move['type'] != 'trade':
            raise RuleError(
                'An existing incoming card can only be selected for a trade.'
            )

        before = dict(move)

        if action in ['deferred', 'canceled']:
            if move_required(repo, move) and move['type'] != 'tag':
                raise RuleError(
                    'Critical consequences must be applied; '
                    'they cannot be skipped.'
                )
            move.update(status=action, critical=False)

        elif action == 'resolved':
            trade_rules = trade_policy(repo, move) if move['type'] == 'trade' else None
            if trade_rules and trade_rules['choose_outgoing'] and not target_id:
                raise RuleError('Choose the outgoing player for Free Trade.')
            pid = target_id or move.get('target')

            if (
                move['type'] in ['dfa', 'demote', 'trade']
                and move.get('target')
                and pid != move['target']
                and not (trade_rules and trade_rules['choose_outgoing'])
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
                    ['dfa'] if move['type'] == 'save_dfa'
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
                    resolution_notes='Canceled by reward ' + mid + ': ' + notes,
                )
                repo.put('moves', other)
                audit(
                    repo, fid, 'awarded_cancellation',
                    other_before, other, notes, move['run_id'],
                )

            elif move['type'] in [
                'cold_bat_hot_seat', 'cold_bat_order',
                'cold_bat_bench', 'downgrade',
            ]:
                _resolve_cold_bat(
                    repo, fid, move, target_id, new_player, notes,
                    no_lower_card_confirmed, next_card_confirmed,
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
                    raise RuleError('Choose an existing minor-league player.')
                area = (
                    'bench' if player['kind'] == 'hitter'
                    else 'rotation' if player['primary'] == 'SP'
                    else 'bullpen'
                )
                position = (
                    player['primary'] if player['kind'] == 'hitter'
                    else 'SP' if area == 'rotation' else 'RP'
                )
                arrange(repo, fid, pid, area, position, player['order'])

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
                    p['id'] for p in pool if p['id'] != pid
                ][:quantity - 1]
                if len(targets) < quantity:
                    raise RuleError(
                        'Not enough eligible players for the required quantity.'
                    )

                existing_incoming = None
                incoming = None

                if move['type'] == 'trade':
                    if quantity != 1:
                        raise RuleError(
                            'Trades require one outgoing and one incoming card.'
                        )
                    if incoming_player_id is not None:
                        if new_player is not None:
                            raise RuleError(
                                'Choose an existing card or submit JSON, not both.'
                            )
                        existing_incoming = repo.get(
                            'players', incoming_player_id,
                        )
                        if (
                            not existing_incoming
                            or existing_incoming['franchise_id'] != fid
                            or existing_incoming['area'] != 'minors'
                            or incoming_player_id == pid
                        ):
                            raise RuleError(
                                'Choose an incoming card from this '
                                'franchise’s Minors.'
                            )
                        incoming = existing_incoming
                    else:
                        if not isinstance(new_player, dict):
                            raise RuleError(
                                'Choose an existing card or enter incoming JSON.'
                            )
                        incoming = dict(new_player)
                        incoming.update(
                            area='minors',
                            position=incoming.get('primary', 'C'),
                            order=1,
                        )

                    errors = trade_card_errors(
                        repo, fid, move, repo.get('players', pid), incoming,
                    )
                    if errors:
                        raise RuleError(' '.join(errors))

                for target in targets:
                    remove_player(
                        repo, fid, target,
                        'minors' if move['type'] == 'demote' else 'dfa',
                    )

                if move['type'] == 'trade':
                    move['outgoing_player_id'] = pid
                    if existing_incoming:
                        before_card = dict(existing_incoming)
                        incoming = dict(existing_incoming)
                        incoming.update(
                            historical_only=False,
                            last_trade_move=mid,
                            last_trade_at=now(),
                        )
                        repo.put('players', incoming)
                        move['incoming_player_id'] = incoming['id']
                        audit(
                            repo, fid, 'trade_existing_card',
                            before_card, incoming, notes, move.get('run_id'),
                        )
                    else:
                        move['incoming_player_id'] = add_player(
                            repo, fid, incoming,
                        )

            elif move['type'] == 'tag':
                if (
                    not pid
                    or grant(
                        repo, fid, pid, replace_tag,
                        source=move['description'],
                    ) == 'cap_decision_required'
                ):
                    raise RuleError(
                        'Choose a tag holder to replace, or decline this new tag.'
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
                is_mvp_upgrade = (
                    move.get('constraints', {}).get('fallback') == 'protection'
                )

                if is_mvp_upgrade and recipient_id != earned_by['id']:
                    raise RuleError('The MVP upgrade must stay with that MVP.')

                if is_mvp_upgrade and max_card_confirmed:
                    if new_player is not None:
                        raise RuleError(
                            'Do not submit a card when confirming no upgrade exists.'
                        )
                    before_card = dict(earned_by)
                    earned_by['protected'] = True
                    repo.put('players', earned_by)
                    move['fallback_applied'] = 'protection'
                    audit(
                        repo, fid, 'mvp_upgrade_fallback',
                        before_card, earned_by, notes, move.get('run_id'),
                    )
                else:
                    if recipient_id != earned_by['id']:
                        if move.get('source') != 'development':
                            raise RuleError(
                                'This upgrade cannot transfer to a teammate.'
                            )
                        if not max_card_confirmed:
                            raise RuleError(
                                'Confirm that the original player has no higher '
                                'Event-eligible card before choosing a teammate.'
                            )
                        move['upgrade_earned_by'] = earned_by['id']

                    player = repo.get('players', recipient_id)
                    if not player or player['franchise_id'] != fid:
                        raise RuleError('The upgrade player is unavailable.')
                    if player['area'] not in ACTIVE_AREAS:
                        raise RuleError(
                            'The player must be on the active roster. '
                            'Defer the upgrade if they have been removed.'
                        )
                    if is_mvp_upgrade and not next_card_confirmed:
                        raise RuleError(
                            'Confirm the next higher-rated Event-legal card.'
                        )

                    move['upgrade_recipient'] = recipient_id
                    _change_card(
                        repo, fid, move, player, new_player, notes, 'up',
                    )

            elif move['type'] == 'acquire':
                incoming = (
                    new_player if isinstance(new_player, list)
                    else [new_player] if new_player else []
                )
                if len(incoming) != quantity:
                    raise RuleError(f'Provide {quantity} incoming card(s).')
                # New Bench Upgrade cards must be hitters. Existing-card
                # acquisitions and same-player upgrades have this same guard
                # in acquisition_service.py.
                if is_bench_upgrade(move) and any(
                    not isinstance(card, dict)
                    or card.get('kind') != 'hitter'
                    for card in incoming
                ):
                    raise RuleError('Bench Upgrade can only acquire hitters.')
                for card in incoming:
                    add_player(repo, fid, card)

            elif move['type'] not in ['review', 'deferred', 'none']:
                raise RuleError(
                    'This move type has no supported resolution: '
                    + move['type']
                )

            if move.get('status') != 'invalid':
                move['status'] = 'resolved'

        else:
            raise RuleError('Unknown resolution action.')

        move.update(resolution_notes=notes, resolved_at=now())
        repo.put('moves', move)
        audit(
            repo, fid, 'resolve_move',
            before, move, notes, move.get('run_id'),
        )


def finish_validation(repo, fid):
    with repo.transaction():
        f = repo.get('franchises', fid)
        if not f or f['state'] != State.VALIDATION:
            raise RuleError('Proceed to roster validation first.')

        run = repo.get('runs', f.get('current_run'))
        if not run:
            raise RuleError('No current week was found.')

        _require_cold_bat_review(repo, fid, run)

        result = validate(repo, fid)
        if not result.valid:
            raise RuleError('\n'.join(result.errors))

        snapshot(repo, fid, run['id'], 'rebuilt')
        current_number = run['number']

        for player in repo.list('players', fid):
            player.update(
                protected=bool(
                    player.get('protection_until_run', 0) > current_number
                ),
                hot_seat=bool(
                    player.get('hot_seat_until_run', 0) > current_number
                ),
            )
            repo.put('players', player)

        f['state'] = State.READY
        repo.put('franchises', f)
