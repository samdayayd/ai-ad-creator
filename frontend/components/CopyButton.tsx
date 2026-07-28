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
      className="rounded-md border border-white/10 px-2 py-1 text-xs text-slate-300 transition hover:border-volt-400/60 hover:text-volt-300"
    >
      {copied ? "Copied!" : "Copy"}
    </button>
  );
}
