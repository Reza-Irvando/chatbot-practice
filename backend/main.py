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
    print(" CHATBOT SKRIPSI SVM: MENGGUNAKAN PROTOKOL MCP (MODEL CONTEXT PROTOCOL)")
    print("=" * 70)
    run_migrations()
    print("\nMCP Client siap terhubung ke FastMCP Server!")
    print(
        "Contoh pertanyaan: 'Berapa akurasi SVM yang diperoleh?' atau 'Jelaskan sensor UAV yang dipakai'\n"
    )


async def run_chat():
    while True:
        user_input = input("\nPertanyaan Anda: ").strip()
        if user_input.lower() in ["exit", "keluar"]:
            print("Selesai.")
            break
        if not user_input:
            continue

        try:
            print("\n[Menghubungi MCP Server & mengambil data skripsi...]")
            result = await mcp_rag_chain(user_input)

            answer = result.get("answer", "")
            citations = result.get("citations", [])

            print(f"\nAsisten Skripsi (via MCP):\n{answer}\n")
            if citations:
                print("Referensi Dokumen:")
                for cite in citations:
                    print(f" - [{cite}]")
                print()
            print("-" * 70)
        except Exception as e:
            print(f"[ERROR]: {e}")


if __name__ == "__main__":
    bootstrap()
    asyncio.run(run_chat())
