from typing import Any, Dict, List

from orchestrators.dify_provider import DifyProvider


async def query_dify_workflow(
    query: str,
    user_id: str,
    conversation_id: str = "",
) -> Dict[str, Any]:
    """
    Wrapper kompatibilitas untuk memanggil DifyProvider secara langsung.
    """
    res = await DifyProvider().ainvoke(
        query=query,
        user_id=user_id,
        conversation_id=conversation_id,
    )
    citations: List[str] = [
        str(c.get("label") or c.get("document_name") or "Dokumen Referensi")
        for c in (res.citations or [])
    ]
    return {
        "answer": res.answer,
        "conversation_id": res.conversation_id,
        "citations": citations,
        "provider_used": res.provider_used,
    }


__all__ = ["query_dify_workflow"]
