import sys
from pathlib import Path
import psycopg2

# Pastikan root direktori terdaftar di sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import settings


def run_migrations():
    """Menjalankan file migrasi SQL yang belum diaplikasikan."""
    conn = psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
    )
    conn.autocommit = True
    cursor = conn.cursor()

    migrations_dir = Path(__file__).resolve().parent
    sql_files = sorted([f.name for f in migrations_dir.glob("*.sql")])

    # Buat tabel pelacak migrasi terlebih dahulu jika belum ada
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
            with open(file_path, "r", encoding="utf-8") as f:
                sql_content = f.read()
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
