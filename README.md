# AI Ad Creator ⭐⭐⭐⭐⭐

One click. Paste a product URL. Get:

- TikTok ads (hook, script, caption, hashtags)
- Facebook ads (primary text, headline, description)
- Google Ads (8 headline variants, 3 description variants)
- Instagram caption
- 5 standalone headline variants
- A persuasive product description
- An email campaign (subject, preview text, body)

A separate personal project, unrelated to this account's other apps —
new repo, own codebase, own deploy.

## How it actually works

1. **Scrape** (`backend/app/scraper.py`) — fetches the product page and pulls
   title/description/price/image from its Open Graph / Twitter Card meta
   tags (what nearly every e-commerce platform sets for link previews),
   falling back to `<title>`/meta description if those are missing.
2. **Generate** (`backend/app/ad_generator.py`) — sends that scraped info to
   the Claude API in one call, with a prompt asking for every channel's copy
   as a single JSON object, so every channel stays grounded in the same real
   product facts instead of each one inventing its own details.

**This is the one part of the app that costs real money to run.** There's
no free way to generate copy that reads like an actual ad instead of a
templated mad-lib — it needs a real language model. Every "Create ads"
click is one paid Claude API call, gated behind `ANTHROPIC_API_KEY`. If
that key isn't set, the app tells you so directly instead of failing
silently or faking a result.

## Quickstart

### Option A — Docker (runs locally, one command)

```bash
cp backend/.env.example backend/.env   # fill in ANTHROPIC_API_KEY at minimum
docker compose up --build
```

### Option B — run locally without Docker

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in ANTHROPIC_API_KEY at minimum
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

Log in with the owner credentials from `backend/.env` (defaults:
`owner@example.com` / `changeme123` for local dev only).

### Option C — Deploy to Render

This repo includes a [`render.yaml`](render.yaml) blueprint. Same two-step
gotcha as any Next.js app using build-time API rewrites: fill in
`BACKEND_URL` (frontend) and `CORS_ORIGINS` (backend) with each other's
assigned URL after the first deploy, then **redeploy the frontend** — that
one needs a full rebuild, not just a restart, since `next.config.js`'s
rewrite is resolved at build time. Also fill in `ANTHROPIC_API_KEY` on the
backend, or ad generation will return a clear "no API key" error instead of
silently doing nothing.

**Note on history:** Render's free plan has no persistent disk, so the
SQLite-backed "past generations" history (`GET /api/ads/history`) is wiped
on every redeploy/restart. Fine for trying it out; add a paid disk (or
point `DATABASE_URL` at a real Postgres instance) if you want that history
to actually last.

## What's real here

- **Real scraping**, not a mock — Open Graph meta tags, verified against a
  live page during development (see git history / the test suite's fixtures
  for the exact HTML shapes handled).
- **Real ad copy from a real model** — every field in the response
  (`AdSetOut` in `backend/app/schemas.py`) comes from one live Claude API
  call grounded in the scraped product info, not templated filler text.
- **Single-owner auth**, same pattern as this account's other personal
  tools: one seeded account, bcrypt-hashed password, JWT session, no public
  signup.
- **A real pytest suite** (`backend/tests/`) covering the scraper against
  both Open-Graph and plain-HTML fixtures, the ad generator's JSON parsing
  (including markdown-fenced responses and the missing-API-key guard) with
  the Anthropic client mocked out so tests never spend real money, and the
  full auth + ad-creation + history API surface.

## What's not built (yet)

- **Multi-language output.** The prompt doesn't currently ask for a target
  language — it writes in whatever language the scraped page content is in.
  Worth adding as an explicit parameter if you sell into non-English markets.
- **Image generation.** Ad *copy* only for now — no auto-generated creative
  images/video. The scraped product image is reused as-is in the UI.
  Real image generation is its own model call (and its own cost) — a
  reasonable next addition once the copy side is proven useful.
- **Editing/regenerating a single section.** Right now a "Create ads" click
  regenerates the whole set; there's no "just redo the TikTok script"
  button yet, though the data model (one JSON blob per generation) would
  need to change to support per-section history for that.

## Responsible use

Scraped product info is only as accurate as the page's own meta tags — the
model is instructed not to invent claims, prices, or guarantees beyond what
was scraped, but always read the generated copy before publishing it.
Nothing here checks ad-platform policy compliance (TikTok/Facebook/Google
each have their own content rules) — that's still on you before you spend
real ad budget on it.
