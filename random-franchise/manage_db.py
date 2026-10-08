"""Explicit initialization, safe reset, and backup restore CLI."""
import argparse
import os
import shutil
import sqlite3
from pathlib import Path
from repositories.sqlite import SQLiteRepository, TABLES


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['init','reset','restore'])
    parser.add_argument('--path',default=os.environ.get('RANDOM_FRANCHISE_DB','data/random_franchise.db'))
    parser.add_argument('--backup')
    parser.add_argument('--confirm',action='store_true',help='Confirm destructive reset/restore')
    args=parser.parse_args();path=Path(args.path)
    if args.action in ['reset','restore'] and not args.confirm:parser.error('Stop Streamlit first, then add --confirm.')
    if args.action=='restore':
        if not args.backup:parser.error('--backup is required.')
        source=Path(args.backup)
        if source.resolve()==path.resolve():parser.error('Backup and destination must differ.')
        con=sqlite3.connect(f'{source.resolve().as_uri()}?mode=ro',uri=True)
        try:
            if con.execute('PRAGMA integrity_check').fetchone()[0]!='ok':parser.error('Invalid database.')
            tables={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if not set(TABLES)<=tables or con.execute('PRAGMA user_version').fetchone()[0]!=1:parser.error('Incompatible backup.')
        finally:con.close()
    if args.action in ['reset','restore']:
        if path.exists():shutil.copy2(path,path.with_suffix('.pre-change-backup.db'))
        for suffix in ['', '-wal', '-shm']:Path(str(path)+suffix).unlink(missing_ok=True)
    path.parent.mkdir(parents=True,exist_ok=True)
    if args.action=='restore':shutil.copy2(args.backup,path)
    repo=SQLiteRepository(path);repo.close()
    print(f'Database {args.action} complete: {path}')

if __name__=='__main__':main()
