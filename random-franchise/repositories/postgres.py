"""Persistent PostgreSQL storage for the franchise app."""

import json
import tempfile
from contextlib import contextmanager
from pathlib import Path

import psycopg

from repositories.sqlite import TABLES, IMMUTABLE, SQLiteRepository


SCHEMA = 'random_franchise'
LOCK_ID = 724031920


class PostgresRepository:
    def __init__(self, config):
        self._depth = 0
        self.connection = psycopg.connect(
            host=config['host'],
            port=int(config.get('port', 5432)),
            dbname=config.get('dbname', 'postgres'),
            user=config['user'],
            password=config['password'],
            sslmode='require',
            connect_timeout=20,
            autocommit=True,
        )
        try:
            self.migrate()
        except BaseException:
            self.connection.close()
            raise

    @staticmethod
    def _table(table):
        if table not in TABLES:
            raise ValueError('Unknown table')
        return f'{SCHEMA}.{table}'

    @contextmanager
    def transaction(self):
        outer = self._depth == 0
        with self.connection.transaction():
            if outer:
                self.connection.execute(
                    'SELECT pg_advisory_xact_lock(%s)',
                    (LOCK_ID,),
                )
            self._depth += 1
            try:
                yield self
            finally:
                self._depth -= 1

    def migrate(self):
        with self.transaction():
            ready = self.connection.execute(
                'SELECT to_regclass(%s)',
                (f'{SCHEMA}.settings',),
            ).fetchone()[0]
            if ready:
                return

            self.connection.execute(
                f'CREATE SCHEMA IF NOT EXISTS {SCHEMA}'
            )
            self.connection.execute(f"""
                CREATE OR REPLACE FUNCTION
                {SCHEMA}.reject_audit_change()
                RETURNS trigger
                LANGUAGE plpgsql
                AS $$
                BEGIN
                    RAISE EXCEPTION 'Immutable audit record';
                END;
                $$
            """)

            for table in TABLES:
                name = self._table(table)
                self.connection.execute(f"""
                    CREATE TABLE {name} (
                        sequence BIGINT GENERATED ALWAYS AS IDENTITY,
                        id TEXT PRIMARY KEY,
                        franchise_id TEXT,
                        run_id TEXT,
                        payload TEXT NOT NULL
                            CHECK (
                                jsonb_typeof(payload::jsonb) = 'object'
                            )
                    )
                """)
                self.connection.execute(f"""
                    CREATE INDEX ix_{table}_owner
                    ON {name}(franchise_id, run_id)
                """)
                if table in IMMUTABLE:
                    self.connection.execute(f"""
                        CREATE TRIGGER immutable_{table}
                        BEFORE UPDATE OR DELETE ON {name}
                        FOR EACH ROW EXECUTE FUNCTION
                        {SCHEMA}.reject_audit_change()
                    """)

    def get(self, table, identifier):
        row = self.connection.execute(
            f'SELECT payload FROM {self._table(table)} WHERE id=%s',
            (identifier,),
        ).fetchone()
        return json.loads(row[0]) if row else None

    def list(self, table, franchise_id=None, run_id=None):
        where = []
        values = []
        for key, value in [
            ('franchise_id', franchise_id),
            ('run_id', run_id),
        ]:
            if value is not None:
                where.append(f'{key}=%s')
                values.append(value)

        query = f'SELECT payload FROM {self._table(table)}'
        if where:
            query += ' WHERE ' + ' AND '.join(where)
        query += ' ORDER BY sequence'

        rows = self.connection.execute(query, values).fetchall()
        return [json.loads(row[0]) for row in rows]

    def put(self, table, value):
        name = self._table(table)
        payload = json.dumps(value, allow_nan=False)
        query = f"""
            INSERT INTO {name}
                (id, franchise_id, run_id, payload)
            VALUES (%s, %s, %s, %s)
        """
        if table not in IMMUTABLE:
            query += """
                ON CONFLICT(id) DO UPDATE SET
                    franchise_id=excluded.franchise_id,
                    run_id=excluded.run_id,
                    payload=excluded.payload
            """
        self.connection.execute(
            query,
            (
                value['id'],
                value.get('franchise_id'),
                value.get('run_id'),
                payload,
            ),
        )

    def delete(self, table, identifier):
        self.connection.execute(
            f'DELETE FROM {self._table(table)} WHERE id=%s',
            (identifier,),
        )

    def backup_bytes(self):
        """Keep the existing downloadable SQLite backup format."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'backup.db'
            destination = SQLiteRepository(path)
            try:
                with self.transaction():
                    with destination.transaction():
                        for table in TABLES:
                            for row in self.list(table):
                                destination.put(table, row)
                return destination.backup_bytes()
            finally:
                destination.close()

    def close(self):
        self.connection.close()
