"""
CLI Interaktif Chatbot Asisten Hukum UU PDP (UU No. 27 Tahun 2022).
Mendukung orkestrator dinamis (Dify & LangGraph) sesuai ORCHESTRATOR_PROVIDER.
Jalankan dari folder backend/:
    python main.py
"""
import asyncio
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config.settings import settings
from orchestrators.factory import get_orchestrator


def bootstrap():
    settings.reload()
    print("=" * 70)
    print("  CHATBOT UU PERLINDUNGAN DATA PRIBADI (UU NO. 27 TAHUN 2022)")
    print(f"  Active Orchestrator: {settings.ORCHESTRATOR_PROVIDER.upper()}")
    print("=" * 70)
    print(
        "Contoh pertanyaan:\n"
        "  1. Apa saja hak-hak subjek data pribadi menurut UU PDP?\n"
        "  2. Apa perbedaan data pribadi yang bersifat spesifik dan umum?\n"
        "  3. Berapa batas waktu notifikasi jika terjadi kegagalan pelindungan data?\n"
        "  4. Apa sanksi pidana dan denda bagi pelaku jual beli data pribadi secara ilegal?\n"
    )
    print("Ketik '/reset' untuk memulai sesi baru, 'exit' untuk keluar.\n")


async def run_chat():
    conversation_id = ""
    while True:
        try:
            user_input = input("Pertanyaan Anda: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nSelesai.")
            break

        if user_input.lower() in ("exit", "keluar", "/exit"):
            print("Selesai.")
            break

        if user_input.lower() == "/reset":
            conversation_id = ""
            print("[Sesi percakapan direset.]\n")
            continue

        if not user_input:
            continue

        try:
            orchestrator = get_orchestrator()
            print(f"\n[Memproses via {settings.ORCHESTRATOR_PROVIDER}...]")
            result = await orchestrator.ainvoke(
                query=user_input,
                user_id="cli_user",
                conversation_id=conversation_id,
            )
            conversation_id = result.conversation_id or conversation_id
            print(f"\nJawaban [{result.provider_used}]:\n{result.answer}\n")
            if result.citations:
                print("Referensi:")
                for cite in result.citations:
                    label = cite.get("label") or cite.get("document_name") or str(cite)
                    print(f"  - {label}")
                print()
            print("-" * 70)
        except Exception as exc:
            print(f"\n[ERROR]: {exc}\n")


if __name__ == "__main__":
    bootstrap()
    asyncio.run(run_chat())
