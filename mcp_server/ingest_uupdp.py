import binascii
import json
import re
import sys
from pathlib import Path

# Pastikan root direktori terdaftar di sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from config.settings import settings

# Definisi seluruh BAB dalam UU No. 27 Tahun 2022
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


def ekstrak_teks_pdf(file_path: Path | str) -> str:
    """Mengekstrak teks dari PDF menggunakan pypdf atau parser hex-stream internal."""
    path_obj = Path(file_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"File PDF UU PDP tidak ditemukan di: {path_obj}")

    # Opsi 1: Coba pypdf jika terpasang (menggunakan dynamic import agar tidak memicu warning linter di IDE)
    try:
        import importlib
        pypdf = importlib.import_module("pypdf")
        PdfReader = getattr(pypdf, "PdfReader")
        reader = PdfReader(str(path_obj))
        pages_text = []
        for page in reader.pages:
            t = page.extract_text()
            if t:
                pages_text.append(t)
        if pages_text and len(" ".join(pages_text)) > 5000:
            print(f"[INGEST] Teks berhasil diekstrak via pypdf ({len(reader.pages)} halaman).")
            return " ".join(pages_text)
    except Exception as e:
        print(f"[INGEST] Note: pypdf tidak aktif atau gagal ({e}), menggunakan parser stream PDF...")

    # Opsi 2: Fallback ke parser stream Tj hex langsung (sangat akurat untuk naskah Setneg OCR)
    with open(path_obj, "rb") as f:
        data = f.read()

    tokens = []
    for m in re.finditer(rb"<([0-9A-Fa-f]+)>\s*Tj", data):
        try:
            decoded = binascii.unhexlify(m.group(1).decode("ascii")).decode("utf-8", errors="ignore")
            tokens.append(decoded)
        except Exception:
            pass

    extracted_text = " ".join(tokens)
    print(f"[INGEST] Teks diekstrak via stream parser ({len(extracted_text)} karakter).")
    return extracted_text


def bersihkan_teks_hukum(teks: str) -> str:
    """Membersihkan artefak OCR pindaian Sekretariat Negara dan normalisasi karakter."""
    # 1. Normalisasi spasi berlebih
    teks = re.sub(r"[ \t]+", " ", teks)

    # 2. Perbaiki tanda pisah kata
    teks = teks.replace(" - ", "")

    # 3. Perbaiki glosarium nomor pasal & bab OCR umum
    teks = re.sub(r"Pasa[l7I1]\s*(\d+)", r"Pasal \1", teks)
    teks = re.sub(r"Pasa7(\d+)", r"Pasal \1", teks)
    teks = re.sub(r"Pasal\s+I\b", "Pasal 1", teks)
    teks = re.sub(r"Pasal\s+T(\d+)", r"Pasal 7\1", teks)
    teks = re.sub(r"Pasal\s+(\d+)O\b", r"Pasal \g<1>0", teks)
    teks = re.sub(r"Pasal\s+2T\b", "Pasal 27", teks)
    teks = re.sub(r"Pasal\s+(\d+)T\b", r"Pasal \g<1>7", teks)
    teks = re.sub(r"Pa6al\s*(\d+)", r"Pasal \1", teks)

    # Normalisasi ejaan BAB OCR
    teks = re.sub(r"\bBAB\s+xI\b", "BAB XI", teks)
    teks = re.sub(r"\bBAB\s+xII\b", "BAB XII", teks)
    teks = re.sub(r"I,ARANGAN", "LARANGAN", teks)
    teks = re.sub(r"PEI\{YELESAI,AN", "PENYELESAIAN", teks)
    teks = re.sub(r"PEI\{YELESAIAN", "PENYELESAIAN", teks)
    teks = re.sub(r"PENYELESAI,AN", "PENYELESAIAN", teks)
    teks = re.sub(r"DAI,AM", "DALAM", teks)

    # 4. Hapus header & footer cetakan naskah Setneg
    teks = re.sub(r"SK\s+No\s+[0-9A-Za-z]+", "", teks)
    teks = re.sub(r"PRESIDEN\s+REPUBLIK\s+INDONESIA\s*-\s*\d+\s*-", "", teks)
    teks = re.sub(r"PRESlDEN\s+REPUBLIK\s+INOONESIA", "", teks)
    teks = re.sub(r"PRESIDEN\s+REPUBLIK\s+INDONESIA", "", teks)
    teks = re.sub(r"TAMBAHAN\s+LEMBARAN\s+NEGARA\s+REPUBLIK\s+INDONESIA\s+NOMOR\s+\d+", "", teks)

    return re.sub(r"\s+", " ", teks).strip()


def segmentasikan_uu_pdp(teks_bersih: str) -> list[dict]:
    """
    Mensegmentasikan teks UU PDP menjadi bagian terstruktur (Batang Tubuh & Penjelasan)
    dan melakukan chunking per Pasal / Ayat dengan Context Enrichment.
    """
    # 1. Pisahkan Batang Tubuh dan Bagian Penjelasan
    penanda_penjelasan = "Perumusan aturan tentang Pelindungan Data Pribadi dapat dipahami"
    idx_penjelasan = teks_bersih.find(penanda_penjelasan)

    if idx_penjelasan != -1:
        teks_batang_tubuh = teks_bersih[:idx_penjelasan].strip()
        teks_penjelasan = teks_bersih[idx_penjelasan:].strip()
    else:
        teks_batang_tubuh = teks_bersih
        teks_penjelasan = ""

    chunks: list[dict] = []

    # 2. Parsing BAB Batang Tubuh
    bab_spans = []
    for b_id, b_title in BAB_LIST:
        m = re.search(rf"\b{b_id}\b", teks_batang_tubuh)
        if m:
            bab_spans.append((m.start(), b_id, b_title))

    bab_spans.sort()

    # Mapping nomor pasal yang berada di setiap BAB secara akurat sesuai naskah UU No. 27/2022
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

    for idx, (start_pos, b_id, b_title) in enumerate(bab_spans):
        end_pos = bab_spans[idx + 1][0] if idx + 1 < len(bab_spans) else len(teks_batang_tubuh)
        bab_content = teks_batang_tubuh[start_pos:end_pos].strip()
        label_bab = f"{b_id} {b_title}"
        start_article, end_article = BAB_ARTICLE_RANGES.get(b_id, (1, 76))

        # 1. HIERARCHICAL PARENT CHUNKS (Otomatis dari PDF, TANPA Hardcode String)
        # Memberikan konteks terpadu untuk pertanyaan luas / plural
        if len(bab_content) <= 4000:
            chunks.append({
                "judul": f"UU No. 27/2022 - {label_bab} (Teks Lengkap)",
                "bab": label_bab,
                "pasal": f"Pasal {start_article} s.d. {end_article}",
                "kategori": "Batang Tubuh (Bab Utuh)",
                "konten": (
                    f"[Dokumen: UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi]\n"
                    f"[Bagian: {label_bab} (Pasal {start_article} s.d. Pasal {end_article})]\n\n"
                    f"{bab_content}"
                ),
            })
        else:
            # Untuk BAB yang sangat panjang (seperti BAB VI), bagi per Bagian resmi undang-undang
            # dan pastikan setiap chunk tidak melebihi kapasitas context window model embedding (~3000 karakter)
            bagian_spans = list(re.finditer(r"(Bagian\s+[A-Za-z]+)", bab_content))
            if bagian_spans:
                for b_i, b_match in enumerate(bagian_spans):
                    b_start = b_match.start()
                    b_end = bagian_spans[b_i + 1].start() if b_i + 1 < len(bagian_spans) else len(bab_content)
                    sub_bab_text = bab_content[b_start:b_end].strip()
                    sub_label = b_match.group(1)

                    if len(sub_bab_text) <= 3000:
                        chunks.append({
                            "judul": f"UU No. 27/2022 - {label_bab} - {sub_label}",
                            "bab": label_bab,
                            "pasal": f"{sub_label}",
                            "kategori": "Batang Tubuh (Bagian)",
                            "konten": (
                                f"[Dokumen: UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi]\n"
                                f"[Bagian: {label_bab} - {sub_label}]\n\n"
                                f"{sub_bab_text}"
                            ),
                        })
                    else:
                        # Sub-chunk bagian yang panjang per ~2500 karakter dengan menjaga keutuhan kata
                        words = sub_bab_text.split(" ")
                        cur_w_block = []
                        w_idx = 1
                        for w in words:
                            cur_w_block.append(w)
                            if len(" ".join(cur_w_block)) >= 2500:
                                chunk_txt = " ".join(cur_w_block).strip()
                                chunks.append({
                                    "judul": f"UU No. 27/2022 - {label_bab} - {sub_label} (Bagian {w_idx})",
                                    "bab": label_bab,
                                    "pasal": f"{sub_label} ({w_idx})",
                                    "kategori": "Batang Tubuh (Bagian)",
                                    "konten": (
                                        f"[Dokumen: UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi]\n"
                                        f"[Bagian: {label_bab} - {sub_label} (Bagian {w_idx})]\n\n"
                                        f"{chunk_txt}"
                                    ),
                                })
                                w_idx += 1
                                cur_w_block = []
                        if cur_w_block:
                            chunk_txt = " ".join(cur_w_block).strip()
                            chunks.append({
                                "judul": f"UU No. 27/2022 - {label_bab} - {sub_label} (Bagian {w_idx})",
                                "bab": label_bab,
                                "pasal": f"{sub_label} ({w_idx})",
                                "kategori": "Batang Tubuh (Bagian)",
                                "konten": (
                                    f"[Dokumen: UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi]\n"
                                    f"[Bagian: {label_bab} - {sub_label} (Bagian {w_idx})]\n\n"
                                    f"{chunk_txt}"
                                ),
                            })

        # 2. CHILD CHUNKS (Per Pasal Individual Secara Berurutan & Presisi)
        article_matches = []
        expected_art = start_article
        for m in re.finditer(r"\bPasal\s+(\d+)\b", bab_content):
            val = int(m.group(1))
            if val == expected_art:
                article_matches.append((val, m.start()))
                expected_art += 1
                if expected_art > end_article:
                    break

        # Fallback jika sequential matcher tidak mendeteksi
        if not article_matches:
            raw_m = list(re.finditer(r"\bPasal\s+(\d+)\b", bab_content))
            for m in raw_m:
                val = int(m.group(1))
                if start_article <= val <= end_article:
                    article_matches.append((val, m.start()))

        if not article_matches:
            # Simpan seluruh konten bab jika tidak ada deteksi pasal individual
            chunks.append({
                "judul": f"UU No. 27/2022 - {label_bab}",
                "bab": label_bab,
                "pasal": "",
                "kategori": "Batang Tubuh",
                "konten": (
                    f"[Dokumen: UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi]\n"
                    f"[Bagian: {label_bab}]\n\n"
                    f"{bab_content}"
                ),
            })
            continue

        for p_idx, (p_num, p_start) in enumerate(article_matches):
            p_end = article_matches[p_idx + 1][1] if p_idx + 1 < len(article_matches) else len(bab_content)
            article_text = bab_content[p_start:p_end].strip()

            label_pasal = f"Pasal {p_num}"

            # Jika pasal terlalu panjang (misal Pasal 1 definisi atau pasal dengan banyak ayat),
            # lakukan sub-chunking dengan mempertahankan context header
            if len(article_text) > settings.CHUNK_SIZE:
                # Potong per ayat / sub-kalimat
                sub_parts = re.split(r"(?=\(\d+\)\s+|(?<=\.\s)(?=[A-Z0-9]))", article_text)
                cur_block = ""
                sub_idx = 1
                for part in sub_parts:
                    if len(cur_block) + len(part) <= settings.CHUNK_SIZE:
                        cur_block += " " + part
                    else:
                        if cur_block.strip():
                            enriched = (
                                f"[Dokumen: UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi]\n"
                                f"[Bagian: {label_bab}]\n"
                                f"[{label_pasal} (Bagian {sub_idx})]\n\n"
                                f"{cur_block.strip()}"
                            )
                            chunks.append({
                                "judul": f"UU No. 27/2022 - {label_bab} - {label_pasal} (Bagian {sub_idx})",
                                "bab": label_bab,
                                "pasal": label_pasal,
                                "kategori": "Batang Tubuh",
                                "konten": enriched,
                            })
                            sub_idx += 1
                        cur_block = part
                if cur_block.strip():
                    enriched = (
                        f"[Dokumen: UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi]\n"
                        f"[Bagian: {label_bab}]\n"
                        f"[{label_pasal} (Bagian {sub_idx})]\n\n"
                        f"{cur_block.strip()}"
                    )
                    chunks.append({
                        "judul": f"UU No. 27/2022 - {label_bab} - {label_pasal} (Bagian {sub_idx})",
                        "bab": label_bab,
                        "pasal": label_pasal,
                        "kategori": "Batang Tubuh",
                        "konten": enriched,
                    })
            else:
                enriched = (
                    f"[Dokumen: UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi]\n"
                    f"[Bagian: {label_bab}]\n"
                    f"[{label_pasal}]\n\n"
                    f"{article_text}"
                )
                chunks.append({
                    "judul": f"UU No. 27/2022 - {label_bab} - {label_pasal}",
                    "bab": label_bab,
                    "pasal": label_pasal,
                    "kategori": "Batang Tubuh",
                    "konten": enriched,
                })

    # 3. Parsing Bagian Penjelasan
    if teks_penjelasan:
        # Penjelasan Umum
        pj_pasal_demi_pasal = "PASAL DEMI PASAL"
        idx_pdp = teks_penjelasan.upper().find(pj_pasal_demi_pasal)

        if idx_pdp != -1:
            penjelasan_umum = teks_penjelasan[:idx_pdp].strip()
            penjelasan_pasal_text = teks_penjelasan[idx_pdp:].strip()
        else:
            penjelasan_umum = teks_penjelasan[:2000].strip()
            penjelasan_pasal_text = teks_penjelasan[2000:].strip()

        # Chunking Penjelasan Umum
        chunks.append({
            "judul": "UU No. 27/2022 - PENJELASAN UMUM",
            "bab": "PENJELASAN",
            "pasal": "Umum",
            "kategori": "Penjelasan",
            "konten": (
                "[Dokumen: UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi]\n"
                "[Bagian: PENJELASAN ATAS UNDANG-UNDANG (UMUM)]\n\n"
                f"{penjelasan_umum[:1500]}"
            ),
        })

        # Chunking Penjelasan Pasal demi Pasal
        pj_matches = list(re.finditer(r"\bPasal\s+(\d+)\b", penjelasan_pasal_text))
        for idx, m in enumerate(pj_matches):
            p_num = m.group(1)
            p_start = m.start()
            p_end = pj_matches[idx + 1].start() if idx + 1 < len(pj_matches) else len(penjelasan_pasal_text)
            konten_pj = penjelasan_pasal_text[p_start:p_end].strip()

            label_pasal = f"Pasal {p_num}"
            enriched_pj = (
                f"[Dokumen: UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi]\n"
                f"[Bagian: PENJELASAN PASAL DEMI PASAL]\n"
                f"[Penjelasan {label_pasal}]\n\n"
                f"{konten_pj}"
            )
            chunks.append({
                "judul": f"UU No. 27/2022 - Penjelasan {label_pasal}",
                "bab": "PENJELASAN PASAL DEMI PASAL",
                "pasal": label_pasal,
                "kategori": "Penjelasan",
                "konten": enriched_pj,
            })

    return chunks


def proses_dan_simpan_uupdp():
    """Membaca file PDF UU PDP, membersihkan, men-chunk, dan menyimpan vektor ke pgvector."""
    from mcp_server.db import get_connection, release_connection
    from mcp_server.vector_store import generate_embedding

    pdf_file = settings.PDF_PATH
    print("=" * 70)
    print(" INGESTION KNOWLEDGE UU PERLINDUNGAN DATA PRIBADI (UU NO. 27 TAHUN 2022)")
    print("=" * 70)
    print(f"[INGEST] Membaca file: {pdf_file}")

    teks_mentah = ekstrak_teks_pdf(pdf_file)
    teks_bersih = bersihkan_teks_hukum(teks_mentah)
    chunks = segmentasikan_uu_pdp(teks_bersih)

    print(f"[INGEST] Total potongan chunk hukum berkualitas: {len(chunks)}")
    table_name = settings.DOC_TABLE_NAME

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            print(f"[INGEST] Mengosongkan tabel {table_name}...")
            cur.execute(f"TRUNCATE TABLE {table_name} RESTART IDENTITY;")
            conn.commit()

            print(f"[INGEST] Memulai generasi embedding ({settings.EMBEDDING_MODEL}) ke pgvector...")
            for idx, c in enumerate(chunks, 1):
                metadata = {
                    "bab": c["bab"],
                    "pasal": c["pasal"],
                    "kategori": c["kategori"],
                    "chunk_id": idx,
                }

                vec = generate_embedding(c["konten"])

                sql = f"""
                    INSERT INTO {table_name} (judul, bab, pasal, kategori, konten, embedding, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                """
                cur.execute(
                    sql,
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

                if idx % 10 == 0 or idx == len(chunks):
                    print(f" -> Terproses {idx}/{len(chunks)} chunks...")
                    conn.commit()

            print(f"\n[SUKSES] Seluruh pasal dan ketentuan UU PDP berhasil di-indeks ke tabel '{table_name}'!")
    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Gagal proses ingest UU PDP: {e}")
        raise
    finally:
        release_connection(conn)


if __name__ == "__main__":
    proses_dan_simpan_uupdp()
