from pathlib import Path

import psycopg

from app.core.config import get_settings

MIGRATIONS_DIRECTORY = Path(__file__).parent.parent / "migrations"
OPTIONAL_MIGRATION_SUFFIX = ".pgvector.sql"


def apply_migrations(database_url: str) -> None:
    migration_paths = sorted(MIGRATIONS_DIRECTORY.glob("*.sql"))
    with psycopg.connect(database_url) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version text PRIMARY KEY,
                applied_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        connection.execute("SELECT pg_advisory_xact_lock(716403126)")
        applied = {
            row[0]
            for row in connection.execute("SELECT version FROM schema_migrations").fetchall()
        }
        for migration_path in migration_paths:
            if migration_path.name in applied:
                continue
            if migration_path.name.endswith(OPTIONAL_MIGRATION_SUFFIX):
                available = connection.execute(
                    "SELECT EXISTS (SELECT 1 FROM pg_available_extensions WHERE name = 'vector')"
                ).fetchone()
                if not available or not available[0]:
                    continue
            connection.execute(migration_path.read_text(encoding="utf-8"))
            connection.execute(
                "INSERT INTO schema_migrations (version) VALUES (%s)",
                (migration_path.name,),
            )


def main() -> None:
    database_url = get_settings().database_url
    if not database_url:
        raise RuntimeError("DATABASE_URL é obrigatória para executar migrações.")
    apply_migrations(database_url)


if __name__ == "__main__":
    main()
