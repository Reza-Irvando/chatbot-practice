import os
import uuid
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from dify_client import query_dify_workflow
from config.settings import settings

app = FastAPI(
    title="UU PDP Assistant API",
    description="Backend API berbasis FastAPI terintegrasi dengan Dify Chatflow untuk tanya jawab UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi.",
    version="2.0.0",
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
# Pydantic Schemas
# ---------------------------------------------------------
class ChatRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None
    user: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    conversation_id: Optional[str] = None
    citations: List[str] = []


class AsyncTaskResponse(BaseModel):
    task_id: str
    status: str


class TaskStatusResponse(BaseModel):
    status: str
    answer: Optional[str] = None
    conversation_id: Optional[str] = None
    citations: Optional[List[str]] = None
    detail: Optional[str] = None


# ---------------------------------------------------------
# Health Check
# ---------------------------------------------------------
@app.get("/api/health", tags=["Health"])
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "service": "UU PDP Knowledge Assistant Backend",
        "engine": "Dify Chatflow API",
        "dify_url": settings.DIFY_API_URL,
    }


# ---------------------------------------------------------
# 1. Direct (Blocking) Chat Endpoint
# ---------------------------------------------------------
@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_direct(payload: ChatRequest):
    """Meneruskan pertanyaan ke Dify Chatflow secara blocking (timeout panjang)."""
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Pertanyaan tidak boleh kosong.")

    try:
        user_id = payload.user or f"user_{uuid.uuid4().hex[:8]}"
        result = await query_dify_workflow(
            query=payload.question,
            user_id=user_id,
            conversation_id=payload.conversation_id or "",
        )
        return ChatResponse(
            answer=result.get("answer", "Tidak ada respon yang dihasilkan."),
            conversation_id=result.get("conversation_id"),
            citations=result.get("citations", []),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan pada alur Dify Chatflow: {str(exc)}",
        )


# ---------------------------------------------------------
# 2. Async Polling Endpoints
# ---------------------------------------------------------
async def _process_dify_job(
    task_id: str,
    question: str,
    conversation_id: Optional[str] = None,
    user_id: Optional[str] = None,
):
    """Background task — meneruskan chat ke Dify Chatflow."""
    try:
        uid = user_id or f"user_{uuid.uuid4().hex[:8]}"
        result = await query_dify_workflow(
            query=question,
            user_id=uid,
            conversation_id=conversation_id or "",
        )
        TASKS_STORE[task_id] = {
            "status": "completed",
            "answer": result.get("answer", "Tidak ada respon yang dihasilkan."),
            "conversation_id": result.get("conversation_id"),
            "citations": result.get("citations", []),
        }
    except Exception as exc:
        TASKS_STORE[task_id] = {"status": "failed", "detail": str(exc)}


@app.post("/api/chat/async", response_model=AsyncTaskResponse, tags=["Chat Async"])
async def chat_async_start(payload: ChatRequest, background_tasks: BackgroundTasks):
    """Inisiasi pekerjaan async — langsung kembalikan task_id untuk polling."""
    if not payload.question.strip():
        raise HTTPException(status_code=400, detail="Pertanyaan tidak boleh kosong.")

    task_id = str(uuid.uuid4())
    TASKS_STORE[task_id] = {"status": "processing"}

    background_tasks.add_task(
        _process_dify_job,
        task_id,
        payload.question,
        payload.conversation_id,
        payload.user,
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
        detail=task.get("detail"),
    )
