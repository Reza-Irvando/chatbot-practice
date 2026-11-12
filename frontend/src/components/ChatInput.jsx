import { useState, useRef, useEffect } from 'react';
import { Send, Loader2 } from 'lucide-react';

export default function ChatInput({
  onSendMessage,
  onSend,
  isLoading = false,
  disabled = false,
}) {
  const [input, setInput] = useState('');
  const textareaRef = useRef(null);

  const sendHandler = onSendMessage || onSend;
  const isInputDisabled = Boolean(isLoading || disabled);

  // Auto-focus ke textarea saat komponen dimuat atau setelah loading selesai
  useEffect(() => {
    if (!isInputDisabled) {
      textareaRef.current?.focus();
    }
  }, [isInputDisabled]);

  // Auto-resize tinggi textarea sesuai panjang teks
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  }, [input]);

  const handleSubmit = (e) => {
    if (e) {
      e.preventDefault();
    }
    const trimmed = input.trim();
    if (!trimmed || isInputDisabled) return;

    if (typeof sendHandler === 'function') {
      sendHandler(trimmed);
      setInput('');
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="relative flex items-end">
      <textarea
        ref={textareaRef}
        rows={1}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Tanyakan ketentuan UU PDP (misal: hak subjek, Pasal 15, kebocoran data, sanksi pidana)..."
        disabled={isInputDisabled}
        className="w-full bg-slate-800/90 border border-slate-700 rounded-xl px-4 py-3 pr-12 text-sm text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/70 resize-none transition max-h-36 overflow-y-auto disabled:opacity-50 disabled:cursor-not-allowed"
      />
      <button
        type="submit"
        disabled={isInputDisabled || !input.trim()}
        title={isLoading ? 'Sedang memproses...' : 'Kirim pertanyaan'}
        className="absolute right-2.5 bottom-2.5 p-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:hover:bg-emerald-600 rounded-lg text-white transition flex items-center justify-center cursor-pointer disabled:cursor-not-allowed shadow-md"
      >
        {isLoading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
      </button>
    </form>
  );
}