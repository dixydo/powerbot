from __future__ import annotations

import os
import sys
from pathlib import Path

import psycopg

# Add app directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Load .env file
import config  # noqa: F401


def _env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None or value == "":
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def get_connection_info() -> str:
    host = _env("DB_HOST", "localhost")
    port = _env("DB_PORT", "5432")
    dbname = _env("DB_NAME", "powerbot")
    user = _env("DB_USER", "powerbot")
    password = _env("DB_PASSWORD", "powerbot")
    return f"host={host} port={port} dbname={dbname} user={user} password={password}"


def ensure_schema_migrations(cur: psycopg.Cursor) -> None:
    cur.execute(
        """
        create table if not exists schema_migrations (
            id bigserial primary key,
            filename text not null unique,
            applied_at timestamptz not null default now()
        );
        """
    )


def list_migration_files(migrations_dir: Path) -> list[Path]:
    files = sorted([p for p in migrations_dir.glob("*.sql") if p.is_file()])
    return files


def get_applied(cur: psycopg.Cursor) -> set[str]:
    cur.execute("select filename from schema_migrations order by filename;")
    return {row[0] for row in cur.fetchall()}


def apply_migration(cur: psycopg.Cursor, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    # Single-file migrations; run as-is (can contain multiple statements).
    cur.execute(sql)
    cur.execute("insert into schema_migrations (filename) values (%s);", (path.name,))


def run() -> None:
    migrations_dir = Path(__file__).parent / "migrations"
    migrations_dir.mkdir(parents=True, exist_ok=True)

    connection_info = get_connection_info()
    with psycopg.connect(connection_info) as conn:
        with conn.cursor() as cur:
            ensure_schema_migrations(cur)
            applied = get_applied(cur)

            files = list_migration_files(migrations_dir)
            pending = [p for p in files if p.name not in applied]

            for path in pending:
                apply_migration(cur, path)

        conn.commit()


if __name__ == "__main__":
    run()

