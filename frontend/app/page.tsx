"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, createAds, getAdHistory } from "@/lib/api";
import { AdSet } from "@/lib/types";
import { useAuth } from "@/lib/auth";
import AdResults from "@/components/AdResults";
import HistoryList from "@/components/HistoryList";
import VideoAdCreator from "@/components/VideoAdCreator";
import UGCAdCreator from "@/components/UGCAdCreator";

type Tab = "text" | "video" | "ugc";

export default function HomePage() {
  const { token, loading: authLoading } = useAuth();
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
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-white">
          AI Ad Creator <span className="text-spark-400">⭐⭐⭐⭐⭐</span>
        </h1>
        <div className="mt-3 flex gap-2">
          <button
            onClick={() => setTab("text")}
            className={`rounded-md px-4 py-2 text-sm font-semibold ${
              tab === "text" ? "bg-spark-500 text-white" : "border border-ink-700 text-slate-300"
            }`}
          >
            Text Ads
          </button>
          <button
            onClick={() => setTab("video")}
            className={`rounded-md px-4 py-2 text-sm font-semibold ${
              tab === "video" ? "bg-spark-500 text-white" : "border border-ink-700 text-slate-300"
            }`}
          >
            Video Ad
          </button>
          <button
            onClick={() => setTab("ugc")}
            className={`rounded-md px-4 py-2 text-sm font-semibold ${
              tab === "ugc" ? "bg-spark-500 text-white" : "border border-ink-700 text-slate-300"
            }`}
          >
            UGC Ad
          </button>
        </div>
      </div>

      {tab === "text" && (
        <div className="space-y-6">
          <div className="rounded-xl border border-ink-700 bg-gradient-to-br from-ink-900 to-ink-800 p-6">
            <p className="text-sm text-slate-400">
              One click. Paste a product URL — get TikTok ads, Facebook ads, Google Ads, an Instagram caption,
              headlines, a product description and an email campaign, all at once.
            </p>

            <form onSubmit={handleSubmit} className="mt-4 flex gap-2">
              <input
                type="url"
                required
                placeholder="https://your-store.com/products/example"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                className="flex-1 rounded-md border border-ink-700 bg-ink-900 px-3 py-2 text-sm text-white outline-none focus:border-spark-500"
              />
              <button
                type="submit"
                disabled={generating}
                className="rounded-md bg-spark-500 px-5 py-2 text-sm font-bold text-white hover:bg-spark-400 disabled:opacity-60"
              >
                {generating ? "Creating…" : "Create ads"}
              </button>
            </form>

            {error && <p className="mt-3 text-sm text-rose-400">{error}</p>}
          </div>

          {adSet && <AdResults adSet={adSet} />}

          <div className="rounded-xl border border-ink-700 bg-ink-900 p-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Past ad sets</p>
            <HistoryList
              items={history.map((h) => ({
                id: h.id,
                title: h.product_title || h.product_url,
                subtitle: h.product_url,
                created_at: h.created_at,
              }))}
              onSelect={handleSelectHistory}
              emptyText="No ad sets generated yet."
            />
          </div>
        </div>
      )}

      {tab === "video" && <VideoAdCreator />}

      {tab === "ugc" && <UGCAdCreator />}
    </div>
  );
}
