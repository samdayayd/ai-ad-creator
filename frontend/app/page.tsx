"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, createAds, getAdHistory } from "@/lib/api";
import { AdSet } from "@/lib/types";
import { useAuth } from "@/lib/auth";
import { useLanguage } from "@/lib/LanguageProvider";
import AdResults from "@/components/AdResults";
import HistoryList from "@/components/HistoryList";
import VideoAdCreator from "@/components/VideoAdCreator";
import UGCAdCreator from "@/components/UGCAdCreator";
import HudRings from "@/components/HudRings";

type Tab = "text" | "video" | "ugc";

export default function HomePage() {
  const { token, loading: authLoading } = useAuth();
  const { t } = useLanguage();
  const router = useRouter();
  const [tab, setTab] = useState<Tab>("text");
  const [url, setUrl] = useState("");
  const [adSet, setAdSet] = useState<AdSet | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const [history, setHistory] = useState<Awaited<ReturnType<typeof getAdHistory>>>([]);

  useEffect(() => {
    if (authLoading) return;
    if (!token) router.push("/login");
  }, [token, authLoading, router]);

  useEffect(() => {
    if (!token) return;
    getAdHistory(token)
      .then(setHistory)
      .catch(() => setHistory([]));
  }, [token]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setAdSet(null);
    setGenerating(true);
    try {
      const result = await createAds(token, url);
      setAdSet(result);
      getAdHistory(token)
        .then(setHistory)
        .catch(() => {});
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Something went wrong.");
    } finally {
      setGenerating(false);
    }
  };

  const handleSelectHistory = (id: number) => {
    const entry = history.find((h) => h.id === id);
    if (entry) setAdSet(entry.result);
  };

  if (authLoading || !token) {
    return <p className="text-slate-400">Loading…</p>;
  }

  return (
    <div className="relative space-y-6">
      <div className="pointer-events-none absolute -right-32 -top-32 h-72 w-72 opacity-40 sm:opacity-60">
        <HudRings />
      </div>
      <div className="relative">
        <h1 className="font-display text-2xl font-bold tracking-wide text-white">
          Ad<span className="glow-text">Storm</span> Studio
        </h1>
        <div className="mt-3 flex gap-2">
          <button onClick={() => setTab("text")} className={tab === "text" ? "chip-active" : "chip"}>
            {t("home.tabText")}
          </button>
          <button onClick={() => setTab("video")} className={tab === "video" ? "chip-active" : "chip"}>
            {t("home.tabVideo")}
          </button>
          <button onClick={() => setTab("ugc")} className={tab === "ugc" ? "chip-active" : "chip"}>
            {t("home.tabUgc")}
          </button>
        </div>
      </div>

      {tab === "text" && (
        <div className="space-y-6">
          <div className="panel p-6">
            <p className="text-sm text-slate-400">{t("home.intro")}</p>

            <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
              <input
                type="url"
                required
                placeholder={t("home.urlPlaceholder")}
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="input-field flex-1"
              />
              <button type="submit" disabled={generating} className="btn-primary shrink-0">
                {generating ? t("home.creating") : t("home.create")}
              </button>
            </form>

            {error && <p className="mt-3 text-sm text-rose-400">{error}</p>}
          </div>

          {adSet && <AdResults adSet={adSet} />}

          <div className="panel p-4">
            <p className="label-tech">{t("home.pastAdSets")}</p>
            <HistoryList
              items={history.map((h) => ({
                id: h.id,
                title: h.product_title || h.product_url,
                subtitle: h.product_url,
                created_at: h.created_at,
              }))}
              onSelect={handleSelectHistory}
              emptyText={t("home.noAdSets")}
            />
          </div>
        </div>
      )}

      {tab === "video" && <VideoAdCreator />}

      {tab === "ugc" && <UGCAdCreator />}
    </div>
  );
}
