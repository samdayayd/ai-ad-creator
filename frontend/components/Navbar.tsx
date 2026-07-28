"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getMe } from "@/lib/api";
import { Me } from "@/lib/types";
import { useAuth } from "@/lib/auth";
import { useLanguage } from "@/lib/LanguageProvider";
import { LOCALES, Locale } from "@/lib/i18n";

export default function Navbar() {
  const { token, logout, loading } = useAuth();
  const { locale, setLocale, t } = useLanguage();
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
    <header className="sticky top-0 z-10 border-b border-white/10 bg-ink-950/80 backdrop-blur-xl">
      <div className="mx-auto flex max-w-4xl items-center justify-between gap-3 px-4 py-4">
        <Link href="/" className="font-display text-lg font-bold tracking-wide text-white">
          Ad<span className="glow-text">Storm</span> <span className="text-sm font-normal text-slate-400">Studio</span>
        </Link>
        <div className="flex items-center gap-4">
          <Link href="/pricing" className="hidden text-sm text-slate-400 transition hover:text-volt-300 sm:inline">
            {t("nav.pricing")}
          </Link>
          <Link href="/contact" className="hidden text-sm text-slate-400 transition hover:text-volt-300 sm:inline">
            {t("nav.contact")}
          </Link>
          {!loading && token && me && (
            <span className="hidden text-sm text-slate-400 md:inline">
              <span className="capitalize text-volt-300">{me.plan}</span> {t("nav.plan")} ·{" "}
              {me.videos_remaining === null ? t("nav.unlimited") : `${me.videos_remaining} ${t("nav.videosLeft")}`}
            </span>
          )}
          <select
            value={locale}
            onChange={(e) => setLocale(e.target.value as Locale)}
            aria-label="Language"
            className="rounded-md border border-white/10 bg-ink-900 px-2 py-1 text-xs text-slate-300 outline-none focus:border-volt-400"
          >
            {LOCALES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
          {!loading && token && (
            <button onClick={logout} className="text-sm text-slate-400 transition hover:text-white">
              {t("nav.logout")}
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
