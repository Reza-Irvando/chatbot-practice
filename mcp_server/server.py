import argparse
import sys
from pathlib import Path

MCP_DIR = Path(__file__).resolve().parent
ROOT_DIR = MCP_DIR.parent
for p in (str(MCP_DIR), str(ROOT_DIR)):
    if p not in sys.path:
        sys.path.insert(0, p)

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

try:
    from mcp_server.config import settings
    from mcp_server.vector_store import format_search_results, search_documents
except ModuleNotFoundError:
    from config import settings  # type: ignore[import-not-found]
    from vector_store import format_search_results, search_documents  # type: ignore[import-not-found]

mcp = FastMCP(
    "UU-PDP-Knowledge-Server",
    host=settings.MCP_HOST,
    port=settings.MCP_PORT,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=False,
    ),
)


@mcp.tool()
def cari_pasal_dan_ketentuan_uupdp(pertanyaan: str) -> str:
    """
    Mencari pasal, ayat, penjelasan resmi, hak subjek data, kewajiban pengendali/prosesor,
    transfer data pribadi, serta sanksi administratif dan pidana dalam
    Undang-Undang Republik Indonesia Nomor 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP).
    """
    try:
        results = search_documents(pertanyaan)
        return format_search_results(results)
    except Exception as err:
        return f"Gagal mengambil dokumen UU PDP dari vector store: {str(err)}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FastMCP Server untuk Knowledge UU PDP")
    parser.add_argument(
        "--transport",
        default=settings.MCP_TRANSPORT or "stdio",
        choices=["stdio", "sse", "streamable-http"],
        help="Protokol transport MCP (default: stdio)",
    )
    args = parser.parse_args()
    mcp.run(transport=args.transport)
