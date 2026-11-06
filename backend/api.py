import os
import sys
import uuid
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Pastikan root direktori terdaftar di sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.agent.workflow import mcp_rag_chain
from mcp_server.migrations.runner import run_migrations

app = FastAPI(
    title="Skripsi SVM Knowledge Assistant API",
    description="Backend API berbasis FastAPI, MCP (Model Context Protocol), Ollama, dan pgvector",
    version="1.0.0",
)

# ---------------------------------------------------------
# Konfigurasi CORS
# ---------------------------------------------------------
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------
# In-Memory Task Store untuk Async Polling
# ---------------------------------------------------------
TASKS_STORE: Dict[str, Dict[str, Any]] = {}


# ---------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------
class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    citations: List[str] = []


class AsyncTaskResponse(BaseModel):
    task_id: str
    status: str


class TaskStatusResponse(BaseModel):
    status: str
    answer: Optional[str] = None
    citations: Optional[List[str]] = None
    detail: Optional[str] = None


# ---------------------------------------------------------
# Startup Event
# ---------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    """Menjalankan migrasi tabel database pgvector saat backend pertama kali aktif."""
    try:
        run_migrations()
        print("INFO:     [DB] Migrasi tabel database skripsi_dokumen berhasil diverifikasi.")
    except Exception as e:
        print(f"WARNING:  [DB] Gagal menjalankan migrasi otomatis: {e}")


# ---------------------------------------------------------
# Health Check Endpoints (Mendukung /api/health dan /health)
# ---------------------------------------------------------
@app.get("/api/health", tags=["Health"])
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "service": "Skripsi SVM Assistant Backend",
        "mcp_protocol": "FastMCP Stdio",
    }


# ---------------------------------------------------------
# 1. Direct Synchronous Chat Endpoint
# ---------------------------------------------------------
@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_direct(payload: ChatRequest):
    """
    Menerima pertanyaan dan memproses RAG secara langsung (blocking).
    Gunakan timeout panjang di sisi client (misal: 90 detik).
    """
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Pertanyaan tidak boleh kosong.")

    try:
        result = await mcp_rag_chain(payload.question)
        return ChatResponse(
            answer=result.get("answer", "Tidak ada respon yang dihasilkan."),
            citations=result.get("citations", []),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan pada alur RAG / MCP: {str(exc)}",
        )


# ---------------------------------------------------------
# 2. Asynchronous Job Endpoints (Bebas Timeout)
# ---------------------------------------------------------
async def process_rag_job(task_id: str, question: str):
    """Berjalan sepenuhnya di latar belakang."""
    try:
        result = await mcp_rag_chain(question)
        TASKS_STORE[task_id] = {
            "status": "completed",
            "answer": result.get("answer", "Tidak ada respon yang dihasilkan."),
            "citations": result.get("citations", []),
        }
    except Exception as exc:
        TASKS_STORE[task_id] = {
            "status": "failed",
            "detail": str(exc),
        }

@app.post("/api/chat/async", response_model=AsyncTaskResponse, tags=["Chat Async"])
async def chat_async_start(payload: ChatRequest, background_tasks: BackgroundTasks):
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Pertanyaan tidak boleh kosong.")

    task_id = str(uuid.uuid4())
    TASKS_STORE[task_id] = {"status": "processing"}

    # Jadwalkan pekerjaan di background tanpa menahan respons return
    background_tasks.add_task(process_rag_job, task_id, payload.question)

    # Mengembalikan respons seketika
    return AsyncTaskResponse(task_id=task_id, status="processing")


@app.get("/api/chat/status/{task_id}", response_model=TaskStatusResponse, tags=["Chat Async"])
async def get_chat_task_status(task_id: str):
    """
    Frontend melakukan polling ke endpoint ini tiap 1-2 detik
    hingga status berubah menjadi 'completed' atau 'failed'.
    """
    task = TASKS_STORE.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="ID pekerjaan tidak ditemukan.")

    return TaskStatusResponse(
        status=task.get("status", "processing"),
        answer=task.get("answer"),
        citations=task.get("citations"),
        detail=task.get("detail"),
    )