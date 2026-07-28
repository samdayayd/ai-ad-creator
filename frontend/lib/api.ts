import { TOKEN_KEY } from "./auth";
import {
  AdGeneration,
  AdSet,
  Me,
  Plan,
  Presenter,
  UGCAd,
  UGCGeneration,
  UGCScript,
  VideoAd,
  VideoGeneration,
  Voice,
} from "./types";

export class ApiError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
    this.detail = detail;
  }
}

// Next.js's built-in rewrite proxy (next.config.js) can't hold a connection
// open long enough for video generation (it drops with a socket hang up
// around 30s, well under the 40-70s the ffmpeg pipeline actually needs), so
// when a public backend URL is baked in at build time, the browser calls it
// directly and skips the proxy. Falls back to the relative /api path (and
// therefore the rewrite) when unset, which is what local Docker Compose dev
// relies on since the browser can't reach the "backend" container hostname
// directly.
const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "";

async function apiFetch<T>(path: string, token: string | null, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BACKEND_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      ...(init?.headers ?? {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    // A 401 on the login call itself just means "wrong password" — nothing
    // to clear, nowhere else to send them. A 401 on anything else means an
    // expired/invalid session, so bounce back to login instead of leaving
    // the user staring at a raw "Invalid or expired session" error string
    // inline in whichever tab they were on.
    if (res.status === 401 && path !== "/api/auth/login" && typeof window !== "undefined") {
      localStorage.removeItem(TOKEN_KEY);
      window.location.href = "/login";
    }
    throw new ApiError(res.status, body.detail ?? `Request to ${path} failed with status ${res.status}.`);
  }
  if (res.status === 204) return null as T;
  const text = await res.text();
  return text ? JSON.parse(text) : (null as T);
}

export function login(email: string, password: string): Promise<{ access_token: string }> {
  return apiFetch("/api/auth/login", null, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export function signup(email: string, password: string): Promise<{ access_token: string }> {
  return apiFetch("/api/auth/signup", null, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
}

export function getMe(token: string | null): Promise<Me> {
  return apiFetch("/api/auth/me", token);
}

export function getPlans(): Promise<Plan[]> {
  return apiFetch("/api/billing/plans", null);
}

export function createCheckout(token: string | null, plan: string): Promise<{ checkout_url: string }> {
  return apiFetch("/api/billing/checkout", token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plan }),
  });
}

export function createBillingPortal(token: string | null): Promise<{ portal_url: string }> {
  return apiFetch("/api/billing/portal", token, { method: "POST" });
}

export function sendContactMessage(name: string, email: string, message: string): Promise<{ sent: boolean }> {
  return apiFetch("/api/contact", null, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email, message }),
  });
}

export function createAds(token: string | null, url: string): Promise<AdSet> {
  return apiFetch("/api/ads/create", token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
}

export function getAdHistory(token: string | null): Promise<AdGeneration[]> {
  return apiFetch("/api/ads/history", token);
}

export function createVideoScript(
  token: string | null,
  productName: string,
  productDescription: string,
  durationSeconds: number
): Promise<{ scenes: string[] }> {
  return apiFetch("/api/video-ads/script", token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ product_name: productName, product_description: productDescription, duration_seconds: durationSeconds }),
  });
}

export function createVideoAd(
  token: string | null,
  images: File[],
  productName: string,
  productDescription: string,
  durationSeconds: number,
  script?: string[]
): Promise<VideoAd> {
  const form = new FormData();
  images.forEach((f) => form.append("images", f));
  form.append("product_name", productName);
  form.append("product_description", productDescription);
  form.append("duration_seconds", String(durationSeconds));
  if (script) script.forEach((line) => form.append("script", line));
  return apiFetch("/api/video-ads/create", token, { method: "POST", body: form });
}

export function getVideoHistory(token: string | null): Promise<VideoGeneration[]> {
  return apiFetch("/api/video-ads/history", token);
}

export async function fetchVideoBlobUrl(token: string | null, videoUrl: string): Promise<string> {
  const res = await fetch(`${BACKEND_URL}${videoUrl}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new ApiError(res.status, "Couldn't load the video.");
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}

export function getPresenters(token: string | null): Promise<Presenter[]> {
  return apiFetch("/api/ugc-ads/presenters", token);
}

export function getVoices(token: string | null): Promise<Voice[]> {
  return apiFetch("/api/ugc-ads/voices", token);
}

export function createUgcScript(
  token: string | null,
  prompt: string,
  productName: string,
  productDescription: string
): Promise<UGCScript> {
  return apiFetch("/api/ugc-ads/script", token, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, product_name: productName, product_description: productDescription }),
  });
}

export function createUgcAd(
  token: string | null,
  images: File[],
  prompt: string,
  productName: string,
  productDescription: string,
  presenterId: string,
  presenterName: string,
  voiceId: string,
  voiceName: string,
  ctaText: string,
  script?: UGCScript
): Promise<UGCAd> {
  const form = new FormData();
  images.forEach((f) => form.append("images", f));
  form.append("prompt", prompt);
  form.append("product_name", productName);
  form.append("product_description", productDescription);
  form.append("presenter_id", presenterId);
  form.append("presenter_name", presenterName);
  form.append("voice_id", voiceId);
  form.append("voice_name", voiceName);
  form.append("cta_text", ctaText);
  if (script) {
    form.append("script_hook", script.hook);
    form.append("script_intro", script.intro);
    script.benefits.forEach((b) => form.append("script_benefits", b));
    form.append("script_cta_line", script.cta_line);
  }
  return apiFetch("/api/ugc-ads/create", token, { method: "POST", body: form });
}

export function getUgcHistory(token: string | null): Promise<UGCGeneration[]> {
  return apiFetch("/api/ugc-ads/history", token);
}
