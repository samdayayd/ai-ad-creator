"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ApiError, signup as signupRequest } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useLanguage } from "@/lib/LanguageProvider";

const MIN_PASSWORD_LENGTH = 8;

export default function SignupPage() {
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
    if (password.length < MIN_PASSWORD_LENGTH) {
      setError(`Password must be at least ${MIN_PASSWORD_LENGTH} characters.`);
      return;
    }
    setSubmitting(true);
    try {
      const result = await signupRequest(email, password);
      login(result.access_token);
      router.push("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Something went wrong.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="panel mx-auto mt-10 max-w-sm p-6">
      <h1 className="font-display text-xl font-bold tracking-wide text-white">{t("signup.title")}</h1>
      <p className="mt-1 text-sm text-slate-400">{t("signup.subtitle")}</p>

      <form onSubmit={handleSubmit} className="mt-5 space-y-3">
        <div>
          <label className="label-tech">{t("signup.email")}</label>
          <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)} className="input-field" />
        </div>
        <div>
          <label className="label-tech">{t("signup.password")}</label>
          <input
            type="password"
            required
            minLength={MIN_PASSWORD_LENGTH}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input-field"
          />
          <p className="mt-1 text-xs text-slate-500">{t("signup.passwordHint")}</p>
        </div>

        {error && <p className="text-sm text-rose-400">{error}</p>}

        <button type="submit" disabled={submitting} className="btn-primary w-full">
          {submitting ? t("signup.submitting") : t("signup.submit")}
        </button>
      </form>

      <p className="mt-4 text-sm text-slate-400">
        {t("signup.haveAccount")}{" "}
        <Link href="/login" className="text-volt-300 hover:underline">
          {t("signup.login")}
        </Link>
        .
      </p>
    </div>
  );
}
