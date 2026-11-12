# Chatbot Asisten Hukum UU Perlindungan Data Pribadi (UU No. 27 Tahun 2022)

Aplikasi chatbot konsultasi hukum berbasis **Dify Chatflow API**, dibangun dengan arsitektur **microservice** terpisah antara Backend (FastAPI) dan Frontend (React + Vite).

---

## Struktur Proyek

```
chatbot-practice/
├── docker-compose.yml          # Orkestrasi dua microservice
├── README.md
├── docs/
│   └── evaluasi_tanya_jawab_uupdp.md
│
├── backend/                    # Microservice 1: FastAPI Proxy
│   ├── .env                    # ← Konfigurasi backend (tidak di-commit)
│   ├── .env.example            # Template konfigurasi backend
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── api.py                  # REST API (sync + async polling)
│   ├── dify_client.py          # HTTP client ke Dify Chatflow
│   ├── main.py                 # CLI interaktif (opsional)
│   └── config/
│       └── settings.py         # Pemuat env vars backend
│
└── frontend/                   # Microservice 2: React + Nginx
    ├── .env                    # ← Konfigurasi frontend (tidak di-commit)
    ├── .env.example            # Template konfigurasi frontend
    ├── Dockerfile              # Multi-stage: Vite build → Nginx (config inline)
    ├── package.json
    ├── vite.config.js
    └── src/
        ├── App.jsx
        ├── components/
        └── services/api.js
```

---

## Arsitektur Sistem

```
Browser / CLI
     │
     ▼
┌─────────────────────────────────────┐
│  Frontend React  (port 5173 / :80)  │
│  Nginx — proxy /api/ → backend:8000 │
└─────────────────────────────────────┘
     │  POST /api/chat/async
     │  GET  /api/chat/status/{id}
     ▼
┌─────────────────────────────────────┐
│  Backend FastAPI  (port 8000)       │
│  Async polling + background worker  │
└─────────────────────────────────────┘
     │  POST /v1/chat-messages (blocking)
     ▼
┌─────────────────────────────────────┐
│  Dify Chatflow (172.16.12.98)       │
│  Knowledge Base UU PDP + LLM        │
└─────────────────────────────────────┘
```

---

## Prasyarat

- **Dify Server** aktif dan dapat diakses di jaringan lokal
- **Dify API Key** dari aplikasi Chatflow yang sudah di-publish
- **Docker / Podman** (dengan compose) — untuk mode container
- **Python 3.10+** dan **Node.js 18+** — untuk mode lokal/manual

---

## Konfigurasi Environment

### Backend (`backend/.env`)
```env
DIFY_API_URL=http://172.16.12.98/v1/chat-messages
DIFY_API_KEY=app-xxxxxxxxxxxxxxxxxxxx
PORT=8000
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

### Frontend (`frontend/.env`)
```env
VITE_API_BASE_URL=/api
```

---

## Menjalankan dengan Docker / Podman

```powershell
# Build & jalankan kedua service sekaligus
podman compose up --build -d
# atau
docker compose up --build -d
```

| Service | URL |
|---|---|
| Web Chatbot | http://localhost:5173 |
| Backend API Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/api/health |

```powershell
# Lihat log
podman compose logs -f backend
podman compose logs -f frontend

# Hentikan
podman compose down
```

---

## Menjalankan Secara Lokal (Manual)

### Backend
```powershell
cd backend
# Aktifkan venv (dari root proyek)
..\venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn api:app --reload --port 8000
```

### Frontend
```powershell
cd frontend
npm install
npm run dev
# Buka http://localhost:5173
```

### CLI Interaktif (opsional)
```powershell
cd backend
python main.py
```

---

## Troubleshooting

### `DIFY_API_KEY belum dikonfigurasi`
Pastikan `backend/.env` berisi `DIFY_API_KEY=app-...` yang valid.

### `Dify API error 401: Access token is invalid`
API Key tidak valid atau kedaluwarsa — buat key baru di dashboard Dify.

### `Timeout 120 detik terlampaui`
Workflow Dify terlalu kompleks atau koneksi ke LLM provider lambat — periksa log eksekusi di tab *Logs & Annotations* pada dashboard Dify.
