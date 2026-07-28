"use client";

import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import { ApiError, createVideoAd, fetchVideoBlobUrl, getVideoHistory } from "@/lib/api";
import { VIDEO_DURATIONS, VideoAd, VideoGeneration } from "@/lib/types";
import { useAuth } from "@/lib/auth";
import HistoryList from "./HistoryList";

export default function VideoAdCreator() {
  const { token } = useAuth();
  const [images, setImages] = useState<File[]>([]);
  const [productName, setProductName] = useState("");
  const [productDescription, setProductDescription] = useState("");
  const [duration, setDuration] = useState<number>(30);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
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

  const showVideo = async (result: VideoAd) => {
    setVideoAd(result);
    const blobUrl = await fetchVideoBlobUrl(token, result.video_url);
    setVideoBlobUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return blobUrl;
    });
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setVideoAd(null);
    if (videoBlobUrl) URL.revokeObjectURL(videoBlobUrl);
    setVideoBlobUrl(null);
    setGenerating(true);
    try {
      const result = await createVideoAd(token, images, productName, productDescription, duration);
      await showVideo(result);
      getVideoHistory(token)
        .then(setHistory)
        .catch(() => {});
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Something went wrong.");
    } finally {
      setGenerating(false);
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
      <div className="rounded-xl border border-ink-700 bg-gradient-to-br from-ink-900 to-ink-800 p-6">
        <h2 className="text-lg font-bold text-white">Make a video ad</h2>
        <p className="mt-1 text-sm text-slate-400">
          Upload product photos, pick a length, and get a real MP4 — AI-written script, voiceover, Ken Burns
          pans across your images, captions, and background sound.
        </p>

        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">Product photos</label>
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple
              required
              onChange={handleImages}
              className="w-full rounded-md border border-ink-700 bg-ink-900 px-3 py-2 text-sm text-white outline-none file:mr-3 file:rounded file:border-0 file:bg-spark-500 file:px-3 file:py-1 file:text-white"
            />
            {images.length > 0 && <p className="mt-1 text-xs text-slate-500">{images.length} image(s) selected</p>}
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">Product name</label>
            <input
              type="text"
              required
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              placeholder="Wireless Noise-Cancelling Headphones"
              className="w-full rounded-md border border-ink-700 bg-ink-900 px-3 py-2 text-sm text-white outline-none focus:border-spark-500"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">Description (optional)</label>
            <textarea
              value={productDescription}
              onChange={(e) => setProductDescription(e.target.value)}
              rows={2}
              placeholder="Immersive sound, 30-hour battery life."
              className="w-full rounded-md border border-ink-700 bg-ink-900 px-3 py-2 text-sm text-white outline-none focus:border-spark-500"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">Length</label>
            <div className="flex gap-2">
              {VIDEO_DURATIONS.map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setDuration(d)}
                  className={`rounded-md px-3 py-1.5 text-sm font-semibold ${
                    duration === d
                      ? "bg-spark-500 text-white"
                      : "border border-ink-700 text-slate-300 hover:border-spark-500"
                  }`}
                >
                  {d}s
                </button>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={generating}
            className="w-full rounded-md bg-spark-500 px-4 py-2 text-sm font-bold text-white hover:bg-spark-400 disabled:opacity-60"
          >
            {generating ? "Rendering video… this can take a minute" : "Make video ad"}
          </button>
        </form>

        {error && <p className="mt-3 text-sm text-rose-400">{error}</p>}
      </div>

      {videoAd && videoBlobUrl && (
        <div className="rounded-xl border border-ink-700 bg-ink-900 p-4">
          <div className="flex flex-col items-center gap-3">
            <video src={videoBlobUrl} controls className="max-h-[70vh] rounded-lg" />
            <div className="flex items-center gap-3 text-sm text-slate-400">
              <span>
                {videoAd.actual_duration_seconds}s (asked for {videoAd.requested_duration_seconds}s)
              </span>
              <a
                href={videoBlobUrl}
                download={`${videoAd.product_title || "video-ad"}.mp4`}
                className="rounded-md border border-ink-700 px-3 py-1 text-spark-400 hover:border-spark-500"
              >
                Download
              </a>
            </div>
          </div>

          <div className="mt-4 space-y-1 text-sm text-slate-300">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Script</p>
            {videoAd.scenes.map((scene, i) => (
              <p key={i}>
                <span className="text-slate-500">{scene.duration}s —</span> {scene.text}
              </p>
            ))}
          </div>
        </div>
      )}

      <div className="rounded-xl border border-ink-700 bg-ink-900 p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Past videos</p>
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
