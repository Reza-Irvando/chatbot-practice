import os
from pathlib import Path

try:
    from dotenv import dotenv_values
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

MCP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MCP_DIR.parent
ENV_FILE = MCP_DIR / ".env"


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    if HAS_DOTENV:
        raw = dotenv_values(path)
        return {k: (v if v is not None else "") for k, v in raw.items()}

    parsed: dict[str, str] = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, val = line.split("=", 1)
                parsed[key.strip()] = val.strip().strip("'\"")
    return parsed


def _resolve_default_pdf_path() -> Path:
    candidates = [
        MCP_DIR / "data" / "UU_No_27_Tahun_2022_PDP.pdf",
        PROJECT_ROOT / "data" / "UU_No_27_Tahun_2022_PDP.pdf",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


class MCPSettings:
    """Konfigurasi mandiri untuk microservice mcp_server (pgvector + Gemini Embedding)."""

    def __init__(self):
        self._env_mtime: float | None = None
        self._initialized: bool = False
        self._container_db_host: str | None = None
        self.reload()

    def _sync_env_file(self) -> None:
        current_mtime = ENV_FILE.stat().st_mtime if ENV_FILE.exists() else None

        if not self._initialized:
            self._initialized = True
            self._env_mtime = current_mtime
            if os.environ.get("DB_HOST") == "db":
                self._container_db_host = "db"
            for key, val in _parse_env_file(ENV_FILE).items():
                if key not in os.environ or (os.environ.get(key, "") == "" and val != ""):
                    os.environ[key] = val
            return

        if current_mtime != self._env_mtime:
            self._env_mtime = current_mtime
            for key, val in _parse_env_file(ENV_FILE).items():
                if key == "DB_HOST" and self._container_db_host == "db":
                    os.environ["DB_HOST"] = "db"
                else:
                    os.environ[key] = val

    def reload(self) -> None:
        self._sync_env_file()

        # Database PostgreSQL & pgvector
        self.DB_HOST: str = os.getenv("DB_HOST", "localhost")
        self.DB_PORT: int = int(os.getenv("DB_PORT", "5432") or "5432")
        self.DB_NAME: str = os.getenv("DB_NAME", "chatbot_db")
        self.DB_USER: str = os.getenv("DB_USER", "postgres")
        self.DB_PASSWORD: str = os.getenv("DB_PASSWORD", "postgres")
        self.DOC_TABLE_NAME: str = os.getenv("DOC_TABLE_NAME", "uupdp_dokumen")

        # Google Gemini Embedding
        self.GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
        self.EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "gemini-embedding-001")
        self.EMBED_DIMENSION: int = int(os.getenv("EMBED_DIMENSION", "768") or "768")

        # Parameter RAG & Chunking
        self.TOP_K_RESULTS: int = int(os.getenv("TOP_K_RESULTS", "5") or "5")
        self.SIMILARITY_THRESHOLD: float = float(
            os.getenv("SIMILARITY_THRESHOLD", "0.40") or "0.40"
        )
        self.CHUNK_SIZE: int = int(os.getenv("CHUNK_SIZE", "1000") or "1000")
        self.CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "150") or "150")

        pdf_env = os.getenv("PDF_PATH", "").strip()
        if pdf_env:
            p = Path(pdf_env)
            self.PDF_PATH: Path = (
                p if p.is_absolute() else (MCP_DIR / p if (MCP_DIR / p).exists() else PROJECT_ROOT / p)
            )
        else:
            self.PDF_PATH: Path = _resolve_default_pdf_path()

        # Server MCP
        self.MCP_HOST: str = os.getenv("MCP_HOST", "0.0.0.0")
        self.MCP_PORT: int = int(os.getenv("MCP_PORT", "8000") or "8000")
        self.MCP_TRANSPORT: str = os.getenv("MCP_TRANSPORT", "stdio")

    def __repr__(self) -> str:
        return (
            f"<MCPSettings DB={self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME} "
            f"EMBED={self.EMBEDDING_MODEL}({self.EMBED_DIMENSION}) PORT={self.MCP_PORT}>"
        )


settings = MCPSettings()

__all__ = ["MCPSettings", "settings", "MCP_DIR", "PROJECT_ROOT"]
