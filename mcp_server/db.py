import os
import sys
from contextlib import contextmanager
from pathlib import Path
import psycopg2
from psycopg2 import pool
from pgvector.psycopg2 import register_vector

# Pastikan root direktori terdaftar di sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import settings

_db_pool: psycopg2.pool.SimpleConnectionPool | None = None


def get_pool() -> psycopg2.pool.SimpleConnectionPool:
    """Mengambil pool koneksi database (lazy initialization)."""
    global _db_pool
    if _db_pool is None or _db_pool.closed:
        _db_pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=10,
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            dbname=settings.DB_NAME,
        )
    return _db_pool


def get_db_connection():
    """Mengambil koneksi dari pool dan mendaftarkan ekstensi pgvector."""
    conn = get_pool().getconn()
    register_vector(conn)
    return conn


def release_db_connection(conn):
    """Mengembalikan koneksi ke pool."""
    if _db_pool is not None and conn is not None:
        _db_pool.putconn(conn)


# Alias untuk kompatibilitas nama fungsi
get_connection = get_db_connection
release_connection = release_db_connection


@contextmanager
def get_db_session():
    """Context manager untuk otomatis mengembalikan koneksi ke pool."""
    conn = get_db_connection()
    try:
        yield conn
    finally:
        release_db_connection(conn)


__all__ = [
    "get_db_connection",
    "release_db_connection",
    "get_connection",
    "release_connection",
    "get_db_session",
    "get_pool",
]
