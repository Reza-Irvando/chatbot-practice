import sys
from pathlib import Path

# 1. Pastikan Root Direktori terdaftar di urutan pertama sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# 2. Impor dependensi FastMCP dan vector store
from mcp.server.fastmcp import FastMCP
from mcp_server.vector_store import search_documents

mcp = FastMCP("UU-PDP-Knowledge-Server")


@mcp.tool()
def cari_pasal_dan_ketentuan_uupdp(pertanyaan: str) -> str:
    """Mencari pasal, ayat, penjelasan resmi, hak subjek data, kewajiban pengendali/prosesor,
    transfer data pribadi, serta sanksi administratif dan pidana dalam
    Undang-Undang Republik Indonesia Nomor 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP).
    """
    try:
        results = search_documents(pertanyaan)
        if not results:
            return "Tidak ditemukan pasal atau ketentuan terkait dalam UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi."

        formatted = []
        for r in results:
            label_bagian = f"{r.get('bab', '')} - {r.get('pasal', '')}".strip(" -")
            if not label_bagian:
                label_bagian = r.get("judul", "UU No. 27/2022")
            kategori = r.get("kategori", "Batang Tubuh")

            formatted.append(
                f"[UU PDP No. 27/2022 - {label_bagian} ({kategori})] (Skor Relevansi: {r['score']:.2f}):\n"
                f"{r['konten']}"
            )
        return "\n\n---\n\n".join(formatted)
    except Exception as err:
        return f"Gagal mengambil dokumen UU PDP dari vector store: {str(err)}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
