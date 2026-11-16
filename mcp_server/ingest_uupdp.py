import binascii
import json
import re
import sys
from pathlib import Path

MCP_DIR = Path(__file__).resolve().parent
ROOT_DIR = MCP_DIR.parent
for p in (str(MCP_DIR), str(ROOT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    from mcp_server.config import settings
except ModuleNotFoundError:
    from config import settings  # type: ignore[import-not-found]

BAB_LIST = [
    ("BAB I", "KETENTUAN UMUM"),
    ("BAB II", "ASAS DAN TUJUAN"),
    ("BAB III", "JENIS DATA PRIBADI"),
    ("BAB IV", "HAK SUBJEK DATA PRIBADI"),
    ("BAB V", "PEMROSESAN DATA PRIBADI"),
    ("BAB VI", "KEWAJIBAN PENGENDALI DATA PRIBADI DAN PROSESOR DATA PRIBADI"),
    ("BAB VII", "TRANSFER DATA PRIBADI"),
    ("BAB VIII", "SANKSI ADMINISTRATIF"),
    ("BAB IX", "KELEMBAGAAN"),
    ("BAB X", "KERJA SAMA INTERNASIONAL"),
    ("BAB XI", "PARTISIPASI MASYARAKAT"),
    ("BAB XII", "PENYELESAIAN SENGKETA DAN HUKUM ACARA"),
    ("BAB XIII", "LARANGAN DALAM PENGGUNAAN DATA PRIBADI"),
    ("BAB XIV", "KETENTUAN PIDANA"),
    ("BAB XV", "KETENTUAN PERALIHAN"),
    ("BAB XVI", "KETENTUAN PENUTUP"),
]

BAB_ARTICLE_RANGES = {
    "BAB I": (1, 2),
    "BAB II": (3, 3),
    "BAB III": (4, 4),
    "BAB IV": (5, 15),
    "BAB V": (16, 18),
    "BAB VI": (19, 54),
    "BAB VII": (55, 56),
    "BAB VIII": (57, 57),
    "BAB IX": (58, 61),
    "BAB X": (62, 62),
    "BAB XI": (63, 63),
    "BAB XII": (64, 64),
    "BAB XIII": (65, 66),
    "BAB XIV": (67, 73),
    "BAB XV": (74, 75),
    "BAB XVI": (76, 76),
}


def ekstrak_teks_pdf(file_path: Path | str) -> str:
    """Mengekstrak teks dari PDF menggunakan pypdf atau parser hex-stream internal."""
    path_obj = Path(file_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"File PDF UU PDP tidak ditemukan di: {path_obj}")

    try:
        import importlib
        pypdf = importlib.import_module("pypdf")
        PdfReader = getattr(pypdf, "PdfReader")
        reader = PdfReader(str(path_obj))
        pages_text = [t for page in reader.pages if (t := page.extract_text())]
        if pages_text and len(" ".join(pages_text)) > 5000:
            return " ".join(pages_text)
    except Exception:
        pass

    with open(path_obj, "rb") as f:
        data = f.read()

    tokens = []
    for m in re.finditer(rb"<([0-9A-Fa-f]+)>\s*Tj", data):
        try:
            decoded = binascii.unhexlify(m.group(1).decode("ascii")).decode("utf-8", errors="ignore")
            tokens.append(decoded)
        except Exception:
            pass

    return " ".join(tokens)


def bersihkan_teks_hukum(teks: str) -> str:
    """Membersihkan artefak OCR cetakan Sekretariat Negara dan normalisasi karakter."""
    teks = re.sub(r"[ \t]+", " ", teks)
    teks = teks.replace(" - ", "")

    teks = re.sub(r"Pasa[l7I1]\s*(\d+)", r"Pasal \1", teks)
    teks = re.sub(r"Pasa7(\d+)", r"Pasal \1", teks)
    teks = re.sub(r"Pasal\s+I\b", "Pasal 1", teks)
    teks = re.sub(r"Pasal\s+T(\d+)", r"Pasal 7\1", teks)
    teks = re.sub(r"Pasal\s+(\d+)O\b", r"Pasal \g<1>0", teks)
    teks = re.sub(r"Pasal\s+2T\b", "Pasal 27", teks)
    teks = re.sub(r"Pasal\s+(\d+)T\b", r"Pasal \g<1>7", teks)
    teks = re.sub(r"Pa6al\s*(\d+)", r"Pasal \1", teks)

    teks = re.sub(r"\bBAB\s+xI\b", "BAB XI", teks)
    teks = re.sub(r"\bBAB\s+xII\b", "BAB XII", teks)
    teks = re.sub(r"I,ARANGAN", "LARANGAN", teks)
    teks = re.sub(r"PEI\{YELESAI,AN", "PENYELESAIAN", teks)
    teks = re.sub(r"PEI\{YELESAIAN", "PENYELESAIAN", teks)
    teks = re.sub(r"PENYELESAI,AN", "PENYELESAIAN", teks)
    teks = re.sub(r"DAI,AM", "DALAM", teks)

    teks = re.sub(r"SK\s+No\s+[0-9A-Za-z]+", "", teks)
    teks = re.sub(r"PRESIDEN\s+REPUBLIK\s+INDONESIA\s*-\s*\d+\s*-", "", teks)
    teks = re.sub(r"PRESlDEN\s+REPUBLIK\s+INOONESIA", "", teks)
    teks = re.sub(r"PRESIDEN\s+REPUBLIK\s+INDONESIA", "", teks)
    teks = re.sub(r"TAMBAHAN\s+LEMBARAN\s+NEGARA\s+REPUBLIK\s+INDONESIA\s+NOMOR\s+\d+", "", teks)

    return re.sub(r"\s+", " ", teks).strip()


def _make_chunk(judul: str, bab: str, pasal: str, kategori: str, konten: str) -> dict:
    return {
        "judul": judul,
        "bab": bab,
        "pasal": pasal,
        "kategori": kategori,
        "konten": konten,
    }


def segmentasikan_uu_pdp(teks_bersih: str) -> list[dict]:
    """Mensegmentasikan teks UU PDP menjadi chunk terstruktur per BAB, Pasal, dan Penjelasan."""
    chunk_size = int(getattr(settings, "CHUNK_SIZE", 1000))
    penanda_penjelasan = "Perumusan aturan tentang Pelindungan Data Pribadi dapat dipahami"
    idx_penjelasan = teks_bersih.find(penanda_penjelasan)

    if idx_penjelasan != -1:
        teks_batang_tubuh = teks_bersih[:idx_penjelasan].strip()
        teks_penjelasan = teks_bersih[idx_penjelasan:].strip()
    else:
        teks_batang_tubuh = teks_bersih
        teks_penjelasan = ""

    chunks: list[dict] = []
    bab_spans = []
    for b_id, b_title in BAB_LIST:
        m = re.search(rf"\b{b_id}\b", teks_batang_tubuh)
        if m:
            bab_spans.append((m.start(), b_id, b_title))
    bab_spans.sort()

    for idx, (start_pos, b_id, b_title) in enumerate(bab_spans):
        end_pos = bab_spans[idx + 1][0] if idx + 1 < len(bab_spans) else len(teks_batang_tubuh)
        bab_content = teks_batang_tubuh[start_pos:end_pos].strip()
        label_bab = f"{b_id} {b_title}"
        start_article, end_article = BAB_ARTICLE_RANGES.get(b_id, (1, 76))

        if len(bab_content) <= 4000:
            chunks.append(
                _make_chunk(
                    f"UU No. 27/2022 - {label_bab} (Teks Lengkap)",
                    label_bab,
                    f"Pasal {start_article} s.d. {end_article}",
                    "Batang Tubuh (Bab Utuh)",
                    (
                        f"[Dokumen: UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi]\n"
                        f"[Bagian: {label_bab} (Pasal {start_article} s.d. Pasal {end_article})]\n\n"
                        f"{bab_content}"
                    ),
                )
            )
        else:
            bagian_spans = list(re.finditer(r"(Bagian\s+[A-Za-z]+)", bab_content))
            for b_i, b_match in enumerate(bagian_spans):
                b_start = b_match.start()
                b_end = bagian_spans[b_i + 1].start() if b_i + 1 < len(bagian_spans) else len(bab_content)
                sub_bab_text = bab_content[b_start:b_end].strip()
                sub_label = b_match.group(1)

                if len(sub_bab_text) <= 3000:
                    chunks.append(
                        _make_chunk(
                            f"UU No. 27/2022 - {label_bab} - {sub_label}",
                            label_bab,
                            sub_label,
                            "Batang Tubuh (Bagian)",
                            (
                                f"[Dokumen: UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi]\n"
                                f"[Bagian: {label_bab} - {sub_label}]\n\n"
                                f"{sub_bab_text}"
                            ),
                        )
                    )
                else:
                    words = sub_bab_text.split(" ")
                    cur_w_block = []
                    w_idx = 1
                    for w in words:
                        cur_w_block.append(w)
                        if len(" ".join(cur_w_block)) >= 2500:
                            chunk_txt = " ".join(cur_w_block).strip()
                            chunks.append(
                                _make_chunk(
                                    f"UU No. 27/2022 - {label_bab} - {sub_label} (Bagian {w_idx})",
                                    label_bab,
                                    f"{sub_label} ({w_idx})",
                                    "Batang Tubuh (Bagian)",
                                    (
                                        f"[Dokumen: UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi]\n"
                                        f"[Bagian: {label_bab} - {sub_label} (Bagian {w_idx})]\n\n"
                                        f"{chunk_txt}"
                                    ),
                                )
                            )
                            w_idx += 1
                            cur_w_block = []
                    if cur_w_block:
                        chunk_txt = " ".join(cur_w_block).strip()
                        chunks.append(
                            _make_chunk(
                                f"UU No. 27/2022 - {label_bab} - {sub_label} (Bagian {w_idx})",
                                label_bab,
                                f"{sub_label} ({w_idx})",
                                "Batang Tubuh (Bagian)",
                                (
                                    f"[Dokumen: UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi]\n"
                                    f"[Bagian: {label_bab} - {sub_label} (Bagian {w_idx})]\n\n"
                                    f"{chunk_txt}"
                                ),
                            )
                        )

        article_matches = []
        expected_art = start_article
        for m in re.finditer(r"\bPasal\s+(\d+)\b", bab_content):
            val = int(m.group(1))
            if val == expected_art:
                article_matches.append((val, m.start()))
                expected_art += 1
                if expected_art > end_article:
                    break

        if not article_matches:
            for m in re.finditer(r"\bPasal\s+(\d+)\b", bab_content):
                val = int(m.group(1))
                if start_article <= val <= end_article:
                    article_matches.append((val, m.start()))

        if not article_matches:
            chunks.append(
                _make_chunk(
                    f"UU No. 27/2022 - {label_bab}",
                    label_bab,
                    "",
                    "Batang Tubuh",
                    (
                        f"[Dokumen: UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi]\n"
                        f"[Bagian: {label_bab}]\n\n"
                        f"{bab_content}"
                    ),
                )
            )
            continue

        for p_idx, (p_num, p_start) in enumerate(article_matches):
            p_end = article_matches[p_idx + 1][1] if p_idx + 1 < len(article_matches) else len(bab_content)
            article_text = bab_content[p_start:p_end].strip()
            label_pasal = f"Pasal {p_num}"

            if len(article_text) > chunk_size:
                sub_parts = re.split(r"(?=\(\d+\)\s+|(?<=\.\s)(?=[A-Z0-9]))", article_text)
                cur_block = ""
                sub_idx = 1
                for part in sub_parts:
                    if len(cur_block) + len(part) <= chunk_size:
                        cur_block += " " + part
                    else:
                        if cur_block.strip():
                            chunks.append(
                                _make_chunk(
                                    f"UU No. 27/2022 - {label_bab} - {label_pasal} (Bagian {sub_idx})",
                                    label_bab,
                                    label_pasal,
                                    "Batang Tubuh",
                                    (
                                        f"[Dokumen: UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi]\n"
                                        f"[Bagian: {label_bab}]\n"
                                        f"[{label_pasal} (Bagian {sub_idx})]\n\n"
                                        f"{cur_block.strip()}"
                                    ),
                                )
                            )
                            sub_idx += 1
                        cur_block = part
                if cur_block.strip():
                    chunks.append(
                        _make_chunk(
                            f"UU No. 27/2022 - {label_bab} - {label_pasal} (Bagian {sub_idx})",
                            label_bab,
                            label_pasal,
                            "Batang Tubuh",
                            (
                                f"[Dokumen: UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi]\n"
                                f"[Bagian: {label_bab}]\n"
                                f"[{label_pasal} (Bagian {sub_idx})]\n\n"
                                f"{cur_block.strip()}"
                            ),
                        )
                    )
            else:
                chunks.append(
                    _make_chunk(
                        f"UU No. 27/2022 - {label_bab} - {label_pasal}",
                        label_bab,
                        label_pasal,
                        "Batang Tubuh",
                        (
                            f"[Dokumen: UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi]\n"
                            f"[Bagian: {label_bab}]\n"
                            f"[{label_pasal}]\n\n"
                            f"{article_text}"
                        ),
                    )
                )

    if teks_penjelasan:
        idx_pdp = teks_penjelasan.upper().find("PASAL DEMI PASAL")
        if idx_pdp != -1:
            penjelasan_umum = teks_penjelasan[:idx_pdp].strip()
            penjelasan_pasal_text = teks_penjelasan[idx_pdp:].strip()
        else:
            penjelasan_umum = teks_penjelasan[:2000].strip()
            penjelasan_pasal_text = teks_penjelasan[2000:].strip()

        chunks.append(
            _make_chunk(
                "UU No. 27/2022 - PENJELASAN UMUM",
                "PENJELASAN",
                "Umum",
                "Penjelasan",
                (
                    "[Dokumen: UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi]\n"
                    "[Bagian: PENJELASAN ATAS UNDANG-UNDANG (UMUM)]\n\n"
                    f"{penjelasan_umum[:1500]}"
                ),
            )
        )

        pj_matches = list(re.finditer(r"\bPasal\s+(\d+)\b", penjelasan_pasal_text))
        for idx, m in enumerate(pj_matches):
            p_num = m.group(1)
            p_start = m.start()
            p_end = pj_matches[idx + 1].start() if idx + 1 < len(pj_matches) else len(penjelasan_pasal_text)
            konten_pj = penjelasan_pasal_text[p_start:p_end].strip()
            label_pasal = f"Pasal {p_num}"
            chunks.append(
                _make_chunk(
                    f"UU No. 27/2022 - Penjelasan {label_pasal}",
                    "PENJELASAN PASAL DEMI PASAL",
                    label_pasal,
                    "Penjelasan",
                    (
                        f"[Dokumen: UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi]\n"
                        f"[Bagian: PENJELASAN PASAL DEMI PASAL]\n"
                        f"[Penjelasan {label_pasal}]\n\n"
                        f"{konten_pj}"
                    ),
                )
            )

    return chunks


def proses_dan_simpan_uupdp():
    """Membaca PDF UU PDP, men-chunk, dan menyimpan vektor embedding Gemini ke pgvector."""
    try:
        from mcp_server.db import get_connection, release_connection
        from mcp_server.vector_store import get_embeddings_batch
    except ModuleNotFoundError:
        from db import get_connection, release_connection  # type: ignore[import-not-found]
        from vector_store import get_embeddings_batch  # type: ignore[import-not-found]

    pdf_file = settings.PDF_PATH
    teks_mentah = ekstrak_teks_pdf(pdf_file)
    teks_bersih = bersihkan_teks_hukum(teks_mentah)
    chunks = segmentasikan_uu_pdp(teks_bersih)
    table_name = settings.DOC_TABLE_NAME

    print(f"[INGEST] Total potongan chunk hukum UU PDP: {len(chunks)}")
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY;")
            conn.commit()

            texts = [c["konten"] for c in chunks]
            print(f"[INGEST] Membuat embedding ({settings.EMBEDDING_MODEL}) via Google Gemini...")
            vectors = get_embeddings_batch(texts, batch_size=20)

            for idx, (c, vec) in enumerate(zip(chunks, vectors), 1):
                metadata = {
                    "bab": c["bab"],
                    "pasal": c["pasal"],
                    "kategori": c["kategori"],
                    "chunk_id": idx,
                }
                cur.execute(
                    f"""
                    INSERT INTO {table_name} (judul, bab, pasal, kategori, konten, embedding, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                    """,
                    (
                        c["judul"],
                        c["bab"],
                        c["pasal"],
                        c["kategori"],
                        c["konten"],
                        vec,
                        json.dumps(metadata),
                    ),
                )
                if idx % 20 == 0 or idx == len(chunks):
                    print(f" -> Tersimpan {idx}/{len(chunks)} chunks...")
                    conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        release_connection(conn)


if __name__ == "__main__":
    proses_dan_simpan_uupdp()
