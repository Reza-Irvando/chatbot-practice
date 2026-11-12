"""
CLI Interaktif Chatbot Asisten Hukum UU PDP (UU No. 27 Tahun 2022).
Jalankan dari folder backend/:
    python main.py
"""
import asyncio

from dify_client import query_dify_workflow
from config.settings import settings


def bootstrap():
    print("=" * 70)
    print("  CHATBOT UU PERLINDUNGAN DATA PRIBADI (UU NO. 27 TAHUN 2022)")
    print(f"  Engine: Dify Chatflow  |  URL: {settings.DIFY_API_URL}")
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
            print("\n[Meneruskan ke Dify Chatflow...]")
            result = await query_dify_workflow(
                query=user_input,
                user_id="cli_user",
                conversation_id=conversation_id,
            )
            conversation_id = result.get("conversation_id", conversation_id)
            print(f"\nJawaban:\n{result.get('answer', '')}\n")
            citations = result.get("citations", [])
            if citations:
                print("Referensi:")
                for cite in citations:
                    print(f"  - {cite}")
                print()
            print("-" * 70)
        except Exception as exc:
            print(f"\n[ERROR]: {exc}\n")


if __name__ == "__main__":
    bootstrap()
    asyncio.run(run_chat())
