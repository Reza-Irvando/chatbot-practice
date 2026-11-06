import os
import sys
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Pastikan Root Direktori terdaftar di sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Lokasi absolut ke server.py
SERVER_PATH = ROOT_DIR / "mcp_server" / "server.py"

# Wariskan environment dan tambahkan PYTHONPATH agar subproses bisa melihat modul root proyek
custom_env = dict(os.environ)
custom_env["PYTHONPATH"] = (
    str(ROOT_DIR) + os.pathsep + custom_env.get("PYTHONPATH", "")
)

server_params = StdioServerParameters(
    command=sys.executable,
    args=["-u", str(SERVER_PATH)],
    env=custom_env,
)


def format_sub_exceptions(exc: BaseException) -> list[str]:
    """Rekursif membongkar isi ExceptionGroup sampai ke error terdalam."""
    errors = []
    if isinstance(exc, BaseExceptionGroup):
        for sub in exc.exceptions:
            errors.extend(format_sub_exceptions(sub))
    else:
        errors.append(f"{type(exc).__name__}: {str(exc)}")
    return errors


async def panggil_tool_mcp(nama_tool: str, argumen: dict) -> str:
    """Menghubungi FastMCP Server via stdio dan mengeksekusi tool."""
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(nama_tool, arguments=argumen)

                if result.content and len(result.content) > 0:
                    return result.content[0].text
                return "Tidak ada hasil yang dikembalikan oleh MCP Server."
    except BaseExceptionGroup as eg:
        rincian = format_sub_exceptions(eg)
        raise RuntimeError(f"Sub-Exception MCP Terdalam: {' | '.join(rincian)}")
    except Exception as e:
        raise RuntimeError(f"Error MCP Client: {type(e).__name__} - {str(e)}")


__all__ = ["panggil_tool_mcp", "format_sub_exceptions"]
