import json
from pathlib import Path
from models.domain import State, RuleError, uid, now

ROOT = Path(__file__).resolve().parents[1]

def defaults(name: str):
    return json.loads((ROOT / 'config' / name).read_text(encoding='utf-8'))

def create_franchise(repo, name: str, event: str) -> str:
    if not name.strip() or not event.strip():
        raise RuleError('Franchise and Event names are required.')

    identifier = uid()
    season_id = uid()
    created = now()

    with repo.transaction():
        repo.put('franchises', dict(
            id=identifier,
            franchise_id=identifier,
            name=name.strip(),
            event=event.strip(),
            state=State.SETUP,
            current_run=None,
            current_season=season_id,
            queue=[],
            return_state=State.ACTIVE,
            created_at=created,
        ))

        repo.put('seasons', dict(
            id=season_id,
            franchise_id=identifier,
            number=1,
            name=event.strip(),
            event=event.strip(),
            status='active',
            started_at=created,
            ended_at=None,
            mvp=None,
        ))

        repo.put('settings', dict(
            id=identifier,
            franchise_id=identifier,
            values=defaults('default_settings.json'),
        ))

        for wheel in defaults('default_wheels.json'):
            repo.put('wheels', dict(
                wheel,
                id=f"{identifier}:{wheel['wheel_id']}",
                franchise_id=identifier,
            ))

    return identifier

def settings(repo, fid):
    return repo.get('settings', fid)['values']

def audit(repo, fid, action, before, after, reason, run_id=None):
    repo.put('corrections', dict(id=uid(), franchise_id=fid, run_id=run_id, action=action,
                                before=before, after=after, reason=reason, created_at=now()))

def save_settings(repo, fid, values):
    with repo.transaction():
        f = repo.get('franchises', fid)
        if f['current_run'] and not repo.get('runs', f['current_run'])['ended_at']:
            raise RuleError('Change rules between runs so the current entry uses one consistent ruleset.')
        if not isinstance(values, dict):
            raise RuleError('Settings must be a JSON object.')
        values = {**defaults('default_settings.json'), **values}
        if not isinstance(values.get('milestones'), dict):
            raise RuleError('Milestones must be an object mapping win thresholds to wheel IDs.')
        for key in ['team', 'series', 'primary', 'bat', 'throw']:
            for prefix in ['allowed_', 'disallowed_']:
                items = values[prefix + key]
                if not isinstance(items, list) or any(not isinstance(x, str) for x in items):
                    raise RuleError(f'{prefix + key} must be a list of strings.')
        if values.get('ovr_cap') is not None and (not isinstance(values['ovr_cap'], (int, float)) or not 0 < values['ovr_cap'] <= 99):
            raise RuleError('OVR cap must be null or a number greater than zero and no more than 99.')
        if not isinstance(values.get('max_losses'), int) or not 1 <= values['max_losses'] <= 10:
            raise RuleError('Maximum losses must be an integer from 1 to 10.')
        if not isinstance(values.get('tag_cap'), int) or values['tag_cap'] < 1:
            raise RuleError('Tag cap must be a positive integer.')
        if len([t for t in repo.list('tags', fid) if t['active']]) > values['tag_cap']:
            raise RuleError('Remove tags before lowering the cap.')
        if values.get('meltdown') not in ['none', 'wheel', 'extra_elimination']:
            raise RuleError('Meltdown must be none, wheel, or extra_elimination.')
        valid_wheels = {w['wheel_id'] for w in repo.list('wheels', fid)}
        for key, wheel in values.get('milestones', {}).items():
            if not str(key).isdigit() or int(key) < 1 or wheel not in valid_wheels:
                raise RuleError('Milestones need positive win counts and existing wheel IDs.')
        for key in ['bench_size', 'rotation_size', 'bullpen_size']:
            if not isinstance(values.get(key), int) or not 0 <= values[key] <= 30:
                raise RuleError(f'{key} must be an integer from 0 to 30.')
        before = settings(repo, fid)
        repo.put('settings', dict(id=fid, franchise_id=fid, values=values))
        audit(repo, fid, 'settings', before, values, 'Settings editor')
def setup_recovered_seasons(repo, fid):
    """Prepare an empty franchise for two recovered Event seasons."""
    with repo.transaction():
        f = repo.get('franchises', fid)
        if not f:
            raise RuleError('Select a valid franchise.')

        if repo.list('runs', fid) or repo.list('games', fid):
            raise RuleError(
                'Season recovery setup must happen before adding weeks or games.'
            )

        seasons = repo.list('seasons', fid)
        names = [
            '2026 Wildcard Series Event',
            '2026 Division Series Event',
        ]

        # Repeating the setup leaves the existing season records unchanged.
        if len(seasons) == 2:
            ordered = sorted(seasons, key=lambda s: s['number'])
            if (
                [s['number'] for s in ordered] == [1, 2]
                and [s['event'] for s in ordered] == names
                and ordered[0]['status'] == 'completed'
                and ordered[1]['status'] == 'active'
                and f.get('current_season') == ordered[1]['id']
            ):
                return
            raise RuleError('This franchise already has a different season setup.')

        if len(seasons) > 1:
            raise RuleError('This franchise already has multiple seasons.')

        if seasons:
            first = dict(seasons[0])
            if first.get('mvp'):
                raise RuleError('The existing season already has an MVP.')
        else:
            first = dict(id=uid(), franchise_id=fid, created_at=now())

        before = dict(franchise=dict(f), seasons=seasons)

        first.update(
            number=1,
            name=names[0],
            event=names[0],
            status='completed',
            started_at=None,
            ended_at=None,
            mvp=None,
            recovered=True,
        )

        second = dict(
            id=uid(),
            franchise_id=fid,
            number=2,
            name=names[1],
            event=names[1],
            status='active',
            created_at=now(),
            started_at=None,
            ended_at=None,
            mvp=None,
            recovered=True,
        )

        repo.put('seasons', first)
        repo.put('seasons', second)

        f.update(
            current_season=second['id'],
            event=names[1],
        )
        repo.put('franchises', f)

        audit(
            repo, fid, 'setup_recovered_seasons',
            before,
            dict(franchise=f, seasons=[first, second]),
            'Restore season structure before importing historical games.',
        )
