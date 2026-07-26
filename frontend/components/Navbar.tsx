"use client";

import { useAuth } from "@/lib/auth";

export default function Navbar() {
  const { token, logout, loading } = useAuth();

  return (
    <header className="border-b border-ink-700 bg-ink-900/80 backdrop-blur">
      <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-4">
        <span className="text-lg font-extrabold tracking-tight text-white">
          AI Ad Creator <span className="text-spark-400">⭐⭐⭐⭐⭐</span>
        </span>
        {!loading && token && (
          <button onClick={logout} className="text-sm text-slate-400 hover:text-white">
            Log out
          </button>
        )}
      </div>
    </header>
  );
}
