import os
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Pastikan direktori backend terdaftar di sys.path baik dijalankan dari root maupun backend/
BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config.settings import settings
from orchestrators.factory import get_orchestrator

app = FastAPI(
    title="UU PDP Assistant API",
    description=(
        "Backend API berbasis FastAPI dengan Strategy Pattern Multi-Orchestrator "
        "(Dify & LangGraph) untuk tanya jawab UU No. 27 Tahun 2022 tentang "
        "Pelindungan Data Pribadi."
    ),
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-Memory Task Store untuk pola Async Polling
TASKS_STORE: Dict[str, Dict[str, Any]] = {}


# ---------------------------------------------------------
# Pydantic Schemas (Kompatibel dengan Frontend React)
# ---------------------------------------------------------
class ChatRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None
    user: Optional[str] = None
    provider: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    conversation_id: Optional[str] = None
    citations: List[str] = []
    provider_used: Optional[str] = None


class AsyncTaskResponse(BaseModel):
    task_id: str
    status: str


class TaskStatusResponse(BaseModel):
    status: str
    answer: Optional[str] = None
    conversation_id: Optional[str] = None
    citations: Optional[List[str]] = None
    provider_used: Optional[str] = None
    detail: Optional[str] = None


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def _format_citations_for_frontend(citations: List[Dict[str, Any]]) -> List[str]:
    """
    Mengonversi citations list[dict] dari OrchestratorResponse menjadi list[str]
    agar langsung kompatibel dengan komponen React CitationBadge.jsx.
    """
    formatted: List[str] = []
    seen: set[str] = set()

    for item in citations or []:
        if isinstance(item, str):
            label = item.strip()
        elif isinstance(item, dict):
            label = str(item.get("label") or "").strip()
            if not label:
                doc_name = str(
                    item.get("document_name")
                    or item.get("bab")
                    or item.get("pasal")
                    or "Dokumen Referensi"
                ).strip()
                score = item.get("score")
                if score is not None:
                    try:
                        label = f"{doc_name} (Skor: {float(score):.2f})"
                    except (ValueError, TypeError):
                        label = doc_name
                else:
                    label = doc_name
        else:
            continue

        if label and label not in seen:
            seen.add(label)
            formatted.append(label)

    return formatted


async def _run_orchestrator_chat(
    question: str,
    user_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    """Menjalankan orkestrator aktif via Factory Strategy Pattern."""
    orchestrator = get_orchestrator(provider_override=provider)
    uid = user_id or f"user_{uuid.uuid4().hex[:8]}"
    result = await orchestrator.ainvoke(
        query=question,
        user_id=uid,
        conversation_id=conversation_id,
    )
    return {
        "answer": result.answer or "Tidak ada respon yang dihasilkan.",
        "conversation_id": result.conversation_id,
        "citations": _format_citations_for_frontend(result.citations),
        "provider_used": result.provider_used,
    }


# ---------------------------------------------------------
# Health Check
# ---------------------------------------------------------
@app.get("/api/health", tags=["Health"])
@app.get("/health", tags=["Health"])
async def health_check():
    settings.reload()
    return {
        "status": "ok",
        "service": "UU PDP Knowledge Assistant Backend",
        "orchestrator_provider": settings.ORCHESTRATOR_PROVIDER,
        "engine": f"Multi-Orchestrator ({settings.ORCHESTRATOR_PROVIDER})",
        "dify_url": settings.DIFY_API_URL,
    }


# ---------------------------------------------------------
# 1. Direct (Blocking) Chat Endpoint
# ---------------------------------------------------------
@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_direct(payload: ChatRequest):
    """Meneruskan pertanyaan ke orkestrator aktif secara langsung (blocking)."""
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Pertanyaan tidak boleh kosong.")

    try:
        data = await _run_orchestrator_chat(
            question=payload.question,
            user_id=payload.user,
            conversation_id=payload.conversation_id,
            provider=payload.provider,
        )
        return ChatResponse(**data)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan pada alur orkestrator: {str(exc)}",
        )


# ---------------------------------------------------------
# 2. Async Polling Endpoints
# ---------------------------------------------------------
async def _process_chat_job(
    task_id: str,
    question: str,
    conversation_id: Optional[str] = None,
    user_id: Optional[str] = None,
    provider: Optional[str] = None,
):
    """Background task — mengeksekusi orkestrator aktif secara asinkron."""
    try:
        data = await _run_orchestrator_chat(
            question=question,
            user_id=user_id,
            conversation_id=conversation_id,
            provider=provider,
        )
        TASKS_STORE[task_id] = {
            "status": "completed",
            **data,
        }
    except Exception as exc:
        TASKS_STORE[task_id] = {"status": "failed", "detail": str(exc)}


# Alias untuk kompatibilitas backward
_process_dify_job = _process_chat_job


@app.post("/api/chat/async", response_model=AsyncTaskResponse, tags=["Chat Async"])
async def chat_async_start(payload: ChatRequest, background_tasks: BackgroundTasks):
    """Inisiasi pekerjaan async — langsung kembalikan task_id untuk polling."""
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Pertanyaan tidak boleh kosong.")

    if payload.provider:
        try:
            get_orchestrator(provider_override=payload.provider)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    task_id = str(uuid.uuid4())
    TASKS_STORE[task_id] = {"status": "processing"}

    background_tasks.add_task(
        _process_chat_job,
        task_id,
        payload.question,
        payload.conversation_id,
        payload.user,
        payload.provider,
    )
    return AsyncTaskResponse(task_id=task_id, status="processing")


@app.get("/api/chat/status/{task_id}", response_model=TaskStatusResponse, tags=["Chat Async"])
async def get_chat_status(task_id: str):
    """Frontend polling endpoint — cek status task hingga 'completed' atau 'failed'."""
    task = TASKS_STORE.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="ID pekerjaan tidak ditemukan.")

    return TaskStatusResponse(
        status=task.get("status", "processing"),
        answer=task.get("answer"),
        conversation_id=task.get("conversation_id"),
        citations=task.get("citations"),
        provider_used=task.get("provider_used"),
        detail=task.get("detail"),
    )
