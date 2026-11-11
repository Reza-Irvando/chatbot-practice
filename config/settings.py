import os
from pathlib import Path

# Root direktori proyek & path ke .env
PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False


def _manual_load_env(path: Path, override: bool = False):
    """Fallback parser sederhana jika python-dotenv belum terpasang."""
    if not path.exists():
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                key, val = key.strip(), val.strip().strip("'\"")
                if override or key not in os.environ:
                    os.environ[key] = val


# Muat file .env ke environment variables sistem
if ENV_FILE.exists():
    if HAS_DOTENV:
        load_dotenv(dotenv_path=ENV_FILE, override=False)
    else:
        _manual_load_env(ENV_FILE, override=False)


class Settings:
    """
    Konfigurasi terpusat yang membaca nilai dari .env menggunakan os.getenv
    dengan fallback default yang aman.
    """

    def __init__(self):
        self.reload()

    def reload(self):
        """Muat ulang environment variables dari file .env."""
        if ENV_FILE.exists():
            if HAS_DOTENV:
                load_dotenv(dotenv_path=ENV_FILE, override=True)
            else:
                _manual_load_env(ENV_FILE, override=True)

        # 1. Konfigurasi Database PostgreSQL & pgvector
        self.DB_HOST: str = os.getenv("DB_HOST", "localhost")
        self.DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
        self.DB_NAME: str = os.getenv("DB_NAME", "chatbot_db")
        self.DB_USER: str = os.getenv("DB_USER", "postgres")
        self.DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")

        # 2. Pilihan LLM Provider ('gemini' atau 'ollama')
        self.LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini")

        # 3. Konfigurasi Google Gemini API
        self.GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
        self.GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

        # 4. Konfigurasi Ollama (LLM Lokal & Embeddings pgvector)
        self.OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.LLM_MODEL: str = os.getenv("LLM_MODEL", "llama3.2")
        # Mendukung EMBED_MODEL atau EMBEDDING_MODEL
        self.EMBED_MODEL: str = (
            os.getenv("EMBED_MODEL")
            or os.getenv("EMBEDDING_MODEL")
            or "nomic-embed-text"
        )
        self.EMBEDDING_MODEL: str = self.EMBED_MODEL
        self.EMBED_DIMENSION: int = int(os.getenv("EMBED_DIMENSION", "768"))

        # 3. Parameter Pencarian RAG & Knowledge UU PDP
        self.TOP_K_RESULTS: int = int(os.getenv("TOP_K_RESULTS", "5"))
        self.SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.40"))
        self.MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "600"))
        self.DOC_TABLE_NAME: str = os.getenv("DOC_TABLE_NAME", "uupdp_dokumen")

        pdf_path_env = os.getenv("PDF_PATH", "data/UU_No_27_Tahun_2022_PDP.pdf")
        self.PDF_PATH: Path = (
            Path(pdf_path_env) if Path(pdf_path_env).is_absolute() else PROJECT_ROOT / pdf_path_env
        )

        # Parameter Chunking RAG untuk Dokumen Perundang-undangan
        self.CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000"))
        self.CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "150"))

        # 4. CORS Origins (opsional, diambil dari .env)
        cors_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
        self.CORS_ORIGINS: list[str] = [
            origin.strip() for origin in cors_raw.split(",") if origin.strip()
        ]

    def __repr__(self) -> str:
        llm_info = (
            f"Gemini({self.GEMINI_MODEL})"
            if self.LLM_PROVIDER == "gemini"
            else f"Ollama({self.LLM_MODEL})"
        )
        return (
            f"<Settings DB={self.DB_USER}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME} "
            f"TABLE={self.DOC_TABLE_NAME} PROVIDER={self.LLM_PROVIDER} "
            f"LLM={llm_info} EMBED={self.EMBED_MODEL}>"
        )


settings = Settings()

__all__ = ["Settings", "settings", "PROJECT_ROOT"]
