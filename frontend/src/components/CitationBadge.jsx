import { BookOpen } from 'lucide-react';

export default function CitationBadge({ citations }) {
  if (!citations || citations.length === 0) return null;

  return (
    <div className="mt-3 pt-3 border-t border-slate-700/60 flex flex-wrap items-center gap-2">
      <span className="text-xs font-semibold text-slate-400 flex items-center gap-1">
        <BookOpen size={13} className="text-emerald-400" /> Sumber Rujukan:
      </span>
      {citations.map((cite, idx) => (
        <span
          key={idx}
          className="text-xs bg-slate-800 text-emerald-300 border border-emerald-500/30 px-2 py-0.5 rounded-md font-mono"
        >
          {cite}
        </span>
      ))}
    </div>
  );
}