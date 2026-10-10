"""Document repository with indexed ownership, transactions, and immutable audits.

Domain services use get/list/put/delete only. A Postgres repository can implement
this small API without moving game rules into the UI or database adapter.
"""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Protocol

TABLES = (
    'franchises', 'runs', 'players', 'games', 'stats', 'spins', 'moves',
    'rewards', 'challenges', 'snapshots', 'corrections', 'tags',
    'wheels', 'settings', 'seasons',
)
IMMUTABLE = {'spins', 'corrections', 'snapshots'}

class Repository(Protocol):
    def get(self, table: str, identifier: str) -> dict[str, Any] | None: ...
    def list(self, table: str, franchise_id: str | None = None, run_id: str | None = None) -> list[dict]: ...
    def put(self, table: str, value: dict) -> None: ...
    def delete(self, table: str, identifier: str) -> None: ...
    def transaction(self): ...

class SQLiteRepository:
    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute('PRAGMA foreign_keys=ON')
        self.connection.execute('PRAGMA journal_mode=WAL')
        self.connection.execute('PRAGMA busy_timeout=30000')
        self._depth = 0
        self.migrate()

    def migrate(self) -> None:
        version = self.connection.execute('PRAGMA user_version').fetchone()[0]
        if version > 1:
            raise RuntimeError('Database is newer than this app; use the matching app version.')
        for table in TABLES:
            self.connection.execute(f'''CREATE TABLE IF NOT EXISTS {table} (
                id TEXT PRIMARY KEY, franchise_id TEXT, run_id TEXT, payload TEXT NOT NULL
                CHECK(json_valid(payload)))''')
            self.connection.execute(f'CREATE INDEX IF NOT EXISTS ix_{table}_owner ON {table}(franchise_id,run_id)')
        for table in IMMUTABLE:
            for action in ('UPDATE', 'DELETE'):
                self.connection.execute(f'''CREATE TRIGGER IF NOT EXISTS immutable_{table}_{action}
                    BEFORE {action} ON {table} BEGIN SELECT RAISE(ABORT,'Immutable audit record'); END''')
        self.connection.execute('PRAGMA user_version=1')

    @staticmethod
    def _table(table: str) -> str:
        if table not in TABLES:
            raise ValueError('Unknown table')
        return table

    @contextmanager
    def transaction(self):
        outer = self._depth == 0
        if outer:
            self.connection.execute('BEGIN IMMEDIATE')
        self._depth += 1
        try:
            yield self
        except BaseException:
            if outer:
                self.connection.execute('ROLLBACK')
            raise
        else:
            if outer:
                self.connection.execute('COMMIT')
        finally:
            self._depth -= 1

    def get(self, table: str, identifier: str) -> dict | None:
        row = self.connection.execute(f'SELECT payload FROM {self._table(table)} WHERE id=?', (identifier,)).fetchone()
        return json.loads(row[0]) if row else None

    def list(self, table: str, franchise_id=None, run_id=None) -> list[dict]:
        where, values = [], []
        for key, value in [('franchise_id', franchise_id), ('run_id', run_id)]:
            if value is not None:
                where.append(f'{key}=?')
                values.append(value)
        query = f'SELECT payload FROM {self._table(table)}'
        if where:
            query += ' WHERE ' + ' AND '.join(where)
        return [json.loads(row[0]) for row in self.connection.execute(query + ' ORDER BY rowid', values)]

    def put(self, table: str, value: dict) -> None:
        table = self._table(table)
        params = (value['id'], value.get('franchise_id'), value.get('run_id'), json.dumps(value, allow_nan=False))
        sql = f'INSERT INTO {table}(id,franchise_id,run_id,payload) VALUES (?,?,?,?)'
        if table not in IMMUTABLE:
            sql += ' ON CONFLICT(id) DO UPDATE SET franchise_id=excluded.franchise_id,run_id=excluded.run_id,payload=excluded.payload'
        self.connection.execute(sql, params)

    def delete(self, table: str, identifier: str):
        self.connection.execute(f'DELETE FROM {self._table(table)} WHERE id=?', (identifier,))

    def backup_bytes(self) -> bytes:
        import tempfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'backup.db'
            destination = sqlite3.connect(path)
            self.connection.backup(destination)
            destination.close()
            return path.read_bytes()

    def close(self):
        self.connection.close()
