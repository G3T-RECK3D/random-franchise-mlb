from models.domain import State, RuleError, now, uid
from services.game_engine import enqueue, snapshot
from services.roster_service import locked, remove_player, add_player, arrange, protected, target_pool
from services.franchise_tag_service import grant
from services.franchise_service import audit
from services.roster_validator import validate


def confirm_end(repo, fid):
    with repo.transaction():
        f = repo.get('franchises', fid)
        if f['state'] != State.ENDED:
            raise RuleError('No ended run to confirm.')
        r = repo.get('runs', f['current_run'])
        r['offseason_step'] = 'mvp'
        f['state'] = State.MVP
        repo.put('runs', r)
        repo.put('franchises', f)


def select_mvp(repo, fid, pid):
    with repo.transaction():
        f = repo.get('franchises', fid)
        r = repo.get('runs', f['current_run'])
        if f['state'] != State.MVP or pid not in r['roster_ids']:
            raise RuleError('Select a player from the ended run.')
        r.update(mvp=pid, offseason_step='elimination')
        p = repo.get('players', pid)
        p['protected'] = True
        repo.put('players', p)
        repo.put('runs', r)
        enqueue(f, 'mvp', 'run_mvp', target=pid)
        f.update(state=State.WHEEL, return_state=State.ELIMINATION)
        repo.put('franchises', f)


def progress(repo, fid):
    with repo.transaction():
        f = repo.get('franchises', fid)
        r = repo.get('runs', f['current_run'])
        if f['state'] == State.ELIMINATION:
            enqueue(f, 'elimination', 'run_end')
            f.update(state=State.WHEEL, return_state=State.MELTDOWN)
            r['offseason_step'] = 'meltdown'
        elif f['state'] == State.MELTDOWN:
            mode = r['settings']['meltdown']
            if r['wins'] == 0 and r['losses'] == 2 and mode != 'none':
                enqueue(f, 'meltdown' if mode == 'wheel' else 'elimination', '0–2 meltdown')
                f.update(state=State.WHEEL, return_state=State.MOVES)
            else:
                f['state'] = State.MOVES
            r['offseason_step'] = 'moves'
        elif f['state'] == State.MOVES:
            if any(m['status'] == 'pending' and m.get('critical') for m in repo.list('moves', fid)):
                raise RuleError('Resolve all critical obligations before reconstruction.')
            if any(c['status'] == 'awaiting_manual' for c in repo.list('challenges', fid)):
                raise RuleError('Confirm manual challenge evidence first.')
            f['state'] = State.REBUILD
            r['offseason_step'] = 'rebuild'
        elif f['state'] == State.REBUILD:
            f['state'] = State.VALIDATION
        else:
            raise RuleError('Complete the current action first.')
        repo.put('runs', r)
        repo.put('franchises', f)


def resolve_move(repo, fid, mid, action, notes, target_id=None, new_player=None, replace_tag=None, confirmed=False, cancel_move_id=None):
    with repo.transaction():
        m = repo.get('moves', mid)
        if not m or m['franchise_id'] != fid:
            raise RuleError('Invalid move.')
        if m['status'] not in ['pending', 'deferred']:
            return
        if locked(repo, fid):
            raise RuleError('Banked moves can only resolve after the run ends.')
        f = repo.get('franchises', fid)
        if f['state'] not in [State.MOVES, State.REBUILD, State.VALIDATION]:
            raise RuleError('Finish MVP and elimination before resolving moves.')
        if not notes.strip() or not confirmed:
            raise RuleError('Provide resolution notes and confirm the action.')
        before = dict(m)
        if action in ['deferred', 'canceled']:
            if m.get('critical') and m['type'] != 'tag':
                raise RuleError('Critical consequences must be applied; they cannot be skipped.')
            m.update(status=action, critical=False)
        elif action == 'resolved':
            pid = target_id or m.get('target')
            if m['type'] in ['dfa', 'demote', 'trade'] and m.get('target') and pid != m['target']:
                original = repo.get('players', m['target'])
                if original and original['area'] in ['lineup', 'bench', 'rotation', 'bullpen'] and not protected(repo, fid, original):
                    raise RuleError('Use the audited wheel target; retargeting is allowed only if it becomes ineligible.')
            quantity = m.get('constraints', {}).get('quantity', 1)
            if m['type'] in ['cancel_elimination', 'save_dfa']:
                other = repo.get('moves', cancel_move_id) if cancel_move_id else None
                allowed = ['dfa'] if m['type'] == 'save_dfa' else ['dfa', 'demote', 'trade']
                if not other or other['franchise_id'] != fid or other['run_id'] != m['run_id'] or other['status'] != 'pending' or other['type'] not in allowed:
                    raise RuleError('Select an eligible pending consequence from this run.')
                other.update(status='canceled', critical=False, resolved_at=now(), resolution_notes='Canceled by reward ' + mid + ': ' + notes)
                repo.put('moves', other)
                audit(repo, fid, 'awarded_cancellation', None, other, notes, m['run_id'])
            elif m['type'] == 'call_up':
                p = repo.get('players', pid) if pid else None
                if not p or p['franchise_id'] != fid or p['area'] != 'minors':
                    raise RuleError('Choose an existing minor-league player.')
                area = 'bench' if p['kind'] == 'hitter' else 'rotation' if p['primary'] == 'SP' else 'bullpen'
                arrange(repo, fid, pid, area, p['primary'], p['order'])
            elif m['type'] in ['dfa', 'demote', 'trade']:
                pool = target_pool(repo, fid)
                if not pid or pid not in {p['id'] for p in pool}:
                    if not pool:
                        m.update(status='invalid', critical=False, resolution_notes='No eligible unprotected target: ' + notes)
                        repo.put('moves', m)
                        audit(repo, fid, 'impossible_move', before, m, notes)
                        return
                    raise RuleError('Choose an eligible, unprotected active player.')
                targets = [pid] + [p['id'] for p in pool if p['id'] != pid][:quantity - 1]
                if len(targets) < quantity:
                    raise RuleError('Not enough eligible players for the required quantity.')
                for target in targets:
                    remove_player(repo, fid, target, 'minors' if m['type'] == 'demote' else 'dfa')
                if m['type'] == 'trade':
                    if not new_player:
                        raise RuleError('Enter the incoming trade card.')
                    add_player(repo, fid, new_player)
            elif m['type'] == 'tag':
                if not pid or grant(repo, fid, pid, replace_tag, source=m['description']) == 'cap_decision_required':
                    raise RuleError('Choose a tag holder to replace, or decline this new tag.')
            elif m['type'] == 'protect':
                p = repo.get('players', pid)
                if not p or p['franchise_id'] != fid:
                    raise RuleError('Select a protection target.')
                p['protected'] = True
                if 'Next Run' in m['description']:
                    p['protection_until_run'] = repo.get('runs', f['current_run'])['number'] + 1
                repo.put('players', p)
            elif m['type'] == 'extra_spin':
                enqueue(f, 'front_office', m['id'])
                f.update(state=State.WHEEL, return_state=State.MOVES)
                repo.put('franchises', f)
            elif m['type'] == 'acquire':
                incoming = new_player if isinstance(new_player, list) else [new_player] if new_player else []
                if len(incoming) != quantity:
                    raise RuleError(f'Provide {quantity} incoming card(s).')
                for card in incoming:
                    add_player(repo, fid, card)
            # Review/choice rewards are explicitly acknowledged with notes.
            m['status'] = 'resolved'
        else:
            raise RuleError('Unknown resolution action.')
        m.update(resolution_notes=notes, resolved_at=now())
        repo.put('moves', m)
        audit(repo, fid, 'resolve_move', before, m, notes, m.get('run_id'))


def finish_validation(repo, fid):
    with repo.transaction():
        f = repo.get('franchises', fid)
        if f['state'] != State.VALIDATION:
            raise RuleError('Proceed to roster validation first.')
        result = validate(repo, fid)
        if not result.valid:
            raise RuleError('\n'.join(result.errors))
        snapshot(repo, fid, f['current_run'], 'rebuilt')
        # MVP/temporary protection protects through this elimination cycle, then expires.
        current_number = repo.get('runs', f['current_run'])['number']
        for p in repo.list('players', fid):
            p.update(protected=bool(p.get('protection_until_run', 0) > current_number), hot_seat=False)
            repo.put('players', p)
        f['state'] = State.READY
        repo.put('franchises', f)
