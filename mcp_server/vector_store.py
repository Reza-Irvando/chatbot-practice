import sys
from pathlib import Path
import requests

# Pastikan Root Direktori terdaftar di sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import settings
from mcp_server.db import get_db_session


def get_embedding(text: str) -> list[float]:
    """Mengambil vektor embedding dari Ollama nomic-embed-text."""
    url = f"{settings.OLLAMA_BASE_URL}/api/embeddings"
    payload = {
        "model": settings.EMBEDDING_MODEL,
        "prompt": text,
    }
    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()
    return response.json()["embedding"]


# Alias fungsi untuk kompatibilitas
generate_embedding = get_embedding


def search_documents(
    query: str,
    top_k: int | None = None,
    min_score: float | None = None,
) -> list[dict]:
    """Mencari dokumen skripsi paling relevan berdasarkan Cosine Similarity (<=>)."""
    if top_k is None:
        top_k = settings.TOP_K_RESULTS
    if min_score is None:
        min_score = settings.SIMILARITY_THRESHOLD

    query_embedding = get_embedding(query)

    with get_db_session() as conn:
        with conn.cursor() as cur:
            sql = """
                SELECT id, judul, konten, 1 - (embedding <=> %s::vector) AS score
                FROM skripsi_dokumen
                WHERE 1 - (embedding <=> %s::vector) >= %s
                ORDER BY embedding <=> %s::vector ASC
                LIMIT %s;
            """
            cur.execute(sql, (query_embedding, query_embedding, min_score, query_embedding, top_k))
            rows = cur.fetchall()

            # Fallback jika threshold terlalu ketat dan tidak ada hasil
            if not rows:
                fallback_sql = """
                    SELECT id, judul, konten, 1 - (embedding <=> %s::vector) AS score
                    FROM skripsi_dokumen
                    ORDER BY embedding <=> %s::vector ASC
                    LIMIT %s;
                """
                cur.execute(fallback_sql, (query_embedding, query_embedding, top_k))
                rows = cur.fetchall()

            results = []
            for row in rows:
                results.append({
                    "id": row[0],
                    "judul": row[1],
                    "konten": row[2],
                    "score": float(row[3]),
                })
            return results


__all__ = ["get_embedding", "generate_embedding", "search_documents"]
