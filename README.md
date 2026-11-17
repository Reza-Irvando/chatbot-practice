# Chatbot Asisten Hukum UU Perlindungan Data Pribadi (UU No. 27 Tahun 2022)

Aplikasi chatbot konsultasi hukum resmi **Undang-Undang Republik Indonesia Nomor 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP)** yang dibangun dengan arsitektur **4-Microservice** terpisah serta pola **Strategy Pattern Multi-Orchestrator** untuk beralih secara dinamis antara **Dify Chatflow** dan **LangGraph Agentic RAG** (berbasis **Google Gemini Flash-Lite**, **MCP Server SSE**, dan **PostgreSQL `pgvector`**).

---

## Daftar Isi
- [Fitur Utama](#fitur-utama)
- [Arsitektur Sistem](#arsitektur-sistem)
- [Alur Kerja LangGraph Agentic RAG](#alur-kerja-langgraph-agentic-rag)
- [Struktur Proyek](#struktur-proyek)
- [Prasyarat Sistem](#prasyarat-sistem)
- [Konfigurasi Environment Per-Microservice](#konfigurasi-environment-per-microservice)
- [Menjalankan dengan Docker / Podman (Rekomendasi)](#menjalankan-dengan-docker--podman-rekomendasi)
- [Menjalankan Secara Lokal (Manual)](#menjalankan-secara-lokal-manual)
- [Evaluasi & Pertanyaan Uji Hukum](#evaluasi--pertanyaan-uji-hukum)
- [Troubleshooting](#troubleshooting)

---

## Fitur Utama

1. **Dynamic Multi-Orchestrator (Strategy Pattern)**: Beralih antara **`dify`** (eksternal Dify Chatflow API) dan **`langgraph`** (Agentic RAG lokal) hanya dengan mengubah `ORCHESTRATOR_PROVIDER` di `backend/.env` tanpa mengubah frontend React.
2. **Alur LangGraph Selaras `tmp/workflow.mmd`**: Mendukung Question Classifier (sapaan vs hukum), Retrieval ke MCP Server, Relevance Grader, Loop Query Rewriter (maksimal 2 putaran), Generator Jawaban Hukum + Sitasi, serta Fallback saat pasal tidak ditemukan.
3. **Google Gemini API (`gemini-3.5-flash-lite` & `gemini-embedding-001`)**: Ringan, cepat, dan menggunakan model Flash-Lite serta embedding 768 dimensi resmi Google AI Studio.
4. **Standalone FastMCP Knowledge Server (`mcp_server`)**: Berjalan sebagai microservice terpisah via transport **SSE** (`http://mcp_server:8000/sse`), melakukan pencarian hybrid (`pgvector` Cosine + PostgreSQL Full-Text Search RRF) dengan fallback otomatis ke pencarian leksikal naskah PDF lokal.
5. **Auto-Migration & Auto-Ingestion**: Saat container `mcp_server` menyala, skema database `pgvector` (`uupdp_dokumen`, indeks HNSW & GIN FTS) otomatis dibuat dan naskah PDF UU PDP di-ingest bila tabel masih kosong dan `GEMINI_API_KEY` tersedia.
6. **Multi-Turn Conversation Memory & Reset Sesi**: Mendukung percakapan multi-turn lewat `conversation_id` (Dify & LangGraph `MemorySaver`) serta tombol **Reset Sesi** di UI Web.

---

## Arsitektur Sistem

```text
Browser (React Web UI)  /  CLI (backend/main.py)
               │
               ▼
┌─────────────────────────────────────────────────────────────┐
│  1. Frontend (React + Vite + Nginx)          [Port: 5173]   │
│     - Proxy /api/ ──▶ backend:8000                          │
└─────────────────────────────────────────────────────────────┘
               │  POST /api/chat/async  |  GET /api/chat/status/{id}
               ▼
┌─────────────────────────────────────────────────────────────┐
│  2. Backend FastAPI (Multi-Orchestrator)     [Port: 8000]   │
│     - Factory: get_orchestrator()                           │
│     ├── ORCHESTRATOR_PROVIDER=dify      ──▶ Dify Chatflow   │
│     └── ORCHESTRATOR_PROVIDER=langgraph ──▶ LangGraph +     │
│                                             Gemini 3.5 Lite │
└─────────────────────────────────────────────────────────────┘
               │  MCP SSE (http://mcp_server:8000/sse)
               ▼
┌─────────────────────────────────────────────────────────────┐
│  3. MCP Knowledge Server (FastMCP)      [Host: 8001 → 8000] │
│     - Tool: cari_pasal_dan_ketentuan_uupdp                  │
│     - Hybrid Retrieval (Vector + FTS RRF) + Auto-Migrate    │
└─────────────────────────────────────────────────────────────┘
               │  TCP :5432
               ▼
┌─────────────────────────────────────────────────────────────┐
│  4. PostgreSQL 16 + pgvector (chatbot_db)    [Port: 5432]   │
│     - Tabel: uupdp_dokumen (VECTOR 768, HNSW, GIN FTS)      │
└─────────────────────────────────────────────────────────────┘
```

---

## Alur Kerja LangGraph Agentic RAG

Orkestrator `langgraph` (`backend/orchestrators/langgraph_provider.py`) mengikuti diagram di [`tmp/workflow.mmd`](tmp/workflow.mmd):

1. **`question_classifier` (`QC`)**: Mengklasifikasikan pesan menjadi sapaan/obrolan umum (`greeting`) atau pertanyaan pasal/hukum UU PDP (`legal`), serta menginisialisasi `current_query`, `is_found = False`, dan `loop_count = 0`.
2. **Cabang Sapaan (`general_assistant` / LLM 4 $\rightarrow$ ANS3)**: Merespons sapaan secara cepat dan ramah tanpa memanggil retrieval.
3. **Cabang Hukum (`LOOP_BLOCK`, Max Loop Count = 2)**:
   - **`knowledge_retrieval` (`KR`)**: Memanggil MCP Server (`cari_pasal_dan_ketentuan_uupdp`) menggunakan `current_query`.
   - **`relevance_grader` (`GRADER`)**: Gemini mengevaluasi relevansi hasil (`RELEVAN` / `TIDAK_RELEVAN`):
     - Jika **`RELEVAN`**: `is_found = True` $\rightarrow$ keluar loop menuju **`legal_generator` (`LLM 3` $\rightarrow$ ANS)** untuk menyusun jawaban beserta sitasi pasal.
     - Jika **`TIDAK_RELEVAN`** dan `loop_count < 2`: menuju **`query_rewriter` (`LLM 2`)** untuk memperbaiki kata kunci hukum UU PDP (`current_query = hasil_rewrite`), lalu kembali ke `knowledge_retrieval`.
     - Jika **`TIDAK_RELEVAN`** setelah 2 putaran (`is_found == False`): menuju **`fallback_not_found` (`ANS2`)**.

---

## Struktur Proyek

```text
chatbot-practice/
├── docker-compose.yml              # Orkestrasi 4 microservice (db, mcp_server, backend, frontend)
├── README.md
├── data/
│   └── UU_No_27_Tahun_2022_PDP.pdf # Naskah resmi UU PDP (di-mount ke mcp_server)
├── docs/
│   └── evaluasi_tanya_jawab_uupdp.md
├── tmp/
│   └── workflow.mmd                # Diagram referensi alur Agentic RAG
│
├── mcp_server/                     # Microservice: Knowledge Base & FastMCP SSE Server
│   ├── .env                        # Konfigurasi DB, Gemini Embedding, & MCP (tidak di-commit)
│   ├── .env.example
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── config.py                   # Pemuat settings mandiri mcp_server
│   ├── db.py                       # Connection pool PostgreSQL + pgvector
│   ├── vector_store.py             # Gemini Embedding (768d) + Hybrid RRF + fallback PDF
│   ├── ingest_uupdp.py             # Parser & segmentasi UU PDP
│   ├── init_db.py                  # Wait DB, migrasi SQL, & auto-ingest
│   ├── server.py                   # FastMCP Server (stdio / sse)
│   └── migrations/
│       └── 001_init_uupdp_schema.sql
│
├── backend/                        # Microservice: FastAPI Multi-Orchestrator
│   ├── .env                        # Konfigurasi Provider, Dify, & Gemini LLM (tidak di-commit)
│   ├── .env.example
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── api.py                      # REST API (/api/health, /api/chat, /api/chat/async)
│   ├── dify_client.py              # Wrapper kompatibilitas DifyProvider
│   ├── main.py                     # CLI interaktif (opsional)
│   ├── config/
│   │   └── settings.py             # Pemuat settings mandiri backend
│   └── orchestrators/              # Strategy Pattern Multi-Orchestrator
│       ├── __init__.py
│       ├── base.py                 # OrchestratorResponse & BaseOrchestrator
│       ├── dify_provider.py        # Strategy: Dify Chatflow API
│       ├── langgraph_provider.py   # Strategy: LangGraph Agentic RAG + Gemini Flash-Lite
│       └── factory.py              # get_orchestrator()
│
└── frontend/                       # Microservice: Web UI React + Vite + Nginx
    ├── .env                        # Konfigurasi VITE_API_BASE_URL (tidak di-commit)
    ├── .env.example
    ├── Dockerfile
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx
        ├── components/
        └── services/api.js
```

---

## Prasyarat Sistem

- **Container Engine (Direkomendasikan)**: **Podman** (dengan `podman-compose`) atau **Docker Desktop**.
- **Google Gemini API Key** (dari [Google AI Studio](https://aistudio.google.com/)) — wajib untuk mode `langgraph` (`gemini-3.5-flash-lite` & `gemini-embedding-001`).
- **Dify Chatflow API Key** — wajib bila `ORCHESTRATOR_PROVIDER=dify`.
- **Lokal / Manual (Opsional)**: Python 3.10+ dan Node.js 18+.

---

## Konfigurasi Environment Per-Microservice

Setiap microservice memiliki file `.env` mandirinya sendiri (salin dari masing-masing `.env.example` bila belum ada):

### 1. Backend (`backend/.env`)
```env
# Pilihan Orchestrator: dify | langgraph
ORCHESTRATOR_PROVIDER=dify

# Dify Chatflow API (wajib jika ORCHESTRATOR_PROVIDER=dify)
DIFY_API_URL=http://172.16.12.98/v1/chat-messages
DIFY_API_KEY=app-xxxxxxxxxxxxxxxxxxxx

# Google Gemini API (wajib jika ORCHESTRATOR_PROVIDER=langgraph)
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxx
GEMINI_MODEL=gemini-3.5-flash-lite
MAX_TOKENS=1024

# Microservice MCP Server (di container otomatis memakai http://mcp_server:8000/sse)
MCP_SERVER_URL=http://mcp_server:8000/sse

PORT=8000
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### 2. MCP Server (`mcp_server/.env`)
```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=chatbot_db
DB_USER=postgres
DB_PASSWORD=postgres
DOC_TABLE_NAME=uupdp_dokumen

# Google Gemini Embedding (untuk indexing & vector search pgvector)
GEMINI_API_KEY=AIzaSyxxxxxxxxxxxxxxxxxxxx
EMBEDDING_MODEL=gemini-embedding-001
EMBED_DIMENSION=768

TOP_K_RESULTS=5
SIMILARITY_THRESHOLD=0.40
CHUNK_SIZE=1000
CHUNK_OVERLAP=150

MCP_HOST=0.0.0.0
MCP_PORT=8000
MCP_TRANSPORT=sse
```

### 3. Frontend (`frontend/.env`)
```env
VITE_API_BASE_URL=/api
```

---

## Menjalankan dengan Docker / Podman (Rekomendasi)

```powershell
# Build & jalankan seluruh 4 microservice (db, mcp_server, backend, frontend)
podman compose up --build -d
# atau
docker compose up --build -d
```

Setelah container aktif:
| Service | Container Name | Endpoint / URL |
|---|---|---|
| **Web Chatbot** | `chatbot_frontend` | [http://localhost:5173](http://localhost:5173) |
| **Backend API & Swagger** | `chatbot_backend` | [http://localhost:8000/docs](http://localhost:8000/docs) |
| **Backend Health Check** | `chatbot_backend` | [http://localhost:8000/api/health](http://localhost:8000/api/health) |
| **MCP Server (SSE)** | `chatbot_mcp_server` | `http://localhost:8001/sse` (internal: `http://mcp_server:8000/sse`) |
| **PostgreSQL pgvector** | `chatbot_db` | `localhost:5432` |

Perintah manajemen container:
```powershell
# Beralih antara Dify <-> LangGraph setelah mengubah ORCHESTRATOR_PROVIDER di backend/.env
podman compose restart backend

# Melihat log masing-masing service
podman compose logs -f mcp_server
podman compose logs -f backend

# Menghentikan seluruh stack
podman compose down
```

### Berbagi Akses via IP Jaringan Lokal (LAN / Wi-Fi)
Secara default, port `db` (`5432`), `mcp_server` (`8001`), dan `backend` (`8000`) hanya dibuka di `127.0.0.1` (localhost) demi keamanan, dan hanya port `frontend` (`5173`) yang menjadi pintu masuk bersama lewat Nginx proxy (`/api/`).

Untuk membagikan Web UI ke perangkat lain di jaringan Wi-Fi/kantor yang sama pada Windows + Podman, jalankan skrip [`share-lan.ps1`](share-lan.ps1) di **PowerShell (Run as Administrator)**:
```powershell
# Buka akses LAN (portproxy + Firewall Private/Domain)
powershell -ExecutionPolicy Bypass -File .\share-lan.ps1 start

# Cek status & alamat IP yang dibagikan
powershell -ExecutionPolicy Bypass -File .\share-lan.ps1 status

# Tutup kembali akses LAN setelah selesai
powershell -ExecutionPolicy Bypass -File .\share-lan.ps1 stop
```

---

## Menjalankan Secara Lokal (Manual)

### 1. Jalankan Database & MCP Server
Pastikan PostgreSQL (`pgvector`) berjalan di `localhost:5432` (bisa menyalakan service `db` saja dengan `podman compose up -d db`), lalu:
```powershell
.\venv\Scripts\Activate.ps1
pip install -r mcp_server\requirements.txt
python mcp_server\init_db.py
python mcp_server\server.py --transport sse
```
*(Sesuaikan `MCP_SERVER_URL=http://localhost:8000/sse` atau port yang dipakai bila menjalankan backend secara lokal.)*

### 2. Jalankan Backend API
```powershell
cd backend
..\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn api:app --reload --port 8000
```

### 3. Jalankan Frontend React
```powershell
cd frontend
npm install
npm run dev
# Buka http://localhost:5173
```

### 4. Mode Terminal Interaktif (CLI - Opsional)
```powershell
cd backend
python main.py
```

---

## Evaluasi & Pertanyaan Uji Hukum

Gunakan daftar 17 pertanyaan uji resmi beserta dasar pasal UU No. 27 Tahun 2022 di:
- [`docs/evaluasi_tanya_jawab_uupdp.md`](docs/evaluasi_tanya_jawab_uupdp.md)

---

## Troubleshooting

1. **`ORCHESTRATOR_PROVIDER '...' tidak valid`**:
   Pastikan `ORCHESTRATOR_PROVIDER` di [`backend/.env`](backend/.env) hanya bernilai `dify` atau `langgraph`.
2. **`DIFY_API_KEY belum dikonfigurasi` / `401 Access token is invalid`**:
   Isi `DIFY_API_KEY` yang valid pada [`backend/.env`](backend/.env) (menu *API Access* $\rightarrow$ *API Keys* di dashboard Dify).
3. **`GEMINI_API_KEY belum dikonfigurasi`**:
   Untuk mode `langgraph`, isi `GEMINI_API_KEY` di [`backend/.env`](backend/.env) (LLM) dan [`mcp_server/.env`](mcp_server/.env) (embedding `pgvector`).
4. **Tabel `uupdp_dokumen` masih kosong (0 baris)**:
   Pastikan `GEMINI_API_KEY` sudah diisi di [`mcp_server/.env`](mcp_server/.env), lalu jalankan ulang `podman compose restart mcp_server` agar proses `init_db.py` meng-ingest 188 chunk naskah UU PDP secara otomatis.
5. **Timeout 120 detik pada Dify API**:
   Periksa tab *Logs & Annotations* di Dify Server untuk melihat node workflow yang melambat.
