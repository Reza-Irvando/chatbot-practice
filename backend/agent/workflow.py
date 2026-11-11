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


def get_llm():
    """
    Menginisialisasi LLM sesuai konfigurasi provider di .env (Gemini atau Ollama).
    Dapat beralih secara dinamis tanpa perlu restart manual.
    """
    settings.reload()
    provider = (settings.LLM_PROVIDER or "ollama").lower().strip()

    # 1. Opsi Provider: Google Gemini API
    if provider == "gemini":
        if not settings.GEMINI_API_KEY:
            print("[WARNING] LLM_PROVIDER disetel ke 'gemini', namun GEMINI_API_KEY di .env kosong.")
            print("[INFO] Beralih otomatis menggunakan model lokal Ollama sebagai fallback...")
        else:
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                return ChatGoogleGenerativeAI(
                    model=settings.GEMINI_MODEL,
                    google_api_key=settings.GEMINI_API_KEY,
                    max_output_tokens=settings.MAX_TOKENS,
                )
            except Exception as e:
                print(f"[ERROR] Gagal inisialisasi Gemini API: {e}. Menggunakan fallback Ollama...")

    # 2. Opsi Provider: Ollama (Lokal Llama 3.2)
    return ChatOllama(
        model=settings.LLM_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0.1,
        num_predict=settings.MAX_TOKENS,
        stop=["<|eot_id|>", "<|end_of_text|>", "\n\nPERTANYAAN PENGGUNA:", "\n\nUSER:"],
    )


SYSTEM_PROMPT = """Kamu adalah Konsultan Hukum Ahli untuk Undang-Undang Republik Indonesia Nomor 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP).

TUGAS UTAMA:
Gunakan kutipan resmi naskah UU PDP di bawah ini untuk menjawab pertanyaan pengguna secara ringkas, akurat, padat, dan berlandaskan hukum.

PANDUAN MENJAWAB:
1. Jawab langsung ke inti pertanyaan secara terstruktur dan hindari kalimat bertele-tele atau pengulangan kata.
2. Cantumkan rujukan pasal dan ayat secara jelas dan eksplisit (misalnya: "Berdasarkan Pasal 15 ayat (1) UU PDP...", "Sebagaimana diatur dalam Pasal 4 ayat (2)...").
3. Jika ada informasi dari Bagian Penjelasan Resmi, sertakan secara ringkas.
4. Bedakan antara Pengendali Data Pribadi, Prosesor Data Pribadi, dan Subjek Data Pribadi.
5. Jika informasi TIDAK diatur dalam UU No. 27 Tahun 2022 atau tidak ditemukan dalam konteks dokumen, nyatakan secara jujur bahwa hal tersebut tidak tercantum dalam naskah UU PDP. Jangan mengarang aturan fiktif.

---
KONTEKS RESMI DARI MCP SERVER (UU NO. 27 TAHUN 2022):
{context}
---"""

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{question}"),
])


def ekstrak_sitasi(context_text: str) -> list[str]:
    """Mengekstrak judul dokumen / label pasal dari konteks untuk ditampilkan pada UI."""
    raw_citations = re.findall(r"\[(UU PDP No\. 27/2022 - .*?)\]", context_text)
    if not raw_citations:
        raw_citations = [
            c for c in re.findall(r"\[(.*?)\]", context_text)
            if not c.startswith("Dokumen:") and not c.startswith("Bagian:") and not c.startswith("Skor")
        ]
    return list(dict.fromkeys(raw_citations))


async def mcp_rag_chain(question: str) -> dict:
    """Pipeline RAG dengan perantara FastMCP Server resmi, mengembalikan answer dan citations."""
    # 1. Panggil MCP Server untuk mengambil pasal-pasal relevan
    context_text = await panggil_tool_mcp(
        nama_tool="cari_pasal_dan_ketentuan_uupdp",
        argumen={"pertanyaan": question},
    )

    # 2. Ambil instans LLM aktif (Gemini atau Ollama)
    active_llm = get_llm()

    # 3. Sintesis jawaban hukum via LLM
    chain = prompt | active_llm | StrOutputParser()
    answer = await chain.ainvoke(
        {"context": context_text, "question": question}
    )

    # 4. Ekstrak metadata sitasi untuk UI
    citations = ekstrak_sitasi(context_text)

    return {
        "answer": answer,
        "citations": citations,
        "raw_context": context_text,
    }


__all__ = ["mcp_rag_chain", "ekstrak_sitasi", "get_llm"]
