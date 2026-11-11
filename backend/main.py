import asyncio
import sys
from pathlib import Path

# Pastikan Root Direktori terdaftar di sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.agent.workflow import mcp_rag_chain
from mcp_server.migrations.runner import run_migrations


def bootstrap():
    print("=" * 70)
    print(" CHATBOT UU PERLINDUNGAN DATA PRIBADI (UU NO. 27 TAHUN 2022)")
    print(" Menggunakan Protokol MCP (Model Context Protocol), Ollama & pgvector")
    print("=" * 70)
    try:
        run_migrations()
    except Exception as e:
        print(f"[PERINGATAN] Migrasi database dilewati / error: {e}")
    print("\nMCP Client siap terhubung ke UU PDP FastMCP Server!")
    print(
        "Contoh pertanyaan:\n"
        " 1. 'Apa saja hak-hak subjek data pribadi menurut UU PDP?'\n"
        " 2. 'Apa perbedaan data pribadi yang bersifat spesifik dan umum?'\n"
        " 3. 'Berapa batas waktu notifikasi jika terjadi kegagalan pelindungan data?'\n"
        " 4. 'Apa sanksi pidana dan denda bagi pelaku jual beli data pribadi secara ilegal?'\n"
    )


async def run_chat():
    while True:
        try:
            user_input = input("\nPertanyaan Anda: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSelesai.")
            break

        if user_input.lower() in ["exit", "keluar"]:
            print("Selesai.")
            break
        if not user_input:
            continue

        try:
            print("\n[Menghubungi MCP Server & mengambil ketentuan UU PDP...]")
            result = await mcp_rag_chain(user_input)

            answer = result.get("answer", "")
            citations = result.get("citations", [])

            print(f"\nAsisten UU PDP (via MCP):\n{answer}\n")
            if citations:
                print("Referensi Dokumen & Pasal:")
                for cite in citations:
                    print(f" - [{cite}]")
                print()
            print("-" * 70)
        except Exception as e:
            print(f"[ERROR]: {e}")


if __name__ == "__main__":
    bootstrap()
    asyncio.run(run_chat())
