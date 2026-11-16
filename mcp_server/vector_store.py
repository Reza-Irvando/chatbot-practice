import logging
import math
import re
import sys
import time
from collections import Counter
from pathlib import Path
from google import genai

# Pastikan Direktori mcp_server dan root terdaftar di sys.path
MCP_DIR = Path(__file__).resolve().parent
ROOT_DIR = MCP_DIR.parent
for p in (str(MCP_DIR), str(ROOT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from mcp_server.config import settings
except ModuleNotFoundError:
    from config import settings  # type: ignore[import-not-found]

logger = logging.getLogger("mcp_vector_store")

# Stopwords domain perundang-undangan yang tidak membedakan topik antar pasal
DOMAIN_STOPWORDS = {
    "data", "pribadi", "pelindungan", "uu", "pdp", "nomor", "tahun", "2022", "27",
    "republik", "indonesia", "yang", "dan", "atau", "oleh", "pada", "untuk", "dengan",
    "adalah", "menurut", "dalam", "sebutkan", "jelaskan", "bagaimana", "apakah",
    "siapa", "kapan", "dimana", "mengapa", "apa", "saja", "tentang", "atas", "bagi",
    "secara", "dari", "ke", "di", "itu", "ini", "tersebut", "berdasarkan",
}

_PDF_CHUNKS_CACHE: list[dict] | None = None


def _get_genai_client() -> genai.Client:
    """Membuat client Google GenAI resmi menggunakan GEMINI_API_KEY."""
    settings.reload()
    api_key = (settings.GEMINI_API_KEY or "").strip()
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY belum dikonfigurasi di mcp_server/.env untuk membuat embedding Gemini."
        )
    return genai.Client(api_key=api_key)


def get_embeddings_batch(texts: list[str], batch_size: int = 20) -> list[list[float]]:
    """
    Menghasilkan vektor embedding batch menggunakan Google Gemini (gemini-embedding-001)
    dengan auto-retry bila terkena rate-limit (429 RESOURCE_EXHAUSTED).
    """
    if not texts:
        return []

    client = _get_genai_client()
    all_vectors: list[list[float]] = []

    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        max_attempts = 4
        for attempt in range(1, max_attempts + 1):
            try:
                resp = client.models.embed_content(
                    model=settings.EMBEDDING_MODEL or "gemini-embedding-001",
                    contents=batch,
                    config={"output_dimensionality": settings.EMBED_DIMENSION},
                )
                all_vectors.extend([list(emb.values) for emb in (resp.embeddings or [])])
                break
            except Exception as exc:
                err_str = str(exc)
                if ("429" in err_str or "RESOURCE_EXHAUSTED" in err_str) and attempt < max_attempts:
                    delay_match = re.search(r"retry in (\d+(?:\.\d+)?)s", err_str, re.IGNORECASE)
                    wait_sec = float(delay_match.group(1)) + 2.0 if delay_match else 22.0
                    logger.warning(
                        "[RATE-LIMIT] Kuota embedding Gemini tercapai. Menunggu %.1f detik...",
                        wait_sec,
                    )
                    time.sleep(wait_sec)
                else:
                    raise

    return all_vectors


def get_embedding(text: str) -> list[float]:
    """Mengambil vektor embedding tunggal dari Google Gemini Embedding API."""
    vectors = get_embeddings_batch([text], batch_size=1)
    if not vectors:
        raise RuntimeError("Gemini Embedding API tidak mengembalikan vektor.")
    return vectors[0]


generate_embedding = get_embedding


def _deteksi_nomor_pasal(query: str) -> list[str]:
    """Mendeteksi penyebutan nomor pasal spesifik dalam query (Pasal 1 s.d. 76)."""
    matches = re.findall(r"\b(?:pasal|pasal\s+ke-?)\s*(\d+)\b", query, re.IGNORECASE)
    return list(dict.fromkeys(matches))


def _tokenize_meaningful(text: str) -> list[str]:
    tokens = re.findall(r"\b[a-zA-Z0-9_-]+\b", text.lower())
    meaningful = [t for t in tokens if len(t) >= 3 and t not in DOMAIN_STOPWORDS]
    if not meaningful:
        meaningful = [t for t in tokens if len(t) >= 2]
    return meaningful


def _ekstrak_kata_kunci_fts(query: str) -> str:
    tokens = _tokenize_meaningful(query)
    return " | ".join(tokens) if tokens else ""


def _load_pdf_chunks_cache() -> list[dict]:
    """Memuat dan men-cache chunk naskah resmi UU PDP langsung dari file PDF."""
    global _PDF_CHUNKS_CACHE
    if _PDF_CHUNKS_CACHE is not None:
        return _PDF_CHUNKS_CACHE

    try:
        from mcp_server.ingest_uupdp import (
            bersihkan_teks_hukum,
            ekstrak_teks_pdf,
            segmentasikan_uu_pdp,
        )
    except ModuleNotFoundError:
        from ingest_uupdp import (  # type: ignore[import-not-found]
            bersihkan_teks_hukum,
            ekstrak_teks_pdf,
            segmentasikan_uu_pdp,
        )

    pdf_path = settings.PDF_PATH
    if not Path(pdf_path).exists():
        logger.warning("File PDF UU PDP tidak ditemukan di %s", pdf_path)
        _PDF_CHUNKS_CACHE = []
        return _PDF_CHUNKS_CACHE

    teks_mentah = ekstrak_teks_pdf(pdf_path)
    teks_bersih = bersihkan_teks_hukum(teks_mentah)
    raw_chunks = segmentasikan_uu_pdp(teks_bersih)

    indexed: list[dict] = []
    for idx, c in enumerate(raw_chunks, 1):
        header_text = f"{c.get('judul', '')} {c.get('bab', '')} {c.get('pasal', '')}"
        konten_text = c.get("konten", "")
        indexed.append({
            "id": idx,
            "judul": c.get("judul", "UU No. 27/2022"),
            "bab": c.get("bab", ""),
            "pasal": c.get("pasal", ""),
            "kategori": c.get("kategori", "Batang Tubuh"),
            "konten": konten_text,
            "metadata": {"source": "pdf_in_memory", "chunk_id": idx},
            "_header_tokens": set(re.findall(r"\b[a-zA-Z0-9_-]+\b", header_text.lower())),
            "_body_counts": Counter(re.findall(r"\b[a-zA-Z0-9_-]+\b", konten_text.lower())),
        })

    _PDF_CHUNKS_CACHE = indexed
    return _PDF_CHUNKS_CACHE


def _search_in_memory_pdf(query: str, top_k: int) -> list[dict]:
    """Pencarian leksikal berbobot di atas chunk PDF UU PDP saat pgvector tidak aktif."""
    chunks = _load_pdf_chunks_cache()
    if not chunks:
        return []

    query_tokens = _tokenize_meaningful(query)
    explicit_pasals = _deteksi_nomor_pasal(query)
    n_docs = len(chunks)

    df: dict[str, int] = {}
    for tok in set(query_tokens):
        df[tok] = sum(1 for c in chunks if tok in c["_body_counts"] or tok in c["_header_tokens"])

    scored: list[dict] = []
    for c in chunks:
        score = 0.0
        for tok in query_tokens:
            idf = math.log((n_docs + 1.0) / (df.get(tok, 0) + 1.0)) + 0.5
            tf_body = c["_body_counts"].get(tok, 0)
            if tf_body > 0:
                score += (1.0 + math.log(tf_body)) * idf
            if tok in c["_header_tokens"]:
                score += 1.5 * idf

        pasal_str = c.get("pasal", "")
        if explicit_pasals:
            for ep in explicit_pasals:
                if re.search(rf"\bPasal\s+{re.escape(ep)}\b", pasal_str, re.IGNORECASE):
                    score += 10.0

        if score > 0:
            scored.append({
                "id": c["id"],
                "judul": c["judul"],
                "bab": c["bab"],
                "pasal": pasal_str,
                "kategori": c["kategori"],
                "konten": c["konten"],
                "metadata": c["metadata"],
                "score": float(score),
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    top = scored[:top_k]
    if top:
        max_s = max(r["score"] for r in top) or 1.0
        if max_s > 1.0:
            for r in top:
                r["score"] = round(min(0.99, 0.5 + 0.45 * (r["score"] / max_s)), 4)
    return top


def search_documents(
    query: str,
    top_k: int | None = None,
    min_score: float | None = None,
) -> list[dict]:
    """
    Pencarian hybrid (pgvector + PostgreSQL FTS RRF) pada UU PDP dengan fallback
    otomatis ke pencarian langsung naskah PDF apabila DB pgvector/Gemini belum terisi.
    """
    if top_k is None:
        top_k = settings.TOP_K_RESULTS
    if min_score is None:
        min_score = settings.SIMILARITY_THRESHOLD

    try:
        try:
            from mcp_server.db import get_db_session
        except ModuleNotFoundError:
            from db import get_db_session  # type: ignore[import-not-found]

        table_name = settings.DOC_TABLE_NAME
        explicit_pasals = _deteksi_nomor_pasal(query)
        fts_query_str = _ekstrak_kata_kunci_fts(query)
        query_embedding = get_embedding(query)

        vec_map: dict[int, dict] = {}
        fts_map: dict[int, dict] = {}

        with get_db_session() as conn:
            with conn.cursor() as cur:
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

        all_doc_ids = set(vec_map.keys()) | set(fts_map.keys())
        k_constant = 60
        fused_results: list[dict] = []

        for doc_id in all_doc_ids:
            r_vec = vec_map[doc_id]["rank_vec"] if doc_id in vec_map else 60
            r_fts = fts_map[doc_id]["rank_fts"] if doc_id in fts_map else 60
            rrf_score = (1.0 / (k_constant + r_vec)) + (1.2 / (k_constant + r_fts))

            base_info = vec_map.get(doc_id) or fts_map.get(doc_id)
            row = base_info["row"]
            pasal_str = row[3] or ""

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

        fused_results.sort(key=lambda x: x["score"], reverse=True)
        if fused_results:
            return fused_results[:top_k]

    except Exception as exc:
        logger.info("pgvector/Gemini embedding belum aktif (%s), beralih ke pencarian PDF lokal.", exc)

    return _search_in_memory_pdf(query, top_k=top_k)


def format_search_results(results: list[dict]) -> str:
    """Memformat daftar hasil pencarian menjadi teks terstruktur untuk LLM / MCP."""
    if not results:
        return "Tidak ditemukan pasal atau ketentuan terkait dalam UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi."

    formatted = []
    for r in results:
        label_bagian = f"{r.get('bab', '')} - {r.get('pasal', '')}".strip(" -")
        if not label_bagian:
            label_bagian = r.get("judul", "UU No. 27/2022")
        kategori = r.get("kategori", "Batang Tubuh")
        formatted.append(
            f"[UU PDP No. 27/2022 - {label_bagian} ({kategori})] (Skor Relevansi: {r['score']:.2f}):\n"
            f"{r['konten']}"
        )
    return "\n\n---\n\n".join(formatted)


__all__ = [
    "get_embedding",
    "get_embeddings_batch",
    "generate_embedding",
    "search_documents",
    "format_search_results",
]
