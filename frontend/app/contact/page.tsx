"use client";

import { FormEvent, useState } from "react";
import { ApiError, sendContactMessage } from "@/lib/api";
import { useLanguage } from "@/lib/LanguageProvider";

export default function ContactPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const { t } = useLanguage();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSending(true);
    try {
      await sendContactMessage(name, email, message);
      setSent(true);
      setName("");
      setEmail("");
      setMessage("");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Something went wrong.");
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="mx-auto mt-4 max-w-lg">
      <h1 className="font-display text-2xl font-bold tracking-wide text-white">{t("contact.title")}</h1>
      <p className="mt-2 text-sm text-slate-400">{t("contact.subtitle")}</p>

      <div className="panel mt-6 p-6">
        {sent ? (
          <div className="text-center">
            <p className="text-lg font-semibold text-volt-300">{t("contact.sentTitle")}</p>
            <p className="mt-1 text-sm text-slate-400">{t("contact.sentSubtitle")}</p>
            <button onClick={() => setSent(false)} className="btn-secondary mt-4">
              {t("contact.sendAnother")}
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="label-tech">{t("contact.name")}</label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="input-field"
              />
            </div>
            <div>
              <label className="label-tech">{t("contact.email")}</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t("contact.emailPlaceholder")}
                className="input-field"
              />
            </div>
            <div>
              <label className="label-tech">{t("contact.message")}</label>
              <textarea
                required
                rows={5}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                maxLength={5000}
                className="input-field"
              />
            </div>

            {error && <p className="text-sm text-rose-400">{error}</p>}

            <button type="submit" disabled={sending} className="btn-primary w-full">
              {sending ? t("contact.submitting") : t("contact.submit")}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
