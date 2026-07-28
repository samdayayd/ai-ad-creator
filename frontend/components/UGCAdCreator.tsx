"use client";

import { ChangeEvent, FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import {
  ApiError,
  createUgcAd,
  createUgcScript,
  fetchVideoBlobUrl,
  getPresenters,
  getUgcHistory,
  getVoices,
} from "@/lib/api";
import { CTA_OPTIONS, Presenter, UGCAd, UGCGeneration, UGCScript, Voice } from "@/lib/types";
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
  const [script, setScript] = useState<UGCScript | null>(null);
  const [writingScript, setWritingScript] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [quotaExceeded, setQuotaExceeded] = useState(false);
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

  // A script written for a different brief/product would be stale — clear
  // it so the user writes a fresh one instead of rendering something that
  // no longer matches what they typed.
  const invalidateScript = () => setScript(null);

  const showVideo = async (result: UGCAd) => {
    setUgcAd(result);
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
    if (!prompt.trim() || !productName.trim()) {
      setError("Fill in the brief and product name first.");
      return;
    }
    setWritingScript(true);
    try {
      const result = await createUgcScript(token, prompt, productName, productDescription);
      setScript(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Something went wrong.");
    } finally {
      setWritingScript(false);
    }
  };

  const updateScript = (field: keyof UGCScript, value: string, benefitIndex?: number) => {
    setScript((prev) => {
      if (!prev) return prev;
      if (field === "benefits" && benefitIndex !== undefined) {
        const benefits = prev.benefits.map((b, i) => (i === benefitIndex ? value : b));
        return { ...prev, benefits };
      }
      return { ...prev, [field]: value };
    });
  };

  const handleRender = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setQuotaExceeded(false);
    if (!presenterId || !voiceId) {
      setError("Choose a presenter and voice first.");
      return;
    }
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
        cta,
        script ?? undefined
      );
      await showVideo(result);
      getUgcHistory(token)
        .then(setHistory)
        .catch(() => {});
    } catch (err) {
      if (err instanceof ApiError && err.status === 402) setQuotaExceeded(true);
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
      <div className="panel p-6">
        <h2 className="font-display text-lg font-bold tracking-wide text-white">UGC Ad</h2>
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
      <div className="panel p-6">
        <h2 className="font-display text-lg font-bold tracking-wide text-white">Make a UGC ad</h2>
        <p className="mt-1 text-sm text-slate-400">
          One sentence + your product → an editable AI-written script → a talking AI presenter reads it, cut
          together with your product photos and a call-to-action card. See the presenter as a talking-avatar shot
          edited alongside your product, not literally holding it — no API generates that yet.
        </p>

        <form onSubmit={script ? handleRender : handleWriteScript} className="mt-4 space-y-3">
          <div>
            <label className="label-tech">One-line brief</label>
            <input
              type="text"
              required
              value={prompt}
              onChange={(e) => {
                setPrompt(e.target.value);
                invalidateScript();
              }}
              placeholder="Create a friendly ad for my wireless earbuds aimed at students."
              className="input-field"
            />
          </div>

          <div>
            <label className="label-tech">Product photos (optional cutaways)</label>
            <input
              type="file"
              accept="image/jpeg,image/png,image/webp"
              multiple
              onChange={handleImages}
              className="input-field file:mr-3 file:rounded file:border-0 file:bg-gradient-to-r file:from-spark-500 file:to-volt-500 file:px-3 file:py-1 file:text-white"
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
              placeholder="Wireless Earbuds"
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
              placeholder="30-hour battery, crystal-clear calls."
              className="input-field"
            />
          </div>

          <div>
            <label className="label-tech">Presenter</label>
            <div className="flex flex-wrap gap-2">
              {presenters.map((p) => (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => setPresenterId(p.id)}
                  className={presenterId === p.id ? "chip-active" : "chip"}
                >
                  {p.name}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="label-tech">Voice</label>
            <select value={voiceId} onChange={(e) => setVoiceId(e.target.value)} className="input-field">
              {voices.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label-tech">Call to action</label>
            <div className="flex flex-wrap gap-2">
              {CTA_OPTIONS.map((c) => (
                <button key={c} type="button" onClick={() => setCta(c)} className={cta === c ? "chip-active" : "chip"}>
                  {c}
                </button>
              ))}
            </div>
          </div>

          {script && (
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
              <div>
                <label className="mb-1 block text-xs text-slate-500">Hook</label>
                <textarea
                  value={script.hook}
                  onChange={(e) => updateScript("hook", e.target.value)}
                  rows={1}
                  className="input-field"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs text-slate-500">Intro</label>
                <textarea
                  value={script.intro}
                  onChange={(e) => updateScript("intro", e.target.value)}
                  rows={2}
                  className="input-field"
                />
              </div>
              {script.benefits.map((b, i) => (
                <div key={i}>
                  <label className="mb-1 block text-xs text-slate-500">Benefit {i + 1}</label>
                  <textarea
                    value={b}
                    onChange={(e) => updateScript("benefits", e.target.value, i)}
                    rows={1}
                    className="input-field"
                  />
                </div>
              ))}
              <div>
                <label className="mb-1 block text-xs text-slate-500">Closing line</label>
                <textarea
                  value={script.cta_line}
                  onChange={(e) => updateScript("cta_line", e.target.value)}
                  rows={1}
                  className="input-field"
                />
              </div>
            </div>
          )}

          <button
            type="submit"
            disabled={writingScript || generating || !presenterId || !voiceId}
            className="btn-primary w-full"
          >
            {script
              ? generating
                ? "Generating… this can take a minute"
                : "Make UGC ad"
              : writingScript
              ? "Writing script…"
              : "Write script"}
          </button>
        </form>

        {error && (
          <div className="mt-3 text-sm text-rose-400">
            <p>{error}</p>
            {quotaExceeded && (
              <Link href="/pricing" className="mt-1 inline-block text-volt-300 underline">
                See plans →
              </Link>
            )}
          </div>
        )}
      </div>

      {ugcAd && videoBlobUrl && (
        <div className="panel p-4">
          <div className="flex flex-col items-center gap-3">
            <video src={videoBlobUrl} controls className="max-h-[70vh] rounded-lg" />
            <div className="flex items-center gap-3 text-sm text-slate-400">
              <span>
                {ugcAd.presenter_name} · {ugcAd.voice_name} · {ugcAd.cta_text}
              </span>
              <a href={videoBlobUrl} download={`${ugcAd.product_title || "ugc-ad"}.mp4`} className="btn-secondary">
                Download
              </a>
            </div>
          </div>

          <div className="mt-4 space-y-1 text-sm text-slate-300">
            <p className="label-tech">Script</p>
            <p>{ugcAd.script.hook}</p>
            <p>{ugcAd.script.intro}</p>
            {ugcAd.script.benefits.map((b, i) => (
              <p key={i}>{b}</p>
            ))}
            <p>{ugcAd.script.cta_line}</p>
          </div>
        </div>
      )}

      <div className="panel p-4">
        <p className="label-tech">Past UGC ads</p>
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
