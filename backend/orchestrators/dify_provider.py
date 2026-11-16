import logging
import uuid
from typing import Any
import httpx

from config.settings import settings
from orchestrators.base import (
    BaseOrchestrator,
    OrchestratorResponse,
    raise_provider_http_error,
)

logger = logging.getLogger("orchestrators.dify")


def _map_dify_citations(metadata: Any) -> list[dict]:
    """Memetakan metadata.retriever_resources dari Dify menjadi list[dict] standar."""
    if not isinstance(metadata, dict):
        return []

    resources = metadata.get("retriever_resources")
    if not isinstance(resources, list):
        return []

    citations: list[dict] = []
    seen_labels: set[str] = set()

    for item in resources:
        if not isinstance(item, dict):
            continue

        doc_name = str(
            item.get("document_name")
            or item.get("dataset_name")
            or item.get("segment_id")
            or "Dokumen Referensi"
        )
        raw_score = item.get("score")
        score_val: float | None = None
        if raw_score is not None:
            try:
                score_val = float(raw_score)
            except (ValueError, TypeError):
                score_val = None

        label = f"{doc_name} (Skor: {score_val:.2f})" if score_val is not None else doc_name
        if label in seen_labels:
            continue
        seen_labels.add(label)

        citations.append({
            "document_name": doc_name,
            "score": score_val,
            "content": item.get("content", ""),
            "label": label,
        })

    return citations


class DifyProvider(BaseOrchestrator):
    """Strategy provider untuk orkestrator eksternal Dify Chatflow API."""

    async def ainvoke(
        self,
        query: str,
        user_id: str,
        conversation_id: str | None = None,
    ) -> OrchestratorResponse:
        settings.reload()
        api_url = (settings.DIFY_API_URL or "").strip()
        api_key = (settings.DIFY_API_KEY or "").strip()

        if not api_url:
            raise ValueError("DIFY_API_URL belum dikonfigurasi di backend/.env.")

        if not api_key or api_key in ("your_dify_api_key_here", "<isi_dengan_api_key_dify>"):
            raise ValueError(
                "DIFY_API_KEY belum dikonfigurasi di backend/.env. "
                "Masukkan API key Dify Chatflow Anda."
            )

        clean_conv_id = (conversation_id or "").strip()
        clean_user_id = (user_id or "default_user").strip()

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "inputs": {},
            "query": query,
            "response_mode": "blocking",
            "conversation_id": clean_conv_id,
            "user": clean_user_id,
        }

        timeout = httpx.Timeout(120.0, connect=10.0)
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(api_url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.RequestError) as exc:
            raise_provider_http_error("Dify", api_url, exc, logger)

        answer = str(data.get("answer", "") or "")
        returned_conv_id = str(data.get("conversation_id") or clean_conv_id or uuid.uuid4())
        citations = _map_dify_citations(data.get("metadata"))

        return OrchestratorResponse(
            answer=answer,
            conversation_id=returned_conv_id,
            citations=citations,
            provider_used="dify",
        )
