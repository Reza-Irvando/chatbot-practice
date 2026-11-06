import sys
from pathlib import Path

# 1. Pastikan Root Direktori terdaftar di urutan pertama sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# 2. Impor dependensi MCP dan local store
from mcp.server.fastmcp import FastMCP
from mcp_server.vector_store import search_documents

mcp = FastMCP("Skripsi-SVM-Knowledge-Server")


@mcp.tool()
def cari_teori_dan_metodologi_skripsi(pertanyaan: str) -> str:
    """Mencari kutipan naskah, metodologi, dan parameter SVM skripsi."""
    try:
        results = search_documents(pertanyaan)
        if not results:
            return "Tidak ditemukan kutipan terkait di naskah skripsi."

        formatted = []
        for r in results:
            formatted.append(
                f"[{r['judul']}] (Skor Relevansi: {r['score']:.2f}):\n{r['konten']}"
            )
        return "\n\n---\n\n".join(formatted)
    except Exception as err:
        return f"Gagal mengambil dokumen dari vector store: {str(err)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
