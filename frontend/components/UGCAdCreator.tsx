"use client";

import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import { ApiError, createUgcAd, fetchVideoBlobUrl, getPresenters, getUgcHistory, getVoices } from "@/lib/api";
import { CTA_OPTIONS, Presenter, UGCAd, UGCGeneration, Voice } from "@/lib/types";
import { useAuth } from "@/lib/auth";
import HistoryList from "./HistoryList";

export default function UGCAdCreator() {
  const { token } = useAuth();
  const [presenters, setPresenters] = useState<Presenter[]>([]);
  const [voices, setVoices] = useState<Voice[]>([]);
  const [setupError, setSetupError] = useState<string | null>(null);
  const [loadingSetup, setLoadingSetup] = useState(true);

  const [images, setImages] = useState<File[]>([]);
  const [prompt, setPrompt] = useState("");
  const [productName, setProductName] = useState("");
  const [productDescription, setProductDescription] = useState("");
  const [presenterId, setPresenterId] = useState("");
  const [voiceId, setVoiceId] = useState("");
  const [cta, setCta] = useState<string>(CTA_OPTIONS[0]);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ugcAd, setUgcAd] = useState<UGCAd | null>(null);
  const [videoBlobUrl, setVideoBlobUrl] = useState<string | null>(null);
  const [history, setHistory] = useState<UGCGeneration[]>([]);

  useEffect(() => {
    if (!token) return;
    Promise.all([getPresenters(token), getVoices(token)])
      .then(([p, v]) => {
        setPresenters(p);
        setVoices(v);
        if (p.length > 0) setPresenterId(p[0].id);
        if (v.length > 0) setVoiceId(v[0].id);
      })
      .catch((err) => {
        setSetupError(
          err instanceof ApiError
            ? err.detail
            : "Couldn't load presenters/voices — the D-ID and ElevenLabs API keys may not be set up yet."
        );
      })
      .finally(() => setLoadingSetup(false));
    getUgcHistory(token)
      .then(setHistory)
      .catch(() => setHistory([]));
  }, [token]);

  const handleImages = (e: ChangeEvent<HTMLInputElement>) => {
    setImages(e.target.files ? Array.from(e.target.files) : []);
  };

  const showVideo = async (result: UGCAd) => {
    setUgcAd(result);
    const blobUrl = await fetchVideoBlobUrl(token, result.video_url);
    setVideoBlobUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return blobUrl;
    });
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setUgcAd(null);
    if (videoBlobUrl) URL.revokeObjectURL(videoBlobUrl);
    setVideoBlobUrl(null);
    setGenerating(true);
    try {
      const presenter = presenters.find((p) => p.id === presenterId);
      const voice = voices.find((v) => v.id === voiceId);
      const result = await createUgcAd(
        token,
        images,
        prompt,
        productName,
        productDescription,
        presenterId,
        presenter?.name || "Presenter",
        voiceId,
        voice?.name || "Voice",
        cta
      );
      await showVideo(result);
      getUgcHistory(token)
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

  if (loadingSetup) {
    return <p className="text-sm text-slate-400">Loading presenters and voices…</p>;
  }

  if (setupError) {
    return (
      <div className="rounded-xl border border-ink-700 bg-gradient-to-br from-ink-900 to-ink-800 p-6">
        <h2 className="text-lg font-bold text-white">UGC Ad</h2>
        <p className="mt-3 text-sm text-rose-400">{setupError}</p>
        <p className="mt-2 text-sm text-slate-400">
          This feature needs two separate paid API keys on the backend: <code>D_ID_API_KEY</code> (studio.d-id.com)
          for the talking presenter, and <code>ELEVENLABS_API_KEY</code> (elevenlabs.io) for the voice.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-ink-700 bg-gradient-to-br from-ink-900 to-ink-800 p-6">
        <h2 className="text-lg font-bold text-white">Make a UGC ad</h2>
        <p className="mt-1 text-sm text-slate-400">
          One sentence + your product → a talking AI presenter reads an AI-written script, cut together with your
          product photos and a call-to-action card. See the presenter as a talking-avatar shot edited alongside your
          product, not literally holding it — no API generates that yet.
        </p>

        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">One-line brief</label>
            <input
              type="text"
              required
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Create a friendly ad for my wireless earbuds aimed at students."
              className="w-full rounded-md border border-ink-700 bg-ink-900 px-3 py-2 text-sm text-white outline-none focus:border-spark-500"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">Product photos (optional cutaways)</label>
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple
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
              placeholder="Wireless Earbuds"
              className="w-full rounded-md border border-ink-700 bg-ink-900 px-3 py-2 text-sm text-white outline-none focus:border-spark-500"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">Description (optional)</label>
            <textarea
              value={productDescription}
              onChange={(e) => setProductDescription(e.target.value)}
              rows={2}
              placeholder="30-hour battery, crystal-clear calls."
              className="w-full rounded-md border border-ink-700 bg-ink-900 px-3 py-2 text-sm text-white outline-none focus:border-spark-500"
            />
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">Presenter</label>
            <div className="flex flex-wrap gap-2">
              {presenters.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setPresenterId(p.id)}
                  className={`rounded-md px-3 py-1.5 text-sm font-semibold ${
                    presenterId === p.id
                      ? "bg-spark-500 text-white"
                      : "border border-ink-700 text-slate-300 hover:border-spark-500"
                  }`}
                >
                  {p.name}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">Voice</label>
            <select
              value={voiceId}
              onChange={(e) => setVoiceId(e.target.value)}
              className="w-full rounded-md border border-ink-700 bg-ink-900 px-3 py-2 text-sm text-white outline-none focus:border-spark-500"
            >
              {voices.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-slate-400">Call to action</label>
            <div className="flex flex-wrap gap-2">
              {CTA_OPTIONS.map((c) => (
                <button
                  key={c}
                  type="button"
                  onClick={() => setCta(c)}
                  className={`rounded-md px-3 py-1.5 text-sm font-semibold ${
                    cta === c ? "bg-spark-500 text-white" : "border border-ink-700 text-slate-300 hover:border-spark-500"
                  }`}
                >
                  {c}
                </button>
              ))}
            </div>
          </div>

          <button
            type="submit"
            disabled={generating || !presenterId || !voiceId}
            className="w-full rounded-md bg-spark-500 px-4 py-2 text-sm font-bold text-white hover:bg-spark-400 disabled:opacity-60"
          >
            {generating ? "Generating… this can take a minute" : "Make UGC ad"}
          </button>
        </form>

        {error && <p className="mt-3 text-sm text-rose-400">{error}</p>}
      </div>

      {ugcAd && videoBlobUrl && (
        <div className="rounded-xl border border-ink-700 bg-ink-900 p-4">
          <div className="flex flex-col items-center gap-3">
            <video src={videoBlobUrl} controls className="max-h-[70vh] rounded-lg" />
            <div className="flex items-center gap-3 text-sm text-slate-400">
              <span>
                {ugcAd.presenter_name} · {ugcAd.voice_name} · {ugcAd.cta_text}
              </span>
              <a
                href={videoBlobUrl}
                download={`${ugcAd.product_title || "ugc-ad"}.mp4`}
                className="rounded-md border border-ink-700 px-3 py-1 text-spark-400 hover:border-spark-500"
              >
                Download
              </a>
            </div>
          </div>

          <div className="mt-4 space-y-1 text-sm text-slate-300">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Script</p>
            <p>{ugcAd.script.hook}</p>
            <p>{ugcAd.script.intro}</p>
            {ugcAd.script.benefits.map((b, i) => (
              <p key={i}>{b}</p>
            ))}
            <p>{ugcAd.script.cta_line}</p>
          </div>
        </div>
      )}

      <div className="rounded-xl border border-ink-700 bg-ink-900 p-4">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Past UGC ads</p>
        <HistoryList
          items={history.map((h) => ({
            id: h.id,
            title: h.product_title || "UGC ad",
            subtitle: `${h.presenter_name} · ${h.voice_name} · ${h.cta_text}`,
            created_at: h.created_at,
          }))}
          onSelect={handleSelectHistory}
          emptyText="No UGC ads generated yet."
        />
      </div>
    </div>
  );
}
