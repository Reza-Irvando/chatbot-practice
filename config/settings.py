import os
from pathlib import Path
from dotenv import load_dotenv

# Root direktori proyek & path ke .env
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

# Muat file .env ke environment variables sistem
if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE, override=False)


class Settings:
    """
    Konfigurasi terpusat yang membaca nilai dari .env menggunakan os.getenv,
    bukan hardcode.
    """

    def __init__(self):
        self.reload()

    def reload(self):
        """Muat ulang environment variables dari file .env."""
        if ENV_FILE.exists():
            load_dotenv(dotenv_path=ENV_FILE, override=False)

        # 1. Konfigurasi Database PostgreSQL & pgvector
        self.DB_HOST: str = os.getenv("DB_HOST", "localhost")
        self.DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
        self.DB_NAME: str = os.getenv("DB_NAME", "chatbot_practice")
        self.DB_USER: str = os.getenv("DB_USER", "postgres")
        self.DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")

        # 2. Konfigurasi Ollama (LLM & Embeddings)
        self.OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3.2")
        # Mendukung EMBED_MODEL atau EMBEDDING_MODEL
        self.EMBED_MODEL: str = os.getenv("EMBED_MODEL") or os.getenv("EMBEDDING_MODEL", "nomic-embed-text")
        self.EMBEDDING_MODEL: str = self.EMBED_MODEL
        self.EMBED_DIMENSION: int = int(os.getenv("EMBED_DIMENSION", "768"))

        # 3. Parameter Pencarian RAG
        self.TOP_K_RESULTS: int = int(os.getenv("TOP_K_RESULTS", "3"))
        self.SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.3"))

        # 4. CORS Origins (opsional, diambil dari .env)
        cors_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000")
        self.CORS_ORIGINS: list[str] = [
            origin.strip() for origin in cors_raw.split(",") if origin.strip()
        ]

    def __repr__(self) -> str:
        return (
            f"<Settings DB={self.DB_USER}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME} "
            f"OLLAMA={self.OLLAMA_BASE_URL} LLM={self.LLM_MODEL} EMBED={self.EMBED_MODEL}>"
        )


settings = Settings()

__all__ = ["Settings", "settings"]
