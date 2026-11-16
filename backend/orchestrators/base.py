import logging
from abc import ABC, abstractmethod
from typing import Any
import httpx
from pydantic import BaseModel, Field


class OrchestratorResponse(BaseModel):
    """Skema respons standar untuk seluruh provider orkestrator chatbot."""

    answer: str
    conversation_id: str
    citations: list[dict] = Field(default_factory=list)
    provider_used: str


class BaseOrchestrator(ABC):
    """Abstract Base Class (Strategy interface) untuk penyedia orkestrator chat."""

    @abstractmethod
    async def ainvoke(
        self,
        query: str,
        user_id: str,
        conversation_id: str | None = None,
    ) -> OrchestratorResponse:
        """Memproses pertanyaan pengguna dan mengembalikan OrchestratorResponse."""


def raise_provider_http_error(
    provider_name: str,
    url: str,
    exc: Exception,
    logger: logging.Logger,
) -> None:
    """Menerjemahkan exception httpx menjadi pesan RuntimeError yang jelas dan seragam."""
    if isinstance(exc, httpx.TimeoutException):
        msg = f"Waktu tunggu pemrosesan {provider_name} API terlampaui (timeout 120 detik) pada URL: {url}."
        logger.error(msg)
        raise RuntimeError(msg) from exc

    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        try:
            err_json: Any = exc.response.json()
            detail_msg = (
                err_json.get("message")
                or err_json.get("detail")
                or err_json.get("error")
                or err_json.get("code")
                or exc.response.text
            )
        except Exception:
            detail_msg = exc.response.text
        msg = f"{provider_name} API error {status_code}: {detail_msg}"
        logger.error(msg)
        raise RuntimeError(msg) from exc

    if isinstance(exc, httpx.RequestError):
        msg = f"Gagal terhubung ke {provider_name} API ({url}): {exc}"
        logger.error(msg)
        raise RuntimeError(msg) from exc

    raise exc
