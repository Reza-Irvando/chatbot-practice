import os
from pathlib import Path

try:
    from dotenv import dotenv_values
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
ENV_FILE = BACKEND_DIR / ".env"


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


class Settings:
    """
    Konfigurasi terpusat microservice backend — orkestrator Dify & LangGraph,
    Google Gemini API (Flash-Lite), dan URL koneksi ke microservice mcp_server.
    """

    def __init__(self):
        self._env_mtime: float | None = None
        self._initialized: bool = False
        self._container_mcp_url: str | None = None
        self.reload()

    def _sync_env_file(self) -> None:
        current_mtime = ENV_FILE.stat().st_mtime if ENV_FILE.exists() else None

        if not self._initialized:
            self._initialized = True
            self._env_mtime = current_mtime
            if os.environ.get("MCP_SERVER_URL") == "http://mcp_server:8000/sse":
                self._container_mcp_url = "http://mcp_server:8000/sse"
            for key, val in _parse_env_file(ENV_FILE).items():
                if key not in os.environ or (os.environ.get(key, "") == "" and val != ""):
                    os.environ[key] = val
            return

        if current_mtime != self._env_mtime:
            self._env_mtime = current_mtime
            for key, val in _parse_env_file(ENV_FILE).items():
                if key == "MCP_SERVER_URL" and self._container_mcp_url:
                    os.environ["MCP_SERVER_URL"] = self._container_mcp_url
                else:
                    os.environ[key] = val

    def reload(self) -> None:
        self._sync_env_file()

        # 1. Pilihan Orchestrator Provider: dify | langgraph
        self.ORCHESTRATOR_PROVIDER: str = (
            os.getenv("ORCHESTRATOR_PROVIDER", "dify") or "dify"
        ).strip().lower()

        # 2. Dify Chatflow API
        self.DIFY_API_URL: str = os.getenv(
            "DIFY_API_URL", "http://172.16.12.98/v1/chat-messages"
        )
        self.DIFY_API_KEY: str = os.getenv("DIFY_API_KEY", "")

        # 3. MCP Server SSE & Google Gemini API (Flash-Lite)
        self.MCP_SERVER_URL: str = os.getenv("MCP_SERVER_URL", "http://mcp_server:8000/sse")
        self.GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
        self.GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
        self.MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", "1024") or "1024")

        # 4. Server & CORS
        self.PORT: int = int(os.getenv("PORT", "8000") or "8000")
        cors_raw = os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        )
        self.CORS_ORIGINS: list[str] = [
            origin.strip() for origin in cors_raw.split(",") if origin.strip()
        ]

    def __repr__(self) -> str:
        return (
            f"<Settings ORCHESTRATOR={self.ORCHESTRATOR_PROVIDER} "
            f"GEMINI_MODEL={self.GEMINI_MODEL} MCP={self.MCP_SERVER_URL} PORT={self.PORT}>"
        )


settings = Settings()

__all__ = ["Settings", "settings", "BACKEND_DIR", "PROJECT_ROOT", "ENV_FILE"]
