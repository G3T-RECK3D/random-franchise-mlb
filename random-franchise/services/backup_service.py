"""Restore a validated database into a fresh installation without replacing live files."""
import json
import sqlite3
import tempfile
from pathlib import Path
from models.domain import RuleError
from repositories.sqlite import TABLES


def restore_empty(repo, data: bytes):
    if len(data) > 50 * 1024 * 1024 or not data.startswith(b'SQLite format 3\x00'):
        raise RuleError('Upload a SQLite backup under 50 MB.')
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'backup.db'
        path.write_bytes(data)
        source = sqlite3.connect(f'{path.as_uri()}?mode=ro', uri=True)
        try:
            if source.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                raise RuleError('Backup failed integrity checks.')
            if source.execute('PRAGMA user_version').fetchone()[0] != 1:
                raise RuleError('Unsupported backup schema.')
            rows = {}
            for table in TABLES:
                rows[table] = [json.loads(r[0]) for r in source.execute(f'SELECT payload FROM {table} ORDER BY rowid')]
                if any(not isinstance(r, dict) or not isinstance(r.get('id'), str) for r in rows[table]):
                    raise RuleError('Backup contains invalid records.')
            franchise_ids = {f['id'] for f in rows['franchises']}
            if any(r.get('franchise_id') not in franchise_ids for table in TABLES for r in rows[table]):
                raise RuleError('Backup contains orphaned records.')
            with repo.transaction():
                if any(repo.list(table) for table in TABLES):
                    raise RuleError('Restore is only allowed into an empty installation. Keep existing data or restore locally to a separate database.')
                for table in TABLES:
                    for row in rows[table]:
                        repo.put(table, row)
            return len(rows['franchises'])
        except (sqlite3.DatabaseError, ValueError, KeyError) as exc:
            raise RuleError(f'Backup could not be restored: {exc}') from exc
        finally:
            source.close()
