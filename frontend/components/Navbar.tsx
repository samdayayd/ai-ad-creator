"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getMe } from "@/lib/api";
import { Me } from "@/lib/types";
import { useAuth } from "@/lib/auth";

export default function Navbar() {
  const { token, logout, loading } = useAuth();
  const [me, setMe] = useState<Me | null>(null);

  useEffect(() => {
    if (!token) {
      setMe(null);
      return;
    }
    getMe(token)
      .then(setMe)
      .catch(() => setMe(null));
  }, [token]);

  return (
    <header className="border-b border-ink-700 bg-ink-900/80 backdrop-blur">
      <div className="mx-auto flex max-w-4xl items-center justify-between px-4 py-4">
        <span className="text-lg font-extrabold tracking-tight text-white">
          AI Ad Creator <span className="text-spark-400">⭐⭐⭐⭐⭐</span>
        </span>
        <div className="flex items-center gap-4">
          <Link href="/pricing" className="text-sm text-slate-400 hover:text-white">
            Pricing
          </Link>
          {!loading && token && me && (
            <span className="hidden text-sm text-slate-400 sm:inline">
              <span className="capitalize">{me.plan}</span> plan ·{" "}
              {me.videos_remaining === null ? "unlimited videos" : `${me.videos_remaining} videos left`}
            </span>
          )}
          {!loading && token && (
            <button onClick={logout} className="text-sm text-slate-400 hover:text-white">
              Log out
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
