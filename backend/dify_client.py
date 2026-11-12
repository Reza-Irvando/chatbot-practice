import logging
from typing import Any, Dict, List, Optional
import httpx

from config.settings import settings

logger = logging.getLogger("dify_client")


def _format_citations(metadata: Optional[Dict[str, Any]]) -> List[str]:
    """Mengekstrak sumber referensi dokumen dari metadata.retriever_resources Dify."""
    citations: List[str] = []
    if not metadata or not isinstance(metadata, dict):
        return citations

    resources = metadata.get("retriever_resources")
    if not resources or not isinstance(resources, list):
        return citations

    for item in resources:
        if not isinstance(item, dict):
            continue
        doc_name = (
            item.get("document_name")
            or item.get("dataset_name")
            or item.get("segment_id")
            or "Dokumen Referensi"
        )
        score = item.get("score")
        if score is not None:
            try:
                label = f"{doc_name} (Skor: {float(score):.2f})"
            except (ValueError, TypeError):
                label = str(doc_name)
        else:
            label = str(doc_name)
        citations.append(label)

    # Hilangkan duplikat, jaga urutan
    return list(dict.fromkeys(citations))


async def query_dify_workflow(
    query: str,
    user_id: str,
    conversation_id: str = "",
) -> Dict[str, Any]:
    """
    Kirim query ke Dify Chatflow API (blocking mode).
    Kembalikan dict: answer, conversation_id, citations, raw_response.
    """
    settings.reload()
    api_url = settings.DIFY_API_URL
    api_key = settings.DIFY_API_KEY

    if not api_key or api_key.strip() in ("", "your_dify_api_key_here"):
        raise ValueError(
            "DIFY_API_KEY belum dikonfigurasi di backend/.env. "
            "Masukkan API key Dify Chatflow Anda."
        )

    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "Content-Type": "application/json",
    }

    payload: Dict[str, Any] = {
        "inputs": {},
        "query": query,
        "response_mode": "blocking",
        "user": user_id or "default_user",
    }

    clean_conv_id = (conversation_id or "").strip()
    if clean_conv_id:
        payload["conversation_id"] = clean_conv_id

    timeout = httpx.Timeout(120.0, connect=10.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(api_url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

    except httpx.TimeoutException as exc:
        msg = f"Timeout 120 detik terlampaui saat memanggil Dify API ({api_url})."
        logger.error(msg)
        raise RuntimeError(msg) from exc

    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        try:
            err_json = exc.response.json()
            detail_msg = err_json.get("message") or err_json.get("detail") or exc.response.text
        except Exception:
            detail_msg = exc.response.text
        msg = f"Dify API error {status_code}: {detail_msg}"
        logger.error(msg)
        raise RuntimeError(msg) from exc

    except httpx.RequestError as exc:
        msg = f"Gagal terhubung ke Dify API ({api_url}): {exc}"
        logger.error(msg)
        raise RuntimeError(msg) from exc

    return {
        "answer": data.get("answer", ""),
        "conversation_id": data.get("conversation_id", clean_conv_id),
        "citations": _format_citations(data.get("metadata")),
        "raw_response": data,
    }


__all__ = ["query_dify_workflow"]
