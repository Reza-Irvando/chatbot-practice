import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { User, Bot } from 'lucide-react';
import CitationBadge from './CitationBadge';

export default function MessageItem({ message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex gap-3.5 my-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center flex-shrink-0 text-white shadow-md shadow-emerald-900/30">
          <Bot size={18} />
        </div>
      )}

      <div
        className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm ${
          isUser
            ? 'bg-blue-600 text-white rounded-br-xs'
            : 'bg-slate-800 border border-slate-700/80 text-slate-100 rounded-bl-xs'
        }`}
      >
        <div className="prose prose-invert prose-sm max-w-none prose-p:my-1 prose-headings:text-slate-100 prose-strong:text-emerald-400 prose-table:my-2 prose-th:border-slate-600 prose-td:border-slate-700">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        </div>

        {!isUser && message.citations && (
          <CitationBadge citations={message.citations} />
        )}
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-full bg-blue-700 flex items-center justify-center flex-shrink-0 text-white shadow-md shadow-blue-900/30">
          <User size={18} />
        </div>
      )}
    </div>
  );
}