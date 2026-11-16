import os

from config.settings import settings
from orchestrators.base import BaseOrchestrator
from orchestrators.dify_provider import DifyProvider
from orchestrators.langgraph_provider import LangGraphProvider

_PROVIDER_REGISTRY: dict[str, type[BaseOrchestrator]] = {
    "dify": DifyProvider,
    "langgraph": LangGraphProvider,
}


def get_orchestrator() -> BaseOrchestrator:
    """
    Factory Strategy Pattern: membaca ORCHESTRATOR_PROVIDER dari environment
    lalu mengembalikan instance provider yang sesuai ('dify' atau 'langgraph').
    """
    settings.reload()
    provider = (
        os.getenv("ORCHESTRATOR_PROVIDER")
        or settings.ORCHESTRATOR_PROVIDER
        or "dify"
    ).strip().lower()

    provider_cls = _PROVIDER_REGISTRY.get(provider)
    if provider_cls is None:
        valid_options = ", ".join(sorted(_PROVIDER_REGISTRY.keys()))
        raise ValueError(
            f"ORCHESTRATOR_PROVIDER '{provider}' tidak valid. "
            f"Pilih salah satu opsi yang didukung: {valid_options}."
        )

    return provider_cls()


__all__ = ["get_orchestrator"]
