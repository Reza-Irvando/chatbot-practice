import { useState, useRef, useEffect } from 'react';
import { Sparkles, Terminal, Scale, RotateCcw } from 'lucide-react';
import MessageItem from './components/MessageItem';
import ChatInput from './components/ChatInput';
import { sendChatMessageAsync, checkBackendHealth } from './services/api';

const QUICK_PROMPTS = [
  "Apa saja hak-hak subjek data pribadi menurut UU PDP?",
  "Apa perbedaan data pribadi yang bersifat spesifik dan umum?",
  "Berapa batas waktu pemberitahuan jika terjadi kegagalan pelindungan data pribadi?",
  "Apa saja sanksi pidana dan denda bagi pelaku jual beli data pribadi?",
];

const INITIAL_MESSAGE = {
  role: 'assistant',
  content:
    'Halo! Saya asisten hukum cerdas untuk **Undang-Undang No. 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP)**.\n\n' +
    'Silakan tanyakan hal-hal terkait:\n' +
    '- **Hak-hak Subjek Data** (Pasal 5 - 15)\n' +
    '- **Kewajiban Pengendali & Prosesor Data** (Pasal 27 - 50)\n' +
    '- **Penanganan Kebocoran Data** (Pasal 46)\n' +
    '- **Sanksi Administratif & Denda Pidana** (Pasal 57, 65 - 73)\n\n' +
    'Apa yang ingin Anda konsultasikan hari ini?',
  citations: [],
};

export default function App() {
  const [messages, setMessages] = useState([INITIAL_MESSAGE]);
  const [conversationId, setConversationId] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isBackendOnline, setIsBackendOnline] = useState(true);
  const chatBottomRef = useRef(null);

  // Polling pengecekan health backend
  useEffect(() => {
    let isMounted = true;
    const verifyHealth = async () => {
      const isOnline = await checkBackendHealth();
      if (isMounted) {
        setIsBackendOnline(Boolean(isOnline));
      }
    };

    verifyHealth();
    const interval = setInterval(verifyHealth, 5000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  // Auto scroll saat ada pesan baru atau loading
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleResetChat = () => {
    setConversationId('');
    setMessages([
      {
        ...INITIAL_MESSAGE,
        content:
          'Sesi percakapan baru telah dimulai. Konteks percakapan sebelumnya telah di-reset.\n\n' +
          'Silakan ajukan pertanyaan terkait **UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi (UU PDP)**.',
      },
    ]);
  };

  const handleSend = async (question) => {
    const trimmedQuestion = question?.trim() || '';
    if (!trimmedQuestion || isLoading) return;

    // 1. Tambah pesan user ke state
    const userMsg = { role: 'user', content: trimmedQuestion, citations: [] };
    setMessages((prev) => [...(prev || []), userMsg]);
    setIsLoading(true);

    try {
      // 2. Request ke backend (meneruskan conversation_id untuk multi-turn Dify)
      const data = await sendChatMessageAsync(trimmedQuestion, conversationId);

      // Simpan conversation_id untuk turn berikutnya
      if (data?.conversation_id) {
        setConversationId(data.conversation_id);
      }

      // Proteksi parsing payload respon backend
      const answerText =
        data?.answer || data?.result || data?.response || 'Tidak ada balasan dari server.';
      const citationsList = Array.isArray(data?.citations) ? data.citations : [];

      const botMsg = {
        role: 'assistant',
        content: answerText,
        citations: citationsList,
      };

      setMessages((prev) => [...(prev || []), botMsg]);
    } catch (err) {
      const errorMsg =
        err?.response?.data?.detail ||
        err?.message ||
        'Terjadi kendala saat menghubungi server backend.';

      setMessages((prev) => [
        ...(prev || []),
        {
          role: 'assistant',
          content: `⚠️ **Error:** ${errorMsg}`,
          citations: [],
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto px-4 py-5">
      {/* Header */}
      <header className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-lg font-bold text-slate-100 flex items-center gap-2">
            <Scale size={20} className="text-emerald-400" />
            UU Perlindungan Data Pribadi Assistant
          </h1>
          <p className="text-xs text-slate-400 mt-0.5">
            Dify Chatflow • UU No. 27 Tahun 2022
          </p>
        </div>

        {/* Action Buttons & Status Badge */}
        <div className="flex items-center gap-2">
          {conversationId && (
            <button
              onClick={handleResetChat}
              title="Mulai sesi percakapan baru (reset konteks)"
              className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 border border-slate-700 transition-colors"
            >
              <RotateCcw size={12} className="text-emerald-400" />
              <span>Reset Sesi</span>
            </button>
          )}

          <div
            className={`flex items-center gap-2 px-3 py-1 rounded-full text-xs border transition-colors ${
              isBackendOnline
                ? 'bg-emerald-950/40 border-emerald-500/30 text-emerald-400'
                : 'bg-rose-950/40 border-rose-500/30 text-rose-400'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isBackendOnline ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'
              }`}
            />
            {isBackendOnline ? 'Backend & Dify Ready' : 'Backend Disconnected'}
          </div>
        </div>
      </header>

      {/* Chat Messages Viewport */}
      <main className="flex-1 overflow-y-auto py-4 pr-1">
        {(messages || []).map((msg, i) => (
          <MessageItem key={i} message={msg || { role: 'assistant', content: '', citations: [] }} />
        ))}
        {isLoading && (
          <div className="flex gap-3.5 my-4 items-center text-xs text-slate-400">
            <div className="w-8 h-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center">
              <Terminal size={14} className="text-emerald-400 animate-pulse" />
            </div>
            <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 px-4 py-2.5 rounded-2xl">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />
              <span>Memproses alur Dify Chatflow & mengambil rujukan pasal...</span>
            </div>
          </div>
        )}
        <div ref={chatBottomRef} />
      </main>

      {/* Quick Suggestions (hanya tampil jika pesan masih sedikit) */}
      {(messages || []).length <= 2 && !isLoading && (
        <div className="mb-3">
          <p className="text-[11px] font-medium text-slate-400 mb-2 flex items-center gap-1.5">
            <Sparkles size={13} className="text-emerald-400" />
            Rekomendasi topik pertanyaan:
          </p>
          <div className="flex flex-wrap gap-2">
            {QUICK_PROMPTS.map((promptText, idx) => (
              <button
                key={idx}
                onClick={() => handleSend(promptText)}
                className="text-xs bg-slate-800/60 hover:bg-slate-700/60 text-slate-300 border border-slate-700/60 hover:border-emerald-500/40 px-3 py-1.5 rounded-xl text-left transition-all duration-150"
              >
                {promptText}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Chat Input Dock */}
      <footer className="pt-2">
        <ChatInput onSend={handleSend} disabled={isLoading || !isBackendOnline} />
        <p className="text-[10px] text-center text-slate-400 mt-2">
          Jawaban dihasilkan oleh Dify Chatflow berdasarkan naskah resmi UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi.
        </p>
      </footer>
    </div>
  );
}
