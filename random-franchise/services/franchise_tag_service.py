from models.domain import RuleError, uid, now
from services.franchise_service import settings, audit

def grant(repo, fid, pid, replace_id=None, source='manual'):
    with repo.transaction():
        p = repo.get('players', pid)
        if not p or p['franchise_id'] != fid:
            raise RuleError('Invalid tag player.')
        tags = [t for t in repo.list('tags', fid) if t['active']]
        if any(t['player_id'] == pid for t in tags):
            return 'already_tagged'
        if len(tags) >= settings(repo, fid)['tag_cap']:
            old = next((t for t in tags if t['player_id'] == replace_id), None)
            if not old:
                return 'cap_decision_required'
            old['active'] = False
            repo.put('tags', old)
            audit(repo, fid, 'replace_tag', old['player_id'], pid, source)
        repo.put('tags', dict(id=uid(), franchise_id=fid, player_id=pid, active=True, created_at=now(), source=source))
        audit(repo, fid, 'grant_tag', None, pid, source)
        return 'granted'
