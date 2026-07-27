import { AdGeneration, AdSet, VideoAd, VideoGeneration } from "./types";

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

export function createVideoAd(
  token: string | null,
  images: File[],
  productName: string,
  productDescription: string,
  durationSeconds: number
): Promise<VideoAd> {
  const form = new FormData();
  images.forEach((f) => form.append("images", f));
  form.append("product_name", productName);
  form.append("product_description", productDescription);
  form.append("duration_seconds", String(durationSeconds));
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
