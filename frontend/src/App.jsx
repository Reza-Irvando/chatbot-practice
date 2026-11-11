import { useState, useRef, useEffect } from 'react';
import { Sparkles, Terminal, Scale } from 'lucide-react';
import MessageItem from './components/MessageItem';
import ChatInput from './components/ChatInput';
import { sendChatMessageAsync, checkBackendHealth } from './services/api';

const QUICK_PROMPTS = [
  "Apa saja hak-hak subjek data pribadi menurut UU PDP?",
  "Apa perbedaan data pribadi yang bersifat spesifik dan umum?",
  "Berapa batas waktu pemberitahuan jika terjadi kegagalan pelindungan data pribadi?",
  "Apa saja sanksi pidana dan denda bagi pelaku jual beli data pribadi?",
];

export default function App() {
  const [messages, setMessages] = useState([
    {
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
    },
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [isBackendOnline, setIsBackendOnline] = useState(false);
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

  const handleSend = async (question) => {
    const trimmedQuestion = question?.trim() || '';
    if (!trimmedQuestion || isLoading) return;

    // 1. Tambah pesan user ke state
    const userMsg = { role: 'user', content: trimmedQuestion, citations: [] };
    setMessages((prev) => [...(prev || []), userMsg]);
    setIsLoading(true);

    try {
      // 2. Request ke backend (Async Polling / Direct)
      const data = await sendChatMessageAsync(trimmedQuestion);
      
      // Proteksi parsing payload respon backend
      const answerText = data?.answer || data?.result || data?.response || 'Tidak ada balasan dari server.';
      const citationsList = Array.isArray(data?.citations) ? data.citations : [];

      const botMsg = {
        role: 'assistant',
        content: answerText,
        citations: citationsList,
      };

      setMessages((prev) => [...(prev || []), botMsg]);
    } catch (err) {
      // Proteksi error object agar tidak melempar 'cannot read properties of undefined'
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
            Model Context Protocol (FastMCP) • Ollama • pgvector • UU No. 27 Tahun 2022
          </p>
        </div>

        {/* Dynamic Status Badge */}
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
          {isBackendOnline ? 'Backend & MCP Ready' : 'Backend Disconnected'}
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
            <span>Sedang menganalisis ketentuan UU PDP No. 27/2022 via FastMCP...</span>
          </div>
        )}
        <div ref={chatBottomRef} />
      </main>

      {/* Quick Suggestions & Input */}
      <footer className="pt-2">
        {messages?.length <= 2 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {QUICK_PROMPTS.map((promptText, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => handleSend(promptText)}
                className="text-xs bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 border border-slate-700/70 px-3 py-1.5 rounded-lg transition cursor-pointer"
              >
                {promptText}
              </button>
            ))}
          </div>
        )}
        <ChatInput onSendMessage={handleSend} isLoading={isLoading} />
      </footer>
    </div>
  );
}
