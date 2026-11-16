import sys
from pathlib import Path
import psycopg2

MCP_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = MCP_DIR.parent
for p in (str(MCP_DIR), str(ROOT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from mcp_server.config import settings
except ModuleNotFoundError:
    from config import settings  # type: ignore[import-not-found]


def run_migrations() -> None:
    """Menjalankan file migrasi SQL yang belum diaplikasikan ke PostgreSQL pgvector."""
    settings.reload()
    conn = psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        connect_timeout=5,
    )
    conn.autocommit = True
    cursor = conn.cursor()

    migrations_dir = Path(__file__).resolve().parent
    sql_files = sorted(f.name for f in migrations_dir.glob("*.sql"))

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version VARCHAR(50) PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    for file_name in sql_files:
        cursor.execute(
            "SELECT 1 FROM schema_migrations WHERE version = %s;",
            (file_name,),
        )
        if cursor.fetchone() is None:
            print(f"[MIGRATION] Menjalankan {file_name}...")
            file_path = migrations_dir / file_name
            sql_content = file_path.read_text(encoding="utf-8")
            cursor.execute(sql_content)
            cursor.execute(
                "INSERT INTO schema_migrations (version) VALUES (%s);",
                (file_name,),
            )
            print(f"[MIGRATION] Sukses mengaplikasikan {file_name}.")
        else:
            print(f"[MIGRATION] {file_name} sudah diaplikasikan sebelumnya.")

    cursor.close()
    conn.close()


if __name__ == "__main__":
    run_migrations()
