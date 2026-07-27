"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ApiError, createAds } from "@/lib/api";
import { AdSet } from "@/lib/types";
import { useAuth } from "@/lib/auth";
import AdResults from "@/components/AdResults";
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

  useEffect(() => {
    if (authLoading) return;
    if (!token) router.push("/login");
  }, [token, authLoading, router]);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setAdSet(null);
    setGenerating(true);
    try {
      const result = await createAds(token, url);
      setAdSet(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Something went wrong.");
    } finally {
      setGenerating(false);
    }
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
        </div>
      )}

      {tab === "video" && <VideoAdCreator />}

      {tab === "ugc" && <UGCAdCreator />}
    </div>
  );
}
