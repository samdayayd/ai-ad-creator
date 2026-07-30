"use client";

import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import {
  ApiError,
  createCreditCheckout,
  createVideoAd,
  createVideoScript,
  fetchVideoBlobUrl,
  getVideoHistory,
} from "@/lib/api";
import { VIDEO_DURATIONS, VideoAd, VideoGeneration } from "@/lib/types";
import { useAuth } from "@/lib/auth";
import { useLanguage } from "@/lib/LanguageProvider";
import HistoryList from "./HistoryList";

export default function VideoAdCreator() {
  const { token } = useAuth();
  const { t } = useLanguage();
  const [buyingCredit, setBuyingCredit] = useState(false);
  const [images, setImages] = useState<File[]>([]);
  const [productName, setProductName] = useState("");
  const [productDescription, setProductDescription] = useState("");
  const [duration, setDuration] = useState<number>(30);
  const [scriptLines, setScriptLines] = useState<string[] | null>(null);
  const [writingScript, setWritingScript] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [quotaExceeded, setQuotaExceeded] = useState(false);
  const [videoAd, setVideoAd] = useState<VideoAd | null>(null);
  const [videoBlobUrl, setVideoBlobUrl] = useState<string | null>(null);
  const [history, setHistory] = useState<VideoGeneration[]>([]);

  useEffect(() => {
    if (!token) return;
    getVideoHistory(token)
      .then(setHistory)
      .catch(() => setHistory([]));
  }, [token]);

  const handleImages = (e: ChangeEvent<HTMLInputElement>) => {
    setImages(e.target.files ? Array.from(e.target.files) : []);
  };

  // Changing the brief after a script was already written would leave a
  // script written for a different product/length — clear it so the user
  // writes a fresh one instead of rendering something stale.
  const invalidateScript = () => setScriptLines(null);

  const showVideo = async (result: VideoAd) => {
    setVideoAd(result);
    const blobUrl = await fetchVideoBlobUrl(token, result.video_url);
    setVideoBlobUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return blobUrl;
    });
  };

  const handleWriteScript = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setQuotaExceeded(false);
    if (!productName.trim()) {
      setError("Enter a product name first.");
      return;
    }
    setWritingScript(true);
    try {
      const result = await createVideoScript(token, productName, productDescription, duration);
      setScriptLines(result.scenes);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Something went wrong.");
    } finally {
      setWritingScript(false);
    }
  };

  const handleSceneChange = (index: number, value: string) => {
    setScriptLines((prev) => (prev ? prev.map((line, i) => (i === index ? value : line)) : prev));
  };

  const handleRender = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setQuotaExceeded(false);
    if (images.length === 0) {
      setError("Upload at least one product photo first.");
      return;
    }
    setVideoAd(null);
    if (videoBlobUrl) URL.revokeObjectURL(videoBlobUrl);
    setVideoBlobUrl(null);
    setGenerating(true);
    try {
      const result = await createVideoAd(
        token,
        images,
        productName,
        productDescription,
        duration,
        scriptLines ?? undefined
      );
      await showVideo(result);
      getVideoHistory(token)
        .then(setHistory)
        .catch(() => {});
    } catch (err) {
      if (err instanceof ApiError && err.status === 402) setQuotaExceeded(true);
      setError(err instanceof ApiError ? err.detail : "Something went wrong.");
    } finally {
      setGenerating(false);
    }
  };

  const handleBuyStandardCredit = async () => {
    setBuyingCredit(true);
    try {
      const { checkout_url } = await createCreditCheckout(token, "standard_1");
      window.location.href = checkout_url;
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Couldn't start checkout.");
      setBuyingCredit(false);
    }
  };

  const handleSelectHistory = async (id: number) => {
    const entry = history.find((h) => h.id === id);
    if (!entry) return;
    setError(null);
    try {
      await showVideo(entry);
    } catch {
      setError("Couldn't load that video — it may no longer be available.");
    }
  };

  return (
    <div className="space-y-4">
      <div className="panel p-6">
        <h2 className="font-display text-lg font-bold tracking-wide text-white">Make a video ad</h2>
        <p className="mt-1 text-sm text-slate-400">
          Upload product photos, pick a length, write a script, then render — AI-written script (editable before you
          commit to rendering), voiceover, Ken Burns pans across your images, captions, and background sound.
        </p>

        <form onSubmit={scriptLines ? handleRender : handleWriteScript} className="mt-4 space-y-3">
          <div>
            <label className="label-tech">Product photos</label>
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple
              onChange={handleImages}
              className="input-field file:mr-3 file:rounded file:border-0 file:bg-volt-400 file:px-3 file:py-1 file:font-semibold file:text-ink-950"
            />
            {images.length > 0 && <p className="mt-1 text-xs text-slate-500">{images.length} image(s) selected</p>}
          </div>

          <div>
            <label className="label-tech">Product name</label>
            <input
              type="text"
              required
              value={productName}
              onChange={(e) => {
                setProductName(e.target.value);
                invalidateScript();
              }}
              placeholder="Wireless Noise-Cancelling Headphones"
              className="input-field"
            />
          </div>

          <div>
            <label className="label-tech">Description (optional)</label>
            <textarea
              value={productDescription}
              onChange={(e) => {
                setProductDescription(e.target.value);
                invalidateScript();
              }}
              rows={2}
              placeholder="Immersive sound, 30-hour battery life."
              className="input-field"
            />
          </div>

          <div>
            <label className="label-tech">Length</label>
            <div className="flex gap-2">
              {VIDEO_DURATIONS.map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => {
                    setDuration(d);
                    invalidateScript();
                  }}
                  className={duration === d ? "chip-active" : "chip"}
                >
                  {d}s
                </button>
              ))}
            </div>
          </div>

          {scriptLines && (
            <div className="space-y-2 rounded-lg border border-white/10 bg-ink-950/60 p-3">
              <div className="flex items-center justify-between">
                <p className="label-tech mb-0">Script — edit before rendering</p>
                <button
                  type="button"
                  onClick={handleWriteScript}
                  disabled={writingScript}
                  className="text-xs text-volt-300 hover:underline disabled:opacity-60"
                >
                  {writingScript ? "Rewriting…" : "Regenerate"}
                </button>
              </div>
              {scriptLines.map((line, i) => (
                <textarea
                  key={i}
                  value={line}
                  onChange={(e) => handleSceneChange(i, e.target.value)}
                  rows={2}
                  className="input-field"
                />
              ))}
            </div>
          )}

          <button type="submit" disabled={writingScript || generating} className="btn-primary w-full">
            {scriptLines
              ? generating
                ? "Rendering video… this can take a minute"
                : "Make video ad"
              : writingScript
              ? "Writing script…"
              : "Write script"}
          </button>
        </form>

        {error && (
          <div className="mt-3 text-sm text-rose-400">
            <p>{error}</p>
            {quotaExceeded && (
              <div className="mt-3 rounded-lg border border-white/10 bg-ink-950/60 p-3">
                <p className="font-display text-sm font-bold text-white">{t("credits.outOfVideos")}</p>
                <p className="mt-1 text-xs text-slate-400">{t("credits.outOfVideosBody")}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <button onClick={handleBuyStandardCredit} disabled={buyingCredit} className="btn-primary">
                    {buyingCredit ? t("credits.buying") : t("credits.buyStandardShort")}
                  </button>
                  <Link href="/pricing" className="btn-secondary">
                    See plans →
                  </Link>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {videoAd && videoBlobUrl && (
        <div className="panel p-4">
          <div className="flex flex-col items-center gap-3">
            <video src={videoBlobUrl} controls className="max-h-[70vh] rounded-lg" />
            <div className="flex items-center gap-3 text-sm text-slate-400">
              <span>
                {videoAd.actual_duration_seconds}s (asked for {videoAd.requested_duration_seconds}s)
              </span>
              <a href={videoBlobUrl} download={`${videoAd.product_title || "video-ad"}.mp4`} className="btn-secondary">
                Download
              </a>
            </div>
          </div>

          <div className="mt-4 space-y-1 text-sm text-slate-300">
            <p className="label-tech">Script</p>
            {videoAd.scenes.map((scene, i) => (
              <p key={i}>
                <span className="text-slate-500">{scene.duration}s —</span> {scene.text}
              </p>
            ))}
          </div>
        </div>
      )}

      <div className="panel p-4">
        <p className="label-tech">Past videos</p>
        <HistoryList
          items={history.map((h) => ({
            id: h.id,
            title: h.product_title || "Video ad",
            subtitle: `${h.actual_duration_seconds}s`,
            created_at: h.created_at,
          }))}
          onSelect={handleSelectHistory}
          emptyText="No videos generated yet."
        />
      </div>
    </div>
  );
}
