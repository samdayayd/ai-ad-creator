"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ApiError, login as loginRequest } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useLanguage } from "@/lib/LanguageProvider";
import HudRings from "@/components/HudRings";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const { login } = useAuth();
  const { t } = useLanguage();
  const router = useRouter();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const result = await loginRequest(email, password);
      login(result.access_token);
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="relative mx-auto flex min-h-[480px] max-w-2xl items-center justify-center">
      <HudRings />
      <div className="panel w-full max-w-sm p-6">
        <h1 className="font-display text-xl font-bold tracking-wide text-white">{t("login.title")}</h1>
        <p className="mt-1 text-sm text-slate-400">
          {t("login.noAccount")}{" "}
          <Link href="/signup" className="text-volt-300 hover:underline">
            {t("login.signUp")}
          </Link>
          .
        </p>

        <form onSubmit={handleSubmit} className="mt-5 space-y-3">
          <div>
            <label className="label-tech">{t("login.email")}</label>
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="input-field" />
          </div>
          <div>
            <label className="label-tech">{t("login.password")}</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input-field"
            />
          </div>

          {error && <p className="text-sm text-rose-400">{error}</p>}

          <button type="submit" disabled={submitting} className="btn-primary w-full">
            {submitting ? t("login.submitting") : t("login.submit")}
          </button>
        </form>
      </div>
    </div>
  );
}
