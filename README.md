# AI Ad Creator ⭐⭐⭐⭐⭐

Two ways in, both one click:

**Text Ads** — paste a product URL, get:
- TikTok ads (hook, script, caption, hashtags)
- Facebook ads (primary text, headline, description)
- Google Ads (8 headline variants, 3 description variants)
- Instagram caption
- 5 standalone headline variants
- A persuasive product description
- An email campaign (subject, preview text, body)

**Video Ad** — upload product photos, pick a length (20/30/40/50/60s), get a
real MP4: an AI-written script, a spoken voiceover, your images panned and
zoomed across (Ken Burns style) with the script as animated captions, and a
background tone mixed in underneath.

A separate personal project, unrelated to this account's other apps —
new repo, own codebase, own deploy.

## How it actually works

### Text ads

1. **Scrape** (`backend/app/scraper.py`) — fetches the product page and pulls
   title/description/price/image from its Open Graph / Twitter Card meta
   tags (what nearly every e-commerce platform sets for link previews),
   falling back to `<title>`/meta description if those are missing.
2. **Generate** (`backend/app/ad_generator.py`) — sends that scraped info to
   the Claude API in one call, with a prompt asking for every channel's copy
   as a single JSON object, so every channel stays grounded in the same real
   product facts instead of each one inventing its own details.

### Video ads

1. **Script** (`backend/app/video_generator.py`) — one Claude call writes a
   scene-by-scene script sized to the requested length (~5 seconds of
   narration per scene).
2. **Voice** — each scene's line is voiced locally by `espeak-ng`, a free,
   offline text-to-speech engine. Genuinely synthetic-sounding — not a
   premium neural voice — but real automated speech at zero marginal cost.
3. **Visuals** — `ffmpeg`'s `zoompan` filter pans/zooms across your uploaded
   product images per scene (the "Ken Burns effect"), with the script
   rendered as animated captions via `drawtext`.
4. **Sound bed** — a simple ambient tone bed, procedurally generated with
   `ffmpeg`'s `aevalsrc` (three slowly-detuning sine waves) and mixed in
   under the voiceover at low volume. Not licensed music — there's no
   reliable, free, legal way to source real royalty-free tracks at request
   time — but it's real generated audio, not silence.
5. **This is deliberately not** a photorealistic AI-video generator
   (Runway/Luma/Sora-style tools that synthesize footage from a text
   prompt) — those charge real money per second of output via a third-party
   video-gen API this app doesn't integrate. This composes a video from
   *your own* product photos instead, which is why the only paid step is
   the same one text ads already had: one Claude call to write the script.
   Voice, visuals, and rendering all run locally afterward, so a video costs
   nothing beyond that one text generation.
6. **The rendered length isn't forced to match the requested one exactly.**
   It's however long the narration naturally takes — a "30-second" ad might
   render at 27 or 33 seconds. Artificially stretching or speeding up
   speech to hit an exact number would sound worse than just being honest
   that the number is a target, not a guarantee.

**Ad copy generation is the one part of the app that costs real money to
run.** There's no free way to generate copy — or a video script — that
reads like something an actual copywriter wrote; it needs a real language
model. Every "Create ads" or "Make video ad" click makes one paid Claude
API call, gated behind `ANTHROPIC_API_KEY`. If that key isn't set, the app
tells you so directly instead of failing silently or faking a result.
Voice, visuals, and video rendering are all free and local.

## Quickstart

### Option A — Docker (runs locally, one command)

```bash
cp backend/.env.example backend/.env   # fill in ANTHROPIC_API_KEY at minimum
docker compose up --build
```

### Option B — run locally without Docker

Video ads need `ffmpeg` and `espeak-ng` installed as system binaries (not
Python packages) — `apt-get install ffmpeg espeak-ng fonts-dejavu-core` on
Debian/Ubuntu, `brew install ffmpeg espeak-ng` on macOS. Text ads don't need
either.

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
SQLite-backed "past generations" history (`GET /api/ads/history` and
`GET /api/video-ads/history`) — and the rendered video files themselves,
under `VIDEO_STORAGE_DIR` — are wiped on every redeploy/restart. Fine for
trying it out; add a paid disk (or point `DATABASE_URL` at a real Postgres
instance and `VIDEO_STORAGE_DIR` at persistent storage) if you want either
to actually last. Download any video you care about right after generating
it.

### Option D — Deploy to Google Cloud Run (free)

Google Cloud Run's free tier is a genuine standing allowance, not a
time-limited trial credit — it renews monthly, and since Cloud Run scales
to zero, a personal tool with occasional use shouldn't come close to it
(check [cloud.google.com/run/pricing](https://cloud.google.com/run/pricing)
for the current exact numbers, since free-tier terms do shift over time).
You'll still need a Google account with a card on file — that's Google
verifying you're not a bot, not a hidden charge; you stay at $0 as long as
you're under the free quota.

Everything below runs in **Cloud Shell** (the terminal icon in the Google
Cloud Console) — no local installs, `gcloud` is already there.

```bash
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

git clone https://github.com/samdayayd/ai-ad-creator.git
cd ai-ad-creator

# 1. Backend — gcloud builds the Dockerfile and deploys in one step.
#    --memory 1Gi gives ffmpeg's video encoding enough headroom.
gcloud run deploy ai-ad-creator-backend \
  --source ./backend \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --set-env-vars OWNER_EMAIL=you@example.com,OWNER_PASSWORD=CHANGE_ME,JWT_SECRET=$(openssl rand -hex 32),ANTHROPIC_API_KEY=sk-ant-...,CORS_ORIGINS=*

# Copy the URL gcloud prints for the backend (ends in .run.app) — you need
# it for the next step.

# 2. Frontend — same build-time-BACKEND_URL requirement as Render (see
#    frontend/cloudbuild.yaml's comment), so this is a build + deploy in
#    two commands instead of Cloud Run's one-line --source shortcut.
gcloud builds submit ./frontend \
  --config ./frontend/cloudbuild.yaml \
  --substitutions=_BACKEND_URL=PASTE_BACKEND_URL_HERE,_IMAGE=gcr.io/YOUR_PROJECT_ID/ai-ad-creator-frontend

gcloud run deploy ai-ad-creator-frontend \
  --image gcr.io/YOUR_PROJECT_ID/ai-ad-creator-frontend \
  --region us-central1 \
  --allow-unauthenticated

# 3. Now that the frontend has a URL too, lock CORS down to just it
#    instead of leaving it wide open.
gcloud run services update ai-ad-creator-backend \
  --region us-central1 \
  --update-env-vars CORS_ORIGINS=PASTE_FRONTEND_URL_HERE
```

If `gcr.io` isn't enabled on your project, `gcloud` will print the exact
Artifact Registry command to run instead — follow what it suggests rather
than fighting the `gcr.io` path.

**Same history caveat as Render, slightly sharper:** Cloud Run containers
have no persistent disk, and scaling to zero means a fresh container (and
therefore a freshly re-seeded, empty SQLite database) on the next request
after any idle period — not just on redeploys. The owner login always
comes back (the app reseeds it automatically on startup), but ad/video
history won't survive an idle-then-cold-start cycle. Fine for a tool you
use in occasional sessions; if you want history to actually persist, this
is the point where a real database (Cloud SQL) or object storage (Cloud
Storage bucket for `VIDEO_STORAGE_DIR`) stops being optional.

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
- **Real video files, not mocked ones.** `test_video_generator.py` runs the
  actual `ffmpeg`/`espeak-ng` pipeline end-to-end (only the Claude script
  call is mocked, to keep tests free) and asserts on the real MP4's video
  and audio streams. Verified manually too: uploaded a real photo through
  the actual UI, generated a video, and confirmed the frames show correctly
  wrapped, centered captions and the file plays with both voice and music
  tracks present.

## What's not built (yet)

- **Multi-language output.** Neither prompt currently asks for a target
  language — text ads write in whatever language the scraped page is in;
  video scripts default to English narration. Worth adding as an explicit
  parameter if you sell into non-English markets.
- **AI-generated images/footage.** Text ads reuse the scraped product image
  as-is; video ads reuse your uploaded photos with pans/zooms, not
  AI-synthesized visuals. Real image/video generation is a different (and
  much more expensive) kind of model call — see the video-ads section above
  for why that's a deliberate scope line, not an oversight.
- **Premium voiceover.** The video pipeline's TTS is `espeak-ng` — free,
  local, and audibly synthetic. Swapping in a paid neural TTS provider
  (ElevenLabs, OpenAI TTS) would sound much better at the cost of a second
  paid API per video, on top of the Claude script call.
- **Editing/regenerating a single section.** Right now a "Create ads" or
  "Make video ad" click regenerates the whole thing; there's no "just redo
  the TikTok script" or "just redo scene 3" button yet.

## Responsible use

Scraped product info is only as accurate as the page's own meta tags — the
model is instructed not to invent claims, prices, or guarantees beyond what
was given (scraped page info for text ads, your typed name/description for
video ads), but always read/watch the generated result before publishing
it. Nothing here checks ad-platform policy compliance (TikTok/Facebook/
Google each have their own content and disclosure rules, including around
synthetic voices in some jurisdictions) — that's still on you before you
spend real ad budget on it.
