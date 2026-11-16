import logging
import re
import sys
import uuid
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from config.settings import BACKEND_DIR, PROJECT_ROOT, settings
from orchestrators.base import BaseOrchestrator, OrchestratorResponse

logger = logging.getLogger("orchestrators.langgraph")

for _path in (str(PROJECT_ROOT), str(BACKEND_DIR)):
    if _path not in sys.path:
        sys.path.insert(0, _path)

MAX_LOOP_COUNT = 2

_GREETING_TOKEN = (
    r"(?:hai|halo|hello|hi|hey|selamat\s+(?:pagi|siang|sore|malam)|"
    r"assalamu\s*'?alaikum|waalaikum\s*salam|terima\s*kasih|makasih|"
    r"thanks|thank\s+you|apa\s+kabar|permisi|tes|test)"
)
_GREETING_PATTERN = re.compile(
    rf"^\s*{_GREETING_TOKEN}(?:[\s,!.?]+{_GREETING_TOKEN})*[!.,?\s]*$",
    re.IGNORECASE,
)

_LEGAL_KEYWORD_PATTERN = re.compile(
    r"\b(pasal|ayat|bab|uu|pdp|undang|data|pribadi|subjek|pengendali|"
    r"prosesor|kebocoran|bocor|gagal|kegagalan|sanksi|pidana|denda|"
    r"administratif|transfer|internasional|persetujuan|dpo|pejabat|"
    r"spesifik|umum|hak|kewajiban|larangan|lembaga|hukum)\b",
    re.IGNORECASE,
)

_SHARED_CHECKPOINTER = MemorySaver()


class WorkflowState(TypedDict):
    """
    State workflow Agentic RAG UU PDP selaras dengan diagram tmp/workflow.mmd:
    - query (sys.query)
    - current_query (variabel loop pencarian aktif)
    - is_found (variabel loop penanda relevansi ditemukan)
    - loop_count (penghitung putaran loop, Max Loop Count = 2)
    """

    messages: Annotated[list[AnyMessage], add_messages]
    query: str
    current_query: str
    is_found: bool
    loop_count: int
    route: str
    context: str
    citations: list[dict]
    grade: str
    answer: str


def _gemini_is_configured() -> bool:
    """Memeriksa apakah GEMINI_API_KEY sudah diisi di backend/.env."""
    settings.reload()
    return bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip())


def get_llm() -> ChatGoogleGenerativeAI:
    """
    Menginisialisasi model Google Gemini Flash-Lite terbaru sesuai konfigurasi .env.
    """
    settings.reload()
    api_key = (settings.GEMINI_API_KEY or "").strip()
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY belum dikonfigurasi di backend/.env. "
            "Silakan isi API Key Google AI Studio Anda untuk menjalankan LangGraph."
        )

    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL or "gemini-3.5-flash-lite",
        google_api_key=api_key,
        max_output_tokens=settings.MAX_TOKENS,
    )


def _extract_ai_text(resp: Any) -> str:
    """Mengekstrak teks bersih dari AIMessage (string maupun list of content blocks)."""
    content = getattr(resp, "content", resp)
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict):
                if block.get("type") == "thinking":
                    continue
                text_val = block.get("text")
                if isinstance(text_val, str) and text_val.strip():
                    parts.append(text_val)
        if parts:
            return "\n".join(parts).strip()
    text_prop = getattr(resp, "text", None)
    if isinstance(text_prop, str) and text_prop.strip():
        return text_prop.strip()
    return str(content).strip() if content is not None else ""


def _parse_citations_from_text(context_text: str) -> list[dict]:
    """Mengekstrak metadata sitasi terstruktur dari teks output MCP Server."""
    citations: list[dict] = []
    seen: set[str] = set()
    pattern = re.compile(
        r"\[(UU PDP No\. 27/2022 - [^\]]+)\](?:\s*\(Skor Relevansi:\s*([0-9.]+)\))?"
    )
    for match in pattern.finditer(context_text):
        title = match.group(1).strip()
        raw_score = match.group(2)
        score_val: float | None = None
        if raw_score is not None:
            try:
                score_val = float(raw_score)
            except ValueError:
                score_val = None
        label = f"{title} (Skor: {score_val:.2f})" if score_val is not None else title
        if label in seen:
            continue
        seen.add(label)
        citations.append({
            "document_name": title,
            "score": score_val,
            "label": label,
        })
    return citations


async def _retrieve_via_mcp_sse(query: str) -> tuple[str, list[dict]] | None:
    """Mencoba memanggil MCP Server eksternal via transport SSE bila URL aktif."""
    mcp_url = (settings.MCP_SERVER_URL or "").strip()
    if not mcp_url.startswith(("http://", "https://")):
        return None

    try:
        from mcp import ClientSession
        from mcp.client.sse import sse_client

        async with sse_client(url=mcp_url, timeout=5.0, sse_read_timeout=30.0) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "cari_pasal_dan_ketentuan_uupdp",
                    arguments={"pertanyaan": query},
                )
                if result.content:
                    text = str(result.content[0].text or "")
                    return text, _parse_citations_from_text(text)
    except Exception as exc:
        logger.debug("MCP SSE (%s) tidak terjangkau, mencoba fallback lokal: %s", mcp_url, exc)
    return None


def _retrieve_via_local_store(query: str) -> tuple[str, list[dict]]:
    """Fallback lokal bila dijalankan di luar container saat mcp_server tersedia di disk."""
    try:
        from mcp_server.vector_store import format_search_results, search_documents
    except ModuleNotFoundError:
        return (
            "Layanan MCP Server (MCP_SERVER_URL) belum terjangkau saat ini.",
            [],
        )

    results = search_documents(query)
    context_text = format_search_results(results)

    citations: list[dict] = []
    seen: set[str] = set()
    for r in results:
        bab = r.get("bab", "")
        pasal = r.get("pasal", "")
        title = f"{bab} - {pasal}".strip(" -") or r.get("judul", "UU No. 27/2022")
        score = float(r.get("score", 0.0))
        label = f"UU PDP No. 27/2022 - {title} (Skor: {score:.2f})"
        if label in seen:
            continue
        seen.add(label)
        citations.append({
            "document_name": f"UU PDP No. 27/2022 - {title}",
            "bab": bab,
            "pasal": pasal,
            "score": round(score, 4),
            "label": label,
        })
    return context_text, citations


# ---------------------------------------------------------
# Node Workflow (Selaras tmp/workflow.mmd)
# ---------------------------------------------------------
async def question_classifier_node(state: WorkflowState) -> dict[str, Any]:
    """QC: Memilah Sapaan/Obrolan Umum vs Pertanyaan Pasal/UU PDP & init variabel loop."""
    query = (state.get("query") or "").strip()
    base_init: dict[str, Any] = {
        "current_query": query,
        "is_found": False,
        "loop_count": 0,
        "context": "",
        "citations": [],
        "grade": "",
    }

    if _GREETING_PATTERN.match(query):
        return {**base_init, "route": "greeting"}

    if _LEGAL_KEYWORD_PATTERN.search(query):
        return {**base_init, "route": "legal"}

    if _gemini_is_configured():
        try:
            llm = get_llm()
            resp = await llm.ainvoke([
                SystemMessage(
                    content=(
                        "Anda adalah QUESTION CLASSIFIER. Klasifikasikan pesan pengguna "
                        "menjadi SATU kata saja:\n"
                        "- 'greeting' untuk sapaan / basa-basi / obrolan umum.\n"
                        "- 'legal' untuk pertanyaan dokumen, definisi, hukum, pasal, atau UU PDP."
                    )
                ),
                HumanMessage(content=query),
            ])
            decision = _extract_ai_text(resp).lower()
            if "greeting" in decision and "legal" not in decision:
                return {**base_init, "route": "greeting"}
        except Exception as exc:
            logger.warning("Classifier Gemini gagal (%s), default ke jalur 'legal'.", exc)

    return {**base_init, "route": "legal"}


async def general_assistant_node(state: WorkflowState) -> dict[str, Any]:
    """Cabang 1 (LLM 4 -> ANS3): Respons cepat untuk sapaan atau obrolan umum."""
    history_msgs = list(state.get("messages") or [])
    reply = (
        "Halo! Saya asisten hukum **UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP)**.\n\n"
        "Silakan ajukan pertanyaan mengenai hak subjek data pribadi, kewajiban pengendali/prosesor, "
        "penanganan kebocoran data, transfer data internasional, atau sanksi pidana/administratif."
    )

    if _gemini_is_configured():
        try:
            llm = get_llm()
            resp = await llm.ainvoke([
                SystemMessage(
                    content=(
                        "Kamu adalah General Assistant untuk chatbot hukum UU No. 27 Tahun 2022 (UU PDP). "
                        "Balas sapaan atau obrolan ringan pengguna secara ramah, singkat, dan sopan, "
                        "serta arahkan mereka untuk berkonsultasi mengenai UU PDP."
                    )
                ),
                *history_msgs[-6:],
            ])
            candidate = _extract_ai_text(resp)
            if candidate:
                reply = candidate
        except Exception as exc:
            logger.warning("General Assistant Gemini gagal (%s), memakai respons default.", exc)

    return {
        "answer": reply,
        "citations": [],
        "messages": [AIMessage(content=reply)],
    }


async def knowledge_retrieval_node(state: WorkflowState) -> dict[str, Any]:
    """LOOP_BLOCK -> KR: Mengambil potongan pasal dari Dataset UU_No_27_Tahun_2022."""
    current_query = (state.get("current_query") or state.get("query") or "").strip()
    loop_count = int(state.get("loop_count", 0)) + 1

    sse_res = await _retrieve_via_mcp_sse(current_query)
    if sse_res is not None:
        context_text, citations = sse_res
        return {
            "loop_count": loop_count,
            "context": context_text,
            "citations": citations,
        }

    context_text, citations = _retrieve_via_local_store(current_query)
    return {
        "loop_count": loop_count,
        "context": context_text,
        "citations": citations,
    }


async def relevance_grader_node(state: WorkflowState) -> dict[str, Any]:
    """
    LOOP_BLOCK -> GRADER + IF_REL + VA_TRUE:
    Mengevaluasi relevansi hasil retrieval ('RELEVAN' vs 'TIDAK_RELEVAN')
    dan menetapkan variabel is_found = True bila relevan.
    """
    current_query = state.get("current_query") or state.get("query") or ""
    context = state.get("context") or ""

    if not context.strip() or "Tidak ditemukan pasal atau ketentuan terkait" in context:
        return {"grade": "TIDAK_RELEVAN", "is_found": False}

    if _gemini_is_configured():
        try:
            llm = get_llm()
            resp = await llm.ainvoke([
                SystemMessage(
                    content=(
                        "Anda adalah Relevance Grader untuk dokumen UU PDP (UU No. 27 Tahun 2022). "
                        "Evaluasi apakah potongan dokumen membantu menjawab pertanyaan pengguna.\n"
                        "Jawab HANYA dengan tepat satu kata: 'RELEVAN' atau 'TIDAK_RELEVAN'."
                    )
                ),
                HumanMessage(
                    content=f"Query: {current_query}\n\nPotongan Dokumen:\n{context[:2500]}"
                ),
            ])
            verdict = _extract_ai_text(resp).upper()
            if "TIDAK_RELEVAN" in verdict or "TIDAK RELEVAN" in verdict:
                return {"grade": "TIDAK_RELEVAN", "is_found": False}
            if "RELEVAN" in verdict:
                return {"grade": "RELEVAN", "is_found": True}
        except Exception as exc:
            logger.warning("Grader Gemini gagal (%s), menganggap hasil retrieval relevan.", exc)

    return {"grade": "RELEVAN", "is_found": True}


async def query_rewriter_node(state: WorkflowState) -> dict[str, Any]:
    """
    LOOP_BLOCK -> REWRITER (LLM 2) + VA_QUERY:
    Memperbaiki kata kunci pencarian dan mengassign current_query = hasil_rewrite.
    """
    current_query = state.get("current_query") or state.get("query") or ""
    rewritten = current_query

    if _gemini_is_configured():
        try:
            llm = get_llm()
            resp = await llm.ainvoke([
                SystemMessage(
                    content=(
                        "Anda adalah Query Rewriter hukum UU No. 27 Tahun 2022 (UU PDP). "
                        "Perbaiki query pencarian agar menggunakan istilah baku UU PDP "
                        "(misalnya: subjek data pribadi, pengendali data, prosesor data, "
                        "kegagalan pelindungan data, sanksi pidana, denda administratif). "
                        "Berikan HANYA query hasil perbaikan tanpa komentar tambahan."
                    )
                ),
                HumanMessage(content=current_query),
            ])
            candidate = _extract_ai_text(resp)
            if candidate:
                rewritten = candidate
        except Exception as exc:
            logger.warning("Rewriter Gemini gagal (%s), memperluas query secara lokal.", exc)

    if rewritten == current_query:
        rewritten = f"{current_query} UU PDP Pelindungan Data Pribadi Pasal"

    return {"current_query": rewritten}


async def legal_generator_node(state: WorkflowState) -> dict[str, Any]:
    """IF_FOUND == True -> LLM 3 (Generator Jawaban Hukum + Sitasi) -> ANS."""
    context = state.get("context") or ""
    history_msgs = list(state.get("messages") or [])

    system_prompt = (
        "Kamu adalah Konsultan Hukum Ahli untuk Undang-Undang Republik Indonesia "
        "Nomor 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP).\n\n"
        "PANDUAN MENJAWAB:\n"
        "1. Jawab langsung, padat, terstruktur, dan berlandaskan kutipan resmi di bawah ini.\n"
        "2. Sebutkan rujukan Pasal dan Ayat secara eksplisit (misal: Pasal 15 ayat (1) UU PDP).\n"
        "3. Bedakan Pengendali Data Pribadi, Prosesor Data Pribadi, dan Subjek Data Pribadi.\n"
        "4. Bila ada informasi yang tidak tercantum di konteks, sampaikan apa adanya.\n\n"
        f"KONTEKS RESMI UU NO. 27 TAHUN 2022:\n{context}"
    )

    answer_text = ""
    if _gemini_is_configured():
        try:
            llm = get_llm()
            resp = await llm.ainvoke([
                SystemMessage(content=system_prompt),
                *history_msgs[-6:],
            ])
            answer_text = _extract_ai_text(resp)
        except Exception as exc:
            logger.error("Legal Generator Gemini gagal: %s", exc)

    if not answer_text:
        answer_text = (
            "Berikut kutipan pasal relevan dari naskah resmi **UU No. 27 Tahun 2022 (UU PDP)** "
            "(*Catatan: Gemini API belum aktif/terkonfigurasi di backend/.env*):\n\n"
            f"{context}"
        )

    return {
        "answer": answer_text,
        "messages": [AIMessage(content=answer_text)],
    }


async def fallback_not_found_node(state: WorkflowState) -> dict[str, Any]:
    """IF_FOUND == False -> ANS2 (Fallback: Pasal Tidak Ditemukan)."""
    query = state.get("query") or ""
    fallback_text = (
        f"Maaf, setelah dilakukan penelusuran ulang hingga {MAX_LOOP_COUNT} kali putaran pada "
        "basis data naskah resmi **UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP)**, "
        f"pasal atau ketentuan yang relevan untuk pertanyaan \"{query}\" tidak ditemukan.\n\n"
        "Silakan perjelas kata kunci atau sebutkan nomor pasal/topik spesifik UU PDP yang ingin Anda tanyakan."
    )
    return {
        "answer": fallback_text,
        "citations": [],
        "messages": [AIMessage(content=fallback_text)],
    }


# ---------------------------------------------------------
# Fungsi Transisi Kondisi Graph
# ---------------------------------------------------------
def _route_after_classifier(state: WorkflowState) -> str:
    if state.get("route") == "greeting":
        return "general_assistant"
    return "knowledge_retrieval"


def _route_after_grader(state: WorkflowState) -> str:
    if state.get("is_found"):
        return "legal_generator"
    if int(state.get("loop_count", 0)) < MAX_LOOP_COUNT:
        return "query_rewriter"
    return "fallback_not_found"


def _build_workflow():
    """Membangun StateGraph persis mengikuti alur Dify Chatflow pada tmp/workflow.mmd."""
    builder = StateGraph(WorkflowState)

    builder.add_node("question_classifier", question_classifier_node)
    builder.add_node("general_assistant", general_assistant_node)
    builder.add_node("knowledge_retrieval", knowledge_retrieval_node)
    builder.add_node("relevance_grader", relevance_grader_node)
    builder.add_node("query_rewriter", query_rewriter_node)
    builder.add_node("legal_generator", legal_generator_node)
    builder.add_node("fallback_not_found", fallback_not_found_node)

    builder.add_edge(START, "question_classifier")
    builder.add_conditional_edges(
        "question_classifier",
        _route_after_classifier,
        {
            "general_assistant": "general_assistant",
            "knowledge_retrieval": "knowledge_retrieval",
        },
    )
    builder.add_edge("general_assistant", END)

    # LOOP_BLOCK: KR -> GRADER -> IF_REL (True: BREAK -> IF_FOUND | False: REWRITER -> KR)
    builder.add_edge("knowledge_retrieval", "relevance_grader")
    builder.add_conditional_edges(
        "relevance_grader",
        _route_after_grader,
        {
            "legal_generator": "legal_generator",
            "query_rewriter": "query_rewriter",
            "fallback_not_found": "fallback_not_found",
        },
    )
    builder.add_edge("query_rewriter", "knowledge_retrieval")

    builder.add_edge("legal_generator", END)
    builder.add_edge("fallback_not_found", END)

    return builder.compile(checkpointer=_SHARED_CHECKPOINTER)


_COMPILED_GRAPH = _build_workflow()


class LangGraphProvider(BaseOrchestrator):
    """Strategy provider lokal berbasis LangGraph Agentic RAG + Google Gemini + MCP."""

    def __init__(self):
        self._graph = _COMPILED_GRAPH

    async def ainvoke(
        self,
        query: str,
        user_id: str,
        conversation_id: str | None = None,
    ) -> OrchestratorResponse:
        settings.reload()
        clean_conv_id = (conversation_id or "").strip() or f"lg_{uuid.uuid4().hex[:12]}"

        initial_state: WorkflowState = {
            "messages": [HumanMessage(content=query)],
            "query": query,
            "current_query": query,
            "is_found": False,
            "loop_count": 0,
            "route": "",
            "context": "",
            "citations": [],
            "grade": "",
            "answer": "",
        }

        final_state = await self._graph.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": clean_conv_id}},
        )

        return OrchestratorResponse(
            answer=str(final_state.get("answer") or "Tidak ada respon yang dihasilkan."),
            conversation_id=clean_conv_id,
            citations=list(final_state.get("citations") or []),
            provider_used="langgraph",
        )
