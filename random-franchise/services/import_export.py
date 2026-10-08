"""Manual roster interchange; external provider integration deliberately unimplemented."""
import csv
import io
import json
from typing import Protocol
from models.domain import RuleError
from services.roster_service import add_player, locked

class RosterProvider(Protocol):
    def fetch_roster(self, external_id: str) -> list[dict]: ...

class ExternalProviderPlaceholder:
    def fetch_roster(self, external_id: str) -> list[dict]:
        raise NotImplementedError('Configure a licensed provider adapter in V2. No scraping is performed.')

FIELDS = ['name','version','ovr','primary','secondary','kind','team','series','bat','throw','area','position','order','eligibility','notes']

def export_roster(repo, fid, fmt='json'):
    rows = [{key: p.get(key, '') for key in FIELDS} for p in repo.list('players', fid)]
    if fmt == 'json':
        return json.dumps(rows, indent=2)
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=FIELDS)
    writer.writeheader()
    for row in rows:
        row['secondary'] = '|'.join(row['secondary'])
        writer.writerow(row)
    return stream.getvalue()

def import_roster(repo, fid, content, fmt):
    if locked(repo, fid):
        raise RuleError('Roster imports are only available between runs.')
    try:
        rows = json.loads(content) if fmt == 'json' else list(csv.DictReader(io.StringIO(content)))
        if not isinstance(rows, list) or len(rows) > 500:
            raise ValueError('Expected a list of at most 500 cards.')
        with repo.transaction():
            ids = []
            for raw in rows:
                data = {key: value for key, value in raw.items() if key in FIELDS}
                for key in ['ovr', 'order']:
                    if key in data:
                        data[key] = int(data[key])
                if isinstance(data.get('secondary'), str):
                    data['secondary'] = [s.strip() for s in data['secondary'].split('|') if s.strip()]
                ids.append(add_player(repo, fid, data))
            return ids
    except (ValueError, TypeError, AttributeError) as exc:
        raise RuleError(f'Import rejected; no rows changed: {exc}') from exc
