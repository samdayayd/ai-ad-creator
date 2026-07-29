"use client";

import Link from "next/link";
import { useLanguage } from "@/lib/LanguageProvider";

export default function Footer() {
  const { t } = useLanguage();
  return (
    <footer className="border-t border-white/10 bg-ink-950/60 backdrop-blur">
      <div className="mx-auto flex max-w-4xl flex-col items-center gap-2 px-4 py-6 text-xs text-slate-500 sm:flex-row sm:justify-between">
        <span className="font-display tracking-wide">
          Ze<span className="glow-text">Truth</span> Studio
        </span>
        <div className="flex gap-4">
          <Link href="/pricing" className="hover:text-volt-300">
            {t("nav.pricing")}
          </Link>
          <Link href="/contact" className="hover:text-volt-300">
            {t("nav.contact")}
          </Link>
        </div>
      </div>
    </footer>
  );
}
