"""
Entry point utama Chatbot Skripsi SVM RAG (MCP & PostgreSQL pgvector).
Dapat dijalankan langsung dengan:
    python main.py
atau
    python -m backend.main
"""
import asyncio
import sys
from pathlib import Path

# Pastikan Root Direktori terdaftar di sys.path
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.main import bootstrap, run_chat


if __name__ == "__main__":
    bootstrap()
    asyncio.run(run_chat())

