import json
import re
import sys
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

# Pastikan root direktori terdaftar di sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import settings
from mcp_server.db import get_connection, release_connection
from mcp_server.vector_store import generate_embedding

PDF_PATH = ROOT_DIR / "docs" / "skripsi_svm.pdf"


def bersihkan_teks(teks: str) -> str:
    """Membersihkan whitespace ganjil dan baris terputus akibat format PDF."""
    teks = re.sub(r"\s+", " ", teks)  # Gabung whitespace berlebih
    teks = teks.replace(" - ", "")    # Perbaiki tanda pisah kata
    return teks.strip()


def baca_dan_filter_pdf(file_path: Path | str) -> list[dict]:
    path_obj = Path(file_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"File skripsi tidak ditemukan di: {path_obj}")

    reader = PdfReader(str(path_obj))
    total_pages = len(reader.pages)
    pages_data = []

    print(f"[INGEST] Membaca file PDF ({total_pages} halaman)...")

    # Lewati halaman awal jika perlu (di sini membaca seluruh halaman yang memiliki konten memadai)
    for idx, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text:
            continue

        clean_text = bersihkan_teks(text)

        # Abaikan halaman yang terlalu pendek (biasanya halaman kosong atau lembar pemisah)
        if len(clean_text) < 100:
            continue

        pages_data.append({
            "page_number": idx + 1,
            "text": clean_text,
        })

    return pages_data


def proses_dan_simpan_skripsi():
    pages = baca_dan_filter_pdf(PDF_PATH)

    # Chunking lebih luas untuk mempertahankan konteks paragraf akademis
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1200,
        chunk_overlap=200,
        separators=["\n\n", "\n", ". ", "; ", " ", ""],
    )

    chunks = []
    for item in pages:
        sub_chunks = splitter.split_text(item["text"])
        for chunk_idx, text_chunk in enumerate(sub_chunks):
            # Context Enrichment: metadata halaman disuntikkan ke teks konten
            konten_terkaya = (
                f"[Sumber: Skripsi Klasifikasi Vegetasi SVM UAV - Halaman {item['page_number']}]\n"
                f"{text_chunk}"
            )

            chunks.append({
                "halaman": item["page_number"],
                "chunk_id": chunk_idx + 1,
                "konten": konten_terkaya,
            })

    print(f"[INGEST] Total potongan chunk berkualitas: {len(chunks)}")

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            print("[INGEST] Mengosongkan tabel lama...")
            cur.execute("TRUNCATE TABLE skripsi_dokumen RESTART IDENTITY;")
            conn.commit()

            print(f"[INGEST] Mulai generate embedding ({settings.EMBEDDING_MODEL}) ke pgvector...")
            for idx, c in enumerate(chunks, 1):
                judul = f"Skripsi SVM - Halaman {c['halaman']} (Bagian {c['chunk_id']})"
                metadata = {
                    "halaman": c["halaman"],
                    "chunk": c["chunk_id"],
                }

                vec = generate_embedding(c["konten"])

                cur.execute(
                    """
                    INSERT INTO skripsi_dokumen (judul, konten, embedding, metadata)
                    VALUES (%s, %s, %s, %s);
                    """,
                    (judul, c["konten"], vec, json.dumps(metadata)),
                )

                if idx % 10 == 0 or idx == len(chunks):
                    print(f" -> Terproses {idx}/{len(chunks)} chunks...")
                    conn.commit()

            print("\n[SUKSES] Seluruh isi naskah skripsi telah di-indeks ulang dengan chunking baru!")
    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Gagal proses ingest: {e}")
    finally:
        release_connection(conn)


if __name__ == "__main__":
    proses_dan_simpan_skripsi()
