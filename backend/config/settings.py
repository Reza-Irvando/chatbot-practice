import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

# Direktori backend (di mana settings.py ini berada: backend/config/)
BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BACKEND_DIR / ".env"


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


def _load_env(override: bool = False):
    if ENV_FILE.exists():
        if HAS_DOTENV:
            load_dotenv(dotenv_path=ENV_FILE, override=override)
        else:
            _manual_load_env(ENV_FILE, override=override)


# Muat saat module pertama kali diimpor
_load_env(override=False)


class Settings:
    """Konfigurasi terpusat backend — dibaca dari backend/.env atau env vars."""

    def __init__(self):
        self.reload()

    def reload(self):
        """Muat ulang nilai dari environment variables (dan backend/.env)."""
        _load_env(override=True)

        # Dify Chatflow API
        self.DIFY_API_URL: str = os.getenv(
            "DIFY_API_URL", "http://172.16.12.98/v1/chat-messages"
        )
        self.DIFY_API_KEY: str = os.getenv("DIFY_API_KEY", "")

        # Server
        self.PORT: int = int(os.getenv("PORT", "8000"))

        # CORS — koma-separated list
        cors_raw = os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        )
        self.CORS_ORIGINS: list[str] = [
            o.strip() for o in cors_raw.split(",") if o.strip()
        ]

    def __repr__(self) -> str:
        return f"<Settings DIFY_URL={self.DIFY_API_URL} PORT={self.PORT}>"


settings = Settings()

__all__ = ["Settings", "settings"]
