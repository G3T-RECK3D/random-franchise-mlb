from models.domain import RuleError, ACTIVE_AREAS, AREAS, POSITIONS, uid, now
from services.franchise_service import audit
from services.roster_validator import legal_positions

def locked(repo, fid):
    f = repo.get('franchises', fid)
    return bool(f['current_run'] and not repo.get('runs', f['current_run'])['ended_at'])

def protected(repo, fid, player):
    tagged = any(t['player_id'] == player['id'] and t['active'] for t in repo.list('tags', fid))
    return tagged or bool(player.get('protected'))

def target_pool(repo, fid, kind=None):
    return [p for p in repo.list('players', fid) if p['area'] in ACTIVE_AREAS and
            not protected(repo, fid, p) and (kind is None or p['kind'] == kind)]

def add_player(repo, fid, data):
    with repo.transaction():
        if locked(repo, fid):
            raise RuleError('Roster locked: new cards must wait until offseason.')
        if not isinstance(data, dict):
            raise RuleError('Incoming player must be a JSON object.')
        p = dict(id=uid(), franchise_id=fid, name='', version='Base', ovr=75, primary='C', secondary=[],
                 kind='hitter', team='', series='', bat='', throw='', area='minors', position='C', order=1,
                 eligibility='unknown', protected=False, hot_seat=False, notes='', acquired_at=now(),
                 acquisition_run=repo.get('franchises', fid).get('current_run'))
        p.update({key: value for key, value in data.items() if key not in ['id', 'franchise_id']})
        if not p['name'].strip() or not isinstance(p['ovr'], int) or not 0 <= p['ovr'] <= 99:
            raise RuleError('Player needs a name and integer OVR from 0 to 99.')
        if p['kind'] not in ['hitter', 'pitcher'] or p['area'] not in AREAS or p['primary'] not in POSITIONS:
            raise RuleError('Invalid player kind, area, or primary position.')
        if not isinstance(p['secondary'], list) or any(s not in POSITIONS for s in p['secondary']):
            raise RuleError('Secondary positions must be a list of position codes.')
        if p['eligibility'] not in ['legal', 'illegal', 'unknown']:
            raise RuleError('Invalid Event eligibility.')
        if not isinstance(p['order'], int) or p['order'] < 1:
            raise RuleError('Roster order must be a positive integer.')
        repo.put('players', p)
        audit(repo, fid, 'add_player', None, p, 'Manual acquisition')
        return p['id']

def remove_player(repo, fid, pid, area='dfa'):
    with repo.transaction():
        if locked(repo, fid):
            raise RuleError('Roster locked: removals/demotions must wait until offseason.')
        p = repo.get('players', pid)
        if not p or p['franchise_id'] != fid:
            raise RuleError('Player not in this franchise.')
        if area not in ['dfa', 'minors']:
            raise RuleError('Removal destination must be DFA or minors.')
        if protected(repo, fid, p):
            raise RuleError('Tagged/protected players are excluded from ordinary removals.')
        before = dict(p)
        p['area'] = area
        repo.put('players', p)
        audit(repo, fid, 'remove_player', before, p, f'Move to {area}')

def arrange(repo, fid, pid, area, position, order):
    with repo.transaction():
        p = repo.get('players', pid)
        if not p or p['franchise_id'] != fid:
            raise RuleError('Player not in this franchise.')
        if area not in AREAS or not isinstance(order, int) or order < 1:
            raise RuleError('Invalid area or order.')
        if area == 'dfa':
            raise RuleError('Use the confirmed removal action for DFA.')
        if locked(repo, fid) and (p['area'] not in ACTIVE_AREAS or area not in ACTIVE_AREAS):
            raise RuleError('No demotions or call-ups during an active run.')
        if p['area'] in ACTIVE_AREAS and area == 'minors' and protected(repo, fid, p):
            raise RuleError('Tagged/protected players cannot be demoted.')
        if area == 'lineup' and (p['kind'] != 'hitter' or position not in legal_positions(p) or not 1 <= order <= 9):
            raise RuleError('Choose a legal hitting position and batting order 1–9.')
        if area == 'bench' and p['kind'] != 'hitter':
            raise RuleError('Bench players must be hitters.')
        if area in ['rotation', 'bullpen']:
            required = 'SP' if area == 'rotation' else 'RP'
            if p['kind'] != 'pitcher' or position != required or required not in legal_positions(p):
                raise RuleError('Choose a legal pitching role.')
        before = dict(p)
        p.update(area=area, position=position, order=order)
        repo.put('players', p)
        audit(repo, fid, 'arrange', before, p, 'Roster arrangement')

def swap(repo, fid, first_id, second_id):
    with repo.transaction():
        first, second = repo.get('players', first_id), repo.get('players', second_id)
        if not first or not second or first_id == second_id:
            raise RuleError('Select two different players.')
        a, b = (first['area'], first['position'], first['order']), (second['area'], second['position'], second['order'])
        arrange(repo, fid, first_id, *b)
        arrange(repo, fid, second_id, *a)
