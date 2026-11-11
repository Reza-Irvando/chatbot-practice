import re
import sys
from pathlib import Path
import requests

# Pastikan Root Direktori terdaftar di sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import settings
from mcp_server.db import get_db_session

# Stopwords domain perundang-undangan (kata-kata umum yang ada di hampir seluruh pasal
# sehingga tidak memiliki daya pembeda topik dalam pencarian leksikal teks)
DOMAIN_STOPWORDS = {
    "data", "pribadi", "pelindungan", "uu", "pdp", "nomor", "tahun", "2022", "27",
    "republik", "indonesia", "yang", "dan", "atau", "oleh", "pada", "untuk", "dengan",
    "adalah", "menurut", "dalam", "sebutkan", "jelaskan", "bagaimana", "apakah",
    "siapa", "kapan", "dimana", "mengapa", "apa", "saja", "tentang", "atas", "bagi", "secara"
}


def get_embedding(text: str) -> list[float]:
    """Mengambil vektor embedding dari Ollama (model embedding terkonfigurasi)."""
    url = f"{settings.OLLAMA_BASE_URL}/api/embeddings"
    payload = {
        "model": settings.EMBEDDING_MODEL,
        "prompt": text,
    }
    response = requests.post(url, json=payload, timeout=45)
    response.raise_for_status()
    return response.json()["embedding"]


# Alias fungsi untuk kompatibilitas
generate_embedding = get_embedding


def _deteksi_nomor_pasal(query: str) -> list[str]:
    """
    Parser sintaksis umum untuk mendeteksi penyebutan nomor pasal spesifik
    dalam query pengguna (misal: 'Pasal 15', 'pasal 46 ayat 1', 'pasal 67').
    Berlaku seragam untuk seluruh pasal (Pasal 1 s.d. 76).
    """
    pattern = r"\b(?:pasal|pasal\s+ke-?)\s*(\d+)\b"
    matches = re.findall(pattern, query, re.IGNORECASE)
    return list(dict.fromkeys(matches))


def _ekstrak_kata_kunci_fts(query: str) -> str:
    """
    Mengekstrak kata kunci diskriminatif untuk pencarian Full-Text Search (tsvector),
    mengabaikan stopwords umum dan stopwords domain.
    """
    tokens = re.findall(r"\b[a-zA-Z0-9_-]+\b", query.lower())
    meaningful = [t for t in tokens if len(t) >= 3 and t not in DOMAIN_STOPWORDS]
    if not meaningful:
        meaningful = [t for t in tokens if len(t) >= 2]
    return " | ".join(meaningful) if meaningful else ""


def search_documents(
    query: str,
    top_k: int | None = None,
    min_score: float | None = None,
) -> list[dict]:
    """
    Pencarian dokumen UU Perlindungan Data Pribadi secara sistemis & menyeluruh menggunakan:
    1. Weighted Lexical Full-Text Search (PostgreSQL tsvector & ts_rank_cd):
       Memberikan bobot tinggi ('A') pada Judul & BAB, dan bobot ('D') pada Konten.
    2. Dense Vector Semantic Search (pgvector Cosine Distance):
       Memahami makna kontekstual, sinonim, dan bahasa alami pengguna.
    3. Reciprocal Rank Fusion (RRF):
       Menggabungkan skor secara matematis tanpa hardcode aturan/kata kunci.
    4. Exact Article Priority:
       Memprioritaskan pasal jika pengguna eksplisit menyebut nomor pasal tertentu.
    """
    if top_k is None:
        top_k = settings.TOP_K_RESULTS
    if min_score is None:
        min_score = settings.SIMILARITY_THRESHOLD

    table_name = settings.DOC_TABLE_NAME
    explicit_pasals = _deteksi_nomor_pasal(query)
    fts_query_str = _ekstrak_kata_kunci_fts(query)
    query_embedding = get_embedding(query)

    vec_map: dict[int, dict] = {}
    fts_map: dict[int, dict] = {}

    with get_db_session() as conn:
        with conn.cursor() as cur:
            # 1. DENSE VECTOR RETRIEVAL (Kandidat Semantik)
            semantic_sql = f"""
                SELECT id, judul, bab, pasal, kategori, konten, metadata,
                       ROW_NUMBER() OVER (ORDER BY embedding <=> %s::vector ASC) as rank_vec,
                       1 - (embedding <=> %s::vector) as sim_score
                FROM {table_name}
                ORDER BY embedding <=> %s::vector ASC
                LIMIT 30;
            """
            cur.execute(semantic_sql, (query_embedding, query_embedding, query_embedding))
            for row in cur.fetchall():
                vec_map[row[0]] = {
                    "row": row,
                    "rank_vec": int(row[7]),
                    "sim_score": float(row[8]),
                }

            # 2. WEIGHTED LEXICAL FULL-TEXT SEARCH (Kandidat Leksikal Berbobot Judul & BAB)
            if fts_query_str:
                fts_sql = f"""
                    SELECT id, judul, bab, pasal, kategori, konten, metadata,
                           ROW_NUMBER() OVER (
                               ORDER BY ts_rank_cd(
                                   setweight(to_tsvector('simple', coalesce(judul, '') || ' ' || coalesce(bab, '')), 'A') ||
                                   setweight(to_tsvector('simple', coalesce(konten, '')), 'D'),
                                   to_tsquery('simple', %s)
                               ) DESC
                           ) as rank_fts,
                           ts_rank_cd(
                               setweight(to_tsvector('simple', coalesce(judul, '') || ' ' || coalesce(bab, '')), 'A') ||
                               setweight(to_tsvector('simple', coalesce(konten, '')), 'D'),
                               to_tsquery('simple', %s)
                           ) as fts_score
                    FROM {table_name}
                    WHERE (
                        setweight(to_tsvector('simple', coalesce(judul, '') || ' ' || coalesce(bab, '')), 'A') ||
                        setweight(to_tsvector('simple', coalesce(konten, '')), 'D')
                    ) @@ to_tsquery('simple', %s)
                    LIMIT 30;
                """
                cur.execute(fts_sql, (fts_query_str, fts_query_str, fts_query_str))
                for row in cur.fetchall():
                    fts_map[row[0]] = {
                        "row": row,
                        "rank_fts": int(row[7]),
                        "fts_score": float(row[8]),
                    }

    # 3. RECIPROCAL RANK FUSION (RRF) - Skor Matematis Terpadu
    all_doc_ids = set(vec_map.keys()) | set(fts_map.keys())
    k_constant = 60
    fused_results: list[dict] = []

    for doc_id in all_doc_ids:
        r_vec = vec_map[doc_id]["rank_vec"] if doc_id in vec_map else 60
        r_fts = fts_map[doc_id]["rank_fts"] if doc_id in fts_map else 60

        # Formula RRF standar industri dengan bobot leksikal judul 1.2
        rrf_score = (1.0 / (k_constant + r_vec)) + (1.2 / (k_constant + r_fts))

        base_info = vec_map.get(doc_id) or fts_map.get(doc_id)
        row = base_info["row"]
        pasal_str = row[3] or ""

        # Prioritas deterministik jika pengguna menyebut angka pasal tertentu
        if explicit_pasals:
            for ep in explicit_pasals:
                if f"Pasal {ep}" in pasal_str:
                    rrf_score += 2.0

        fused_results.append({
            "id": doc_id,
            "judul": row[1],
            "bab": row[2] or "",
            "pasal": pasal_str,
            "kategori": row[4] or "Batang Tubuh",
            "konten": row[5],
            "metadata": row[6] or {},
            "score": float(rrf_score),
        })

    # Urutkan berdasarkan skor fusi tertinggi
    fused_results.sort(key=lambda x: x["score"], reverse=True)
    return fused_results[:top_k]


__all__ = ["get_embedding", "generate_embedding", "search_documents"]
