"use client";

import { useState } from "react";

export default function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleClick = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <button
      onClick={handleClick}
      className="rounded-md border border-ink-700 px-2 py-1 text-xs text-slate-300 hover:border-spark-500 hover:text-spark-400"
    >
      {copied ? "Copied!" : "Copy"}
    </button>
  );
}
