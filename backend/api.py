import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Pastikan Root Direktori terdaftar di sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.agent.workflow import mcp_rag_chain
from config.settings import settings
from mcp_server.migrations.runner import run_migrations

app = FastAPI(
    title="Skripsi SVM AI Chatbot API",
    version="1.0.0",
    description="API Gateway untuk Chatbot RAG berbasis MCP & PostgreSQL pgvector",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str


class ChatResponse(BaseModel):
    answer: str
    citations: list[str]


@app.on_event("startup")
def startup_event():
    """Pastikan database dan ekstensi pgvector siap saat server dinyalakan."""
    run_migrations()


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "Backend RAG MCP API"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    if not request.question.strip():
        raise HTTPException(
            status_code=400, detail="Pertanyaan tidak boleh kosong."
        )

    try:
        result = await mcp_rag_chain(request.question)
        return ChatResponse(
            answer=result["answer"], citations=result["citations"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api:app", host="0.0.0.0", port=8000, reload=True)
