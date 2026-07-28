"use client";

export interface HistoryItem {
  id: number;
  title: string;
  subtitle: string;
  created_at: string;
}

export default function HistoryList({
  items,
  onSelect,
  emptyText,
}: {
  items: HistoryItem[];
  onSelect: (id: number) => void;
  emptyText: string;
}) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">{emptyText}</p>;
  }

  return (
    <div className="space-y-2">
      {items.map((item) => (
        <button
          key={item.id}
          onClick={() => onSelect(item.id)}
          className="w-full rounded-md border border-ink-700 px-3 py-2 text-left text-sm text-slate-300 hover:border-spark-500 hover:text-white"
        >
          <div className="flex items-center justify-between gap-2">
            <span className="truncate font-semibold">{item.title}</span>
            <span className="shrink-0 text-xs text-slate-500">{new Date(item.created_at).toLocaleString()}</span>
          </div>
          {item.subtitle && <p className="mt-0.5 truncate text-xs text-slate-500">{item.subtitle}</p>}
        </button>
      ))}
    </div>
  );
}
