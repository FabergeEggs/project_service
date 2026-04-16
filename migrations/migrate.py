from pathlib import Path

from yoyo import get_backend, read_migrations
from yoyo.migrations import MigrationList

_MIGRATION_DIR = str(Path(__file__).parent)


def _read_sql_migrations() -> MigrationList:
    all_migrations = read_migrations(_MIGRATION_DIR)
    sql_only = [m for m in all_migrations if m.path.endswith('.sql')]
    return MigrationList(sql_only, all_migrations.post_apply)


def up(database_dsn: str) -> None:
    '''Apply all pending migrations to the database'''
    backend = get_backend(database_dsn)
    migrations = _read_sql_migrations()
    with backend.lock():
        backend.apply_migrations(backend.to_apply(migrations))


def down(database_dsn: str) -> None:
    '''Rollback the most recently applied migration'''
    backend = get_backend(database_dsn)
    migrations = _read_sql_migrations()
    with backend.lock():
        applied = backend.to_apply(migrations)
        if applied:
            backend.rollback_migration(applied[:1])


def drop(database_dsn: str) -> None:
    '''Drop all tables from the database'''
    backend = get_backend(database_dsn)
    migrations = _read_sql_migrations()
    with backend.lock():
        backend.rollback_migrations(backend.to_rollback(migrations))
