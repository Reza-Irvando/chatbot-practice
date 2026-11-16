import os
import sys
import time
from pathlib import Path
import psycopg2

MCP_DIR = Path(__file__).resolve().parent
ROOT_DIR = MCP_DIR.parent
for p in (str(MCP_DIR), str(ROOT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from mcp_server.config import settings
    from mcp_server.ingest_uupdp import proses_dan_simpan_uupdp
    from mcp_server.migrations.runner import run_migrations
except ModuleNotFoundError:
    from config import settings  # type: ignore[import-not-found]
    from ingest_uupdp import proses_dan_simpan_uupdp  # type: ignore[import-not-found]
    from migrations.runner import run_migrations  # type: ignore[import-not-found]


def wait_for_db(max_retries: int = 30, delay: int = 2) -> None:
    """Menunggu hingga container PostgreSQL siap menerima koneksi."""
    settings.reload()
    print(
        f"[MCP-INIT] Menunggu PostgreSQL di {settings.DB_HOST}:{settings.DB_PORT} "
        f"(database: {settings.DB_NAME})..."
    )
    for attempt in range(1, max_retries + 1):
        try:
            conn = psycopg2.connect(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                dbname=settings.DB_NAME,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                connect_timeout=3,
            )
            conn.close()
            print(f"[MCP-INIT] Berhasil terhubung ke PostgreSQL pada percobaan ke-{attempt}.")
            return
        except psycopg2.OperationalError as exc:
            if attempt == max_retries:
                print(f"[ERROR] Gagal terhubung ke PostgreSQL setelah {max_retries} percobaan: {exc}")
                sys.exit(1)
            time.sleep(delay)


def init_database() -> None:
    """Menjalankan migrasi skema pgvector dan auto-ingest bila tabel kosong & API key tersedia."""
    wait_for_db()
    run_migrations()

    force_reingest = os.getenv("FORCE_REINGEST", "false").lower() in ("true", "1", "yes")
    conn = psycopg2.connect(
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        dbname=settings.DB_NAME,
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
    )
    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {settings.DOC_TABLE_NAME};")
            count = int(cur.fetchone()[0])
    finally:
        conn.close()

    if count == 0 or force_reingest:
        if not (settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip()):
            print(
                f"[MCP-INIT] Tabel '{settings.DOC_TABLE_NAME}' masih kosong (0 baris). "
                "Isi GEMINI_API_KEY di mcp_server/.env untuk mengisi vektor embedding pgvector."
            )
            return

        print(f"[MCP-INIT] Memulai ingest otomatis naskah UU PDP ke '{settings.DOC_TABLE_NAME}'...")
        try:
            proses_dan_simpan_uupdp()
        except Exception as exc:
            print(f"[WARNING] Auto-ingest ke pgvector gagal ({exc}). Fallback PDF lokal tetap aktif.")
    else:
        print(f"[MCP-INIT] Tabel '{settings.DOC_TABLE_NAME}' sudah terisi ({count} baris).")


if __name__ == "__main__":
    init_database()
