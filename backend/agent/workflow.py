import re
import sys
from pathlib import Path
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama

# Pastikan Root Direktori terdaftar di sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.agent.client import panggil_tool_mcp
from config.settings import settings

llm = ChatOllama(
    model=settings.LLM_MODEL,
    base_url=settings.OLLAMA_BASE_URL,
    temperature=0.1,
)

PROMPT_TEMPLATE = """Kamu adalah Asisten Akademik Ahli untuk skripsi:
"IMPLEMENTASI KLASIFIKASI TINGKAT KERAPATAN VEGETASI PADA CITRA MULTISPEKTRAL UAV MENGGUNAKAN ALGORITMA SUPPORT VECTOR MACHINE (SVM)".

Gunakan informasi dari kutipan dokumen skripsi berikut untuk menjawab pertanyaan pengguna.
Jika informasi tidak ada dalam kutipan yang diberikan, nyatakan secara jujur bahwa data tersebut tidak ditemukan dalam naskah.

---
KONTEKS DARI MCP SERVER:
{context}
---

PERTANYAAN PENGGUNA:
{question}

JAWABAN AKADEMIS:"""

prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)


def ekstrak_sitasi(context_text: str) -> list[str]:
    """Mengekstrak judul dokumen / label halaman dari konteks untuk UI."""
    return re.findall(r"\[(.*?)\]", context_text)


async def mcp_rag_chain(question: str) -> dict:
    """Pipeline RAG dengan perantara MCP Server resmi, mengembalikan answer dan citations."""
    # 1. Panggil MCP Server
    context_text = await panggil_tool_mcp(
        nama_tool="cari_teori_dan_metodologi_skripsi",
        argumen={"pertanyaan": question},
    )

    # 2. Sintesis jawaban via LLM
    chain = prompt | llm | StrOutputParser()
    answer = await chain.ainvoke(
        {"context": context_text, "question": question}
    )

    # 3. Ekstrak metadata sitasi
    citations = list(dict.fromkeys(ekstrak_sitasi(context_text)))

    return {
        "answer": answer,
        "citations": citations,
        "raw_context": context_text,
    }


__all__ = ["mcp_rag_chain", "ekstrak_sitasi"]
