# Chatbot Asisten Hukum UU Perlindungan Data Pribadi (UU No. 27 Tahun 2022)

Aplikasi Chatbot cerdas berbasis **Retrieval-Augmented Generation (RAG)** dan protokol **Model Context Protocol (FastMCP)** yang menggunakan basis pengetahuan naskah resmi **Undang-Undang Republik Indonesia Nomor 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP)**.

Projek ini mengintegrasikan **FastAPI**, **LangChain**, **Ollama**, dan **PostgreSQL (pgvector)** di sisi backend, serta antarmuka modern interaktif berbasis **React (Vite + Tailwind CSS)** di sisi frontend.

---

## Daftar Isi
- [Fitur Utama](#fitur-utama)
- [Arsitektur Sistem](#arsitektur-sistem)
- [Struktur Folder](#struktur-folder)
- [Prasyarat Sistem](#prasyarat-sistem)
- [Langkah Instalasi](#langkah-instalasi)
- [Konfigurasi Lingkungan (.env)](#konfigurasi-lingkungan-env)
- [Setup Database & Ollama](#setup-database--ollama)
- [Menjalankan Migrasi Database](#menjalankan-migrasi-database)
- [Menjalankan Ingest Dokumen UU PDP](#menjalankan-ingest-dokumen-uu-pdp)
- [Cara Menjalankan Aplikasi](#cara-menjalankan-aplikasi)
  - [Opsi A: Mode Terminal Interaktif (CLI)](#opsi-a-mode-terminal-interaktif-cli)
  - [Opsi B: Mode Full-Stack (Backend API + Web UI)](#opsi-b-mode-full-stack-backend-api--web-ui)
- [Pengujian & Evaluasi Kualitas RAG](#pengujian--evaluasi-kualitas-rag)
- [Troubleshooting](#troubleshooting)

---

## Fitur Utama

1. **Knowledge Asli Dokumen Hukum**: Mengindeks seluruh naskah resmi UU No. 27 Tahun 2022 (Batang Tubuh 16 BAB, 76 Pasal, dan Bagian Penjelasan Resmi).
2. **Hybrid & Article-Boosted RAG**:
   - Jika pengguna menanyakan nomor pasal tertentu (misal *"Apa isi Pasal 15?"* atau *"Bagaimana sanksi Pasal 67?"*), sistem mendeteksi nomor pasal dan menarik pasal terkait secara terarah (*exact article retrieval*).
   - Dilengkapi pencarian kemiripan makna (*Cosine Distance*) menggunakan indeks vektor **HNSW pgvector**.
3. **Context Enrichment**: Setiap potongan data (*chunk*) dilengkapi label konteks eksplisit `[Dokumen]`, `[Bagian/BAB]`, dan `[Pasal]` agar retrieval dan pemahaman LLM memiliki akurasi tinggi.
4. **Resistensi Halusinasi**: System prompt dirancang agar LLM selalu mencantumkan nomor Pasal/Ayat resmi dan menolak mengarang aturan yang tidak diatur dalam UU PDP.
5. **Standar Model Context Protocol (MCP)**: Komunikasi modular antara LLM orchestrator dan tool pencari dokumen melalui FastMCP Server via `stdio`.
6. **Antarmuka Ganda**: Tersedia antarmuka Command Line Interface (CLI) interaktif dan Web Dashboard modern (React Vite).

---

## Arsitektur Sistem

```
+-------------------------------------------------------------+
|                      USER INTERFACE                         |
|     React Web UI (Vite)      ATAU     Terminal CLI (main.py)|
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                     BACKEND FASTAPI                         |
|               (backend/api.py - Port 8000)                  |
|    - Direct Endpoint: /api/chat                             |
|    - Async Polling:   /api/chat/async, /api/chat/status     |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|               ORCHESTRATOR & AGENT WORKFLOW                 |
|                (backend/agent/workflow.py)                  |
|          LangChain + ChatOllama (llama3.2)                  |
+-------------------------------------------------------------+
                              |  (stdio ClientSession)
                              v
+-------------------------------------------------------------+
|                   FASTMCP KNOWLEDGE SERVER                  |
|                  (mcp_server/server.py)                     |
|        Tool: cari_pasal_dan_ketentuan_uupdp                 |
+-------------------------------------------------------------+
                              |
                              v
+-------------------------------------------------------------+
|                     VECTOR STORE & DB                       |
|                (mcp_server/vector_store.py)                 |
|   - Hybrid/Article-Boosted Search                           |
|   - PostgreSQL + pgvector (HNSW Index: uupdp_dokumen)       |
|   - Ollama Embeddings (nomic-embed-text)                    |
+-------------------------------------------------------------+
```

---

## Struktur Folder

```text
chatbot-practice/
├── .env.example                     # Template environment variables
├── .gitignore                       # File dan direktori yang diabaikan git
├── docker-compose.yml.example       # Template deployment Docker untuk DB & Ollama
├── main.py                          # Entry point CLI Chatbot
├── requirements.txt                 # Daftar dependensi Python
├── README.md                        # Dokumentasi lengkap proyek
├── backend/
│   ├── __init__.py
│   ├── api.py                       # REST API Backend (FastAPI)
│   ├── main.py                      # Runner CLI interaktif
│   └── agent/
│       ├── __init__.py
│       ├── client.py                # Klien MCP Stdio untuk subproses
│       └── workflow.py              # LangChain RAG pipeline & Prompt hukum
├── config/
│   ├── __init__.py
│   └── settings.py                  # Konfigurasi terpusat berbasis .env
├── data/
│   └── UU_No_27_Tahun_2022_PDP.pdf  # Naskah resmi PDF UU PDP
├── docs/
│   └── evaluasi_tanya_jawab_uupdp.md# 17 Butir pertanyaan uji & rujukan jawaban AI
├── frontend/                        # Web UI React + Vite + Tailwind CSS
│   ├── package.json
│   ├── src/
│   │   ├── App.jsx                  # Komponen utama chat view & health polling
│   │   ├── components/              # ChatInput, MessageItem, CitationBadge
│   │   └── services/api.js          # Layanan HTTP client ke Backend
├── mcp_server/
│   ├── __init__.py
│   ├── db.py                        # Connection pool PostgreSQL & pgvector
│   ├── ingest_uupdp.py              # Script utama parsing & indexing naskah PDF
│   ├── server.py                    # FastMCP Server (Tools exposer)
│   ├── vector_store.py              # Query hybrid pgvector & Ollama embedding
│   └── migrations/
│       ├── 001_init_uupdp_schema.sql# Skema tabel uupdp_dokumen & indeks HNSW
│       └── runner.py                # Script eksekusi migrasi database
```

---

- **Node.js**: Versi 18+ & **npm** (untuk menjalankan frontend React).
- **PostgreSQL**: Versi 15+ dengan ekstensi **pgvector** aktif.
- **Ollama**: Layanan model lokal sudah aktif di `http://localhost:11434`.

---

## Langkah Instalasi

### 1. Clone atau Buka Folder Proyek
Pastikan Anda berada di direktori root `chatbot-practice`:
```powershell
cd d:\iis-reza\kode-projek\chatbot-practice
```

### 2. Buat dan Aktifkan Virtual Environment Python
```powershell
# Membuat virtual environment
python -m venv venv

# Mengaktifkan di Windows PowerShell
.\venv\Scripts\Activate.ps1

# (Atau jika di Command Prompt / CMD)
# .\venv\Scripts\activate.bat
```

### 3. Install Dependensi Python
```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Install Dependensi Frontend
```powershell
cd frontend
npm install
cd ..
```

---

## Konfigurasi Lingkungan (.env)

Salin file `.env.example` menjadi `.env` pada root folder proyek:
```powershell
copy .env.example .env
```

Sesuaikan nilai di dalam `.env` sesuai pengaturan sistem Anda:
```env
# 1. Database PostgreSQL & Ekstensi pgvector
DB_HOST=localhost
DB_PORT=5432
DB_NAME=chatbot_db
DB_USER=postgres
DB_PASSWORD=postgres
DOC_TABLE_NAME=uupdp_dokumen

# 2. Pilihan LLM Provider ('gemini' untuk Google Cloud, 'ollama' untuk model lokal)
LLM_PROVIDER=gemini

# 3. Konfigurasi Google Gemini API (Model terbaru & sangat cepat)
# Dapatkan API Key di: https://aistudio.google.com/
GEMINI_API_KEY=your_gemini_api_key_here
# Model pilihan:
# - gemini-3.5-flash-lite (Rekomendasi: sangat cepat, ringan, respons <2 detik)
# - gemini-3.8-flash (Model penalaran mendalam terbaru)
GEMINI_MODEL=gemini-3.5-flash-lite

# 4. Konfigurasi Ollama Service (Fallback LLM Lokal & Embeddings pgvector)
OLLAMA_BASE_URL=http://localhost:11434
LLM_MODEL=llama3.2
EMBEDDING_MODEL=nomic-embed-text
EMBED_DIMENSION=768

# 5. Path Dokumen & Parameter RAG
PDF_PATH=data/UU_No_27_Tahun_2022_PDP.pdf
CHUNK_SIZE=1000
CHUNK_OVERLAP=150
TOP_K_RESULTS=5
SIMILARITY_THRESHOLD=0.40
MAX_TOKENS=600

# 6. Frontend & CORS
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

---

## Setup Database & Ollama

Layanan yang dibutuhkan untuk menjalankan sistem RAG ini adalah **PostgreSQL (dengan ekstensi pgvector)** dan **Ollama**. Anda dapat menjalankannya menggunakan **Podman** (sangat direkomendasikan jika tanpa Docker), **Docker**, maupun instalasi lokal.

---

### Opsi A: Menggunakan Podman (Direkomendasikan)

Podman adalah *container engine* berbasis standar OCI yang *rootless* dan *daemonless*. Anda dapat memilih salah satu dari 2 metode berikut:

#### Metode 1: Menggunakan Podman Compose
Jika Anda memiliki `podman-compose` atau plugin `podman compose`:
```powershell
# 1. Pastikan Podman Machine aktif (khusus Windows)
podman machine start

# 2. Salin template compose
copy docker-compose.yml.example docker-compose.yml

# 3. Jalankan container
podman compose up -d
# (atau jika menggunakan podman-compose python package: podman-compose up -d)

# 4. Unduh model di dalam container Ollama
podman exec -it uupdp_ollama ollama pull llama3.2
podman exec -it uupdp_ollama ollama pull nomic-embed-text
```

#### Metode 2: Menggunakan Fitur Asli Podman (Podman Pod - Tanpa Compose)
Podman memiliki fitur unggulan berupa **Pod** (berbagi localhost & network namespace yang sama). Anda tidak perlu menginstal compose tambahan:
```powershell
# 1. Buat Pod bersama dengan mapping port PostgreSQL (5432) dan Ollama (11434)
podman pod create --name uupdp_pod -p 5432:5432 -p 11434:11434

# 2. Jalankan PostgreSQL (pgvector) di dalam pod
podman run -d --pod uupdp_pod --name uupdp_postgres `
  -e POSTGRES_USER=postgres `
  -e POSTGRES_PASSWORD=postgres `
  -e POSTGRES_DB=chatbot_db `
  -v uupdp_pgdata:/var/lib/postgresql/data `
  pgvector/pgvector:pg16

# 3. Jalankan Ollama di dalam pod
podman run -d --pod uupdp_pod --name uupdp_ollama `
  -v uupdp_ollamadata:/root/.ollama `
  ollama/ollama:latest

# 4. Unduh model LLM dan Embeddings
podman exec -it uupdp_ollama ollama pull llama3.2
podman exec -it uupdp_ollama ollama pull nomic-embed-text
```

*Untuk menghentikan pod nantinya:*
```powershell
podman pod stop uupdp_pod
# Untuk memulai kembali:
podman pod start uupdp_pod
```

---

### Opsi B: Menggunakan Docker Compose

Jika Anda menggunakan Docker Desktop atau Docker Engine:
```powershell
copy docker-compose.yml.example docker-compose.yml
docker compose up -d

# Unduh model di dalam container Ollama
docker exec -it uupdp_ollama ollama pull llama3.2
docker exec -it uupdp_ollama ollama pull nomic-embed-text
```

---

### Opsi C: Menggunakan Instalasi Native / Lokal

Jika Anda menjalankan PostgreSQL dan Ollama langsung di host Windows:
1. **Ollama**:
   Pastikan aplikasi Ollama Desktop aktif, lalu unduh model:
   ```powershell
   ollama pull llama3.2
   ollama pull nomic-embed-text
   ```
2. **PostgreSQL**:
   - Pastikan service PostgreSQL aktif di port `5432`.
   - Buat database sesuai `.env`:
     ```sql
     CREATE DATABASE chatbot_db;
     ```
   - Pastikan library `pgvector` sudah terpasang di PostgreSQL lokal Anda.

---

## Menjalankan Migrasi Database

Sebelum mengindeks dokumen atau menyalakan aplikasi, jalankan skrip runner migrasi untuk membuat tabel `uupdp_dokumen` beserta indeks HNSW:

```powershell
python -m mcp_server.migrations.runner
```

*Output yang diharapkan:*
```text
[MIGRATION] Menjalankan 001_init_uupdp_schema.sql...
[MIGRATION] Sukses mengaplikasikan 001_init_uupdp_schema.sql.
```

*(Catatan: Backend FastAPI juga akan otomatis memverifikasi migrasi ini saat pertama kali dinyalakan).*

---

## Menjalankan Ingest Dokumen UU PDP

Jalankan proses ekstraksi, segmentasi pasal/ayat, dan pembuatan embedding untuk naskah `data/UU_No_27_Tahun_2022_PDP.pdf`:

```powershell
python -m mcp_server.ingest_uupdp
```

*Tahapan yang dilakukan oleh skrip:*
1. Membaca naskah PDF UU PDP secara komprehensif (mendukung `pypdf` dan parser stream hex internal).
2. Membersihkan artefak pindaian OCR Setneg (`Pasa722` $\rightarrow$ `Pasal 22`, header/footer Setneg, dll).
3. Melakukan pemisahan hierarkis 16 BAB Batang Tubuh dan Bagian Penjelasan Resmi.
4. Menerapkan **Context Enrichment** pada setiap chunk: menyematkan informasi Dokumen, BAB, dan Nomor Pasal.
5. Menghitung embedding via Ollama (`nomic-embed-text`) dan menyimpannya ke tabel `uupdp_dokumen` di pgvector.

---

## Cara Menjalankan Aplikasi

Anda dapat berinteraksi dengan chatbot melalui dua cara:

### Opsi A: Mode Terminal Interaktif (CLI)

Gunakan mode ini untuk pengujian cepat langsung dari terminal:
```powershell
python main.py
```
atau:
```powershell
python -m backend.main
```

Ketik pertanyaan Anda saat prompt `Pertanyaan Anda:` muncul. Untuk keluar, ketik `exit` atau `keluar`.

---

### Opsi B: Mode Full-Stack (Backend API + Web UI)

#### 1. Jalankan Backend API (FastAPI)
Buka terminal pertama dan jalankan:
```powershell
uvicorn backend.api:app --reload --port 8000
```
- API aktif di: `http://localhost:8000`
- Dokumentasi interaktif Swagger UI: `http://localhost:8000/docs`
- Health check endpoint: `http://localhost:8000/api/health`

#### 2. Jalankan Frontend (React Vite)
Buka terminal kedua dan jalankan:
```powershell
cd frontend
npm run dev
```
- Buka browser Anda di: `http://localhost:5173`
- Status badge di kanan atas akan otomatis berwarna hijau (`Backend & MCP Ready`) saat backend terhubung.

---

## Pengujian & Evaluasi Kualitas RAG

Untuk menguji performa, akurasi, dan ketepatan rujukan pasal oleh model AI, silakan gunakan dokumen benchmark yang telah disediakan:

📄 **[`docs/evaluasi_tanya_jawab_uupdp.md`](docs/evaluasi_tanya_jawab_uupdp.md)**

File ini berisi **17 contoh pertanyaan uji resmi** beserta dasar hukum dan harapan jawaban AI, mencakup:
- **Ketentuan Umum & Definisi**: Perbedaan Pengendali vs Prosesor Data (Pasal 1).
- **Klasifikasi Data Pribadi**: Data Umum vs Spesifik (Pasal 4).
- **Hak Subjek Data Pribadi**: Hak akses, penghapusan (*erasure*), penarikan persetujuan, dan pengecualiannya (Pasal 5 s.d. 15).
- **Penanganan Kebocoran Data**: Kewajiban pemberitahuan maksimal 3 x 24 jam (Pasal 46).
- **Penunjukan DPO**: Syarat wajib penunjukan Pejabat Pelindung Data Pribadi (Pasal 53).
- **Transfer Internasional**: Ketentuan transfer data ke luar negeri (Pasal 56).
- **Sanksi Administratif**: Denda maksimal 2% pendapatan tahunan (Pasal 57).
- **Sanksi Pidana**: Penjara 5-6 tahun dan denda Rp5-Rp6 miliar untuk perolehan ilegal dan jual beli data (Pasal 65 - 68), serta denda 10x lipat bagi korporasi (Pasal 70).
- **Uji Ketahanan Negatif**: Menguji ketahanan model agar tidak berhalusinasi saat ditanyakan hal di luar UU PDP (seperti regulasi GDPR Uni Eropa).

---

## Troubleshooting

### 1. `ModuleNotFoundError: No module named 'psycopg2'` atau `dotenv`
- **Penyebab**: Dependensi belum diinstal di lingkungan Python yang aktif.
- **Solusi**: Pastikan virtual environment telah aktif, lalu jalankan `pip install -r requirements.txt`.

### 2. Error Koneksi Database (`Connection refused` / `database does not exist`)
- **Penyebab**: PostgreSQL belum menyala atau kredensial di `.env` belum sesuai.
- **Solusi**: Periksa apakah container Podman/Docker atau service PostgreSQL lokal sedang aktif di port `5432`. Buat database `chatbot_db` jika belum ada.

### 3. Ekstensi `vector` Tidak Dikenali (`type "vector" does not exist`)
- **Penyebab**: Ekstensi `pgvector` belum terpasang di instance PostgreSQL.
- **Solusi**: Jika menggunakan PostgreSQL lokal, install pgvector sesuai instruksi resmi pgvector. Alternatif termudah adalah menggunakan image container `pgvector/pgvector:pg16` yang sudah disediakan di `docker-compose.yml.example` (bisa dijalankan via Podman atau Docker).

### 4. Eksekusi Skrip NPM Ditolak di PowerShell Windows
- **Penyebab**: Kebijakan eksekusi PowerShell (`PSSecurityException`).
- **Solusi**: Jalankan perintah npm melalui CMD:
  ```powershell
  cmd /c "npm run dev"
  ```
  atau izinkan eksekusi skrip untuk sesi saat ini:
  ```powershell
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  ```

### 5. `Error MCP Client: ConnectionRefusedError` atau Ollama Lambat
- **Penyebab**: Server Ollama belum dinyalakan atau model belum selesai diunduh.
- **Solusi**: Pastikan container Ollama (Podman/Docker) aktif atau jalankan `ollama serve`. Pastikan model `llama3.2` dan `nomic-embed-text` sudah terunduh dengan perintah `ollama list` (atau `podman exec -it uupdp_ollama ollama list`).

### 6. Podman di Windows: `Cannot connect to Podman` / WSL VM Mati
- **Penyebab**: Virtual machine Podman di Windows belum aktif.
- **Solusi**: Jalankan perintah berikut di PowerShell:
  ```powershell
  podman machine list
  podman machine start
  ```
  *(Jika baru pertama kali menginstal Podman, jalankan `podman machine init` terlebih dahulu).*
