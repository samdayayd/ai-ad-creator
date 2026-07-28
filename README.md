# AI Ad Creator ⭐⭐⭐⭐⭐

Three ways in:

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

**UGC Ad** — one sentence + your product → a talking AI presenter (a D-ID
stock actor, not your own footage) reads an AI-written script in a real
voice (ElevenLabs), cut together with short cutaways of your product photos
and a call-to-action card. Needs two extra paid API keys — see its own
section below for exactly why, and for what it deliberately does *not*
claim to do.

Free to try (5 videos, watermarked), then Pro (199 kr/month) or Max
(499 kr/month) for more, no watermark — see [Plans & billing](#plans--billing).
Text ads are free on every plan; only video and UGC ad renders count
against a plan's quota.

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

0. **Write, then review** — `POST /api/video-ads/script` writes the script
   alone (no rendering, no quota spent) so you can edit any line before
   committing to the expensive render step; `POST /api/video-ads/create`
   accepts your edited lines and skips writing a new script when you pass
   them. Skip this and it writes+renders in one call, same as before.
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

**Ad copy generation is the one part of text/video ads that costs real money
to run.** There's no free way to generate copy — or a video script — that
reads like something an actual copywriter wrote; it needs a real language
model. Every "Create ads" or "Make video ad" click makes one paid Claude
API call, gated behind `ANTHROPIC_API_KEY`. If that key isn't set, the app
tells you so directly instead of failing silently or faking a result.
Voice, visuals, and video rendering are all free and local.

### UGC ads

0. **Write, then review** — same pattern as video ads: `POST
   /api/ugc-ads/script` writes hook/intro/benefits/CTA-line alone, no
   quota spent; `POST /api/ugc-ads/create` accepts your edited script_*
   fields and skips writing a new one when you pass them.
1. **Script** (`backend/app/ugc_generator.py`) — one Claude call writes a
   hook, a spoken intro, three benefit lines, and a closing line that leads
   into the CTA, from your one-sentence brief plus the product info.
2. **Voice** — the full script is synthesized by the ElevenLabs API
   (`ELEVENLABS_API_KEY`) into a real neural voice, in whichever of your
   account's voices you pick. Unlike the Ken-Burns video pipeline, there's
   no free fallback here — this is the upgrade path for the "voice is
   terrible" complaint `espeak-ng` earns honestly.
3. **Presenter** — that audio is sent to the D-ID API (`D_ID_API_KEY`),
   which animates one of *D-ID's own* pre-licensed stock presenters
   speaking it (fetched live from `GET /clips/presenters`, never a face
   image you'd have to source and personally clear usage rights for).
4. **Edit** — `ffmpeg` concatenates the presenter clip with up to 2 short
   Ken-Burns cutaways of your uploaded product photos and a text card for
   the CTA you picked (Buy Now / Shop Today / Limited Offer / Order Today /
   Learn More / Visit Website).

**Why "presenter + product cutaways" and not a presenter that holds or uses
your product**: no commercial API — D-ID, HeyGen, and Synthesia included —
generates a photorealistic person physically interacting with an arbitrary
uploaded object today. That capability doesn't exist yet at any price. What
real UGC-ad tools do under the hood is exactly this: a talking-avatar shot
edited together with separate product shots, the way a real ad would be
cut. This is that, honestly, rather than a feature that doesn't exist
marketed as if it does.

**Two separate paid accounts, both distinct from `ANTHROPIC_API_KEY`:**
- `ELEVENLABS_API_KEY` — get one at [elevenlabs.io](https://elevenlabs.io).
- `D_ID_API_KEY` — get one at [studio.d-id.com](https://studio.d-id.com).

Neither key is bundled or free — both are pay-per-use accounts you sign up
for and fund yourself, and D-ID in particular often expects a paid plan
(not just a free trial) before its API is usable. If either key is unset,
the UGC Ad tab tells you so directly instead of failing silently. Both
integrations are implemented from each provider's documented API shape but
haven't been exercised against a live account from this repo — expect the
first real run to need a small field-name fix or two once you plug in real
keys, the same way the Cloud Run deploy needed a few IAM permission grants
before it worked. That's normal for a first real integration test, not a
sign the code is broken.

## Plans & billing

Anyone can sign up (`POST /api/auth/signup` — email + password, at least 8
characters). Every account gets a plan that caps how many video/UGC ad
renders it can create; text ads (paste-a-URL copy generation) are free and
ungated on every plan — the tradeoff there is that any signed-in account
can still spend a Claude API call on a text ad with no cap, which is worth
knowing if abuse becomes a real cost, not just a theoretical one.

| Plan  | Price       | Videos                | Watermark |
|-------|-------------|------------------------|-----------|
| Free  | 0 kr        | 5, lifetime (not/mo)   | Yes       |
| Pro   | 199 kr/mo   | 20/month               | No        |
| Max   | 499 kr/mo   | 60/month               | No        |

The numbers live in `backend/app/config.py` (`PLAN_LIMITS`, `PLAN_PRICE_SEK`)
— plain config, not load-bearing, change them freely. They were picked to
stay profitable against real per-video costs (Claude + ElevenLabs + D-ID for
UGC ads), not from any actual usage data yet — revisit once you have some.
The app owner's own account (seeded from `OWNER_EMAIL`) is unlimited and
never watermarked, on a separate internal `"owner"` plan nobody can buy.

### Setting up Stripe

1. Create a [Stripe](https://dashboard.stripe.com) account and, in **Test
   mode** first, create two recurring monthly **Products** — "Pro" (199 kr)
   and "Max" (499 kr) — and copy each one's **Price ID** (`price_...`).
2. Get your test **Secret key** from the Stripe dashboard.
3. Register a webhook endpoint in Stripe pointing at
   `https://YOUR_BACKEND_URL/api/billing/webhook`, subscribed to at least:
   `checkout.session.completed`, `customer.subscription.updated`,
   `customer.subscription.deleted`, `invoice.paid`. Copy the **Signing
   secret** (`whsec_...`) Stripe gives you for that endpoint.
4. Set `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_ID_PRO`,
   `STRIPE_PRICE_ID_MAX`, and `FRONTEND_URL` (your real frontend URL, used
   to build the Checkout/portal redirect links) on the backend.
5. Test with a subscription, using
   [Stripe's test card numbers](https://docs.stripe.com/testing) — never a
   real card while `STRIPE_SECRET_KEY` is a test key.
6. This integration is implemented from Stripe's documented API shapes but
   hasn't been exercised against a live Stripe account from this repo —
   same caveat as D-ID/ElevenLabs above: expect a small fix on the first
   real checkout/webhook test.

**Going live with real payments — two things Stripe itself won't stop you
from skipping, but you shouldn't:**

- **A persistent database.** This app defaults to SQLite on local disk,
  which — as the deploy sections below explain — gets wiped on every
  Render/Cloud-Run cold start or redeploy. That's an acceptable tradeoff
  for a free personal tool's history; it is **not acceptable** once real
  customers' accounts and Stripe subscription links live in that table. Set
  `DATABASE_URL` to a real Postgres instance (e.g. a small Cloud SQL
  instance, or Render's managed Postgres) before switching Stripe out of
  test mode. `psycopg2-binary` is already in `requirements.txt` for this —
  SQLAlchemy handles the rest via `DATABASE_URL`'s scheme.
- **Being legally allowed to accept recurring payments.** Depending on
  where you live, charging real subscribers may require registering as a
  business for tax purposes (in Sweden, at minimum an *enskild firma* with
  F-skatt) before Stripe will let you leave test mode in practice. That's
  outside anything this codebase can set up for you — sort it out before
  flipping `STRIPE_SECRET_KEY` from a test key to a live one.

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

Sign up for a real account at `/signup`, or log in with the owner
credentials from `backend/.env` (defaults: `owner@example.com` /
`changeme123` for local dev only) for unlimited, unwatermarked access.

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

**Adding UGC ads after the fact:** the two extra keys (`ELEVENLABS_API_KEY`,
`D_ID_API_KEY`) are optional and best set separately rather than folded into
the big `--set-env-vars` command above — a real secret typed straight into
a command you can see is easy to accidentally paste into chat/logs/shell
history. Use `read -s` on its own line instead, so the key is never visible:

```bash
read -s ELEVENLABS_KEY
gcloud run services update ai-ad-creator-backend --region us-central1 --update-env-vars ELEVENLABS_API_KEY=$ELEVENLABS_KEY
unset ELEVENLABS_KEY

read -s DID_KEY
gcloud run services update ai-ad-creator-backend --region us-central1 --update-env-vars D_ID_API_KEY=$DID_KEY
unset DID_KEY
```

Run each `read -s` line by itself, paste the key at the blank prompt it
leaves, then run the next line — don't edit the command itself.

**Adding Stripe billing after the fact**, same safe pattern — plus
`FRONTEND_URL` and the two Price IDs, which aren't secrets and are fine in
a normal `--update-env-vars` call:

```bash
gcloud run services update ai-ad-creator-backend \
  --region us-central1 \
  --update-env-vars FRONTEND_URL=PASTE_FRONTEND_URL_HERE,STRIPE_PRICE_ID_PRO=price_...,STRIPE_PRICE_ID_MAX=price_...

read -s STRIPE_KEY
gcloud run services update ai-ad-creator-backend --region us-central1 --update-env-vars STRIPE_SECRET_KEY=$STRIPE_KEY
unset STRIPE_KEY

read -s STRIPE_WHSEC
gcloud run services update ai-ad-creator-backend --region us-central1 --update-env-vars STRIPE_WEBHOOK_SECRET=$STRIPE_WHSEC
unset STRIPE_WHSEC
```

**Before accepting real subscriptions on Cloud Run specifically:** the
persistent-database requirement from
[Plans & billing](#plans--billing) applies with extra force here — see the
history caveat right below. A cold start doesn't just clear old video
history on Cloud Run, it clears *every account and subscription link* in
the default SQLite setup. Set `DATABASE_URL` to a real Postgres instance
(Cloud SQL is the natural fit alongside the rest of this stack) before
`STRIPE_SECRET_KEY` is a live key, not a test one.

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
- **Real public accounts and billing.** Anyone can sign up; bcrypt-hashed
  passwords, per-IP rate limiting on both login and signup, JWT sessions.
  Plan/quota state (`plan`, `videos_used`, `usage_period_start`,
  `stripe_customer_id`) lives on the `User` row and is kept in sync by a
  real Stripe webhook, not a mocked billing stub. The app owner's own
  account is exempt (unlimited, on a separate internal plan) — see
  [Plans & billing](#plans--billing).
- **A real pytest suite** (`backend/tests/`) covering the scraper against
  both Open-Graph and plain-HTML fixtures (plus SSRF-blocking tests for
  private/metadata IPs and redirect bypasses), the ad generator's JSON
  parsing (including markdown-fenced responses and the missing-API-key
  guard), quota rollover/lifetime-cap logic, and the Stripe webhook
  dispatch logic — all with the Anthropic/Stripe/D-ID/ElevenLabs clients
  mocked out so tests never spend real money, plus the full auth +
  ad-creation + billing + history API surface.
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
- **Editing a single section, not the whole script.** Video and UGC ads now
  let you review/edit the AI-written script before rendering (see their
  "Write, then review" step above) — but it's edit-the-whole-thing, not
  "just redo scene 3" or "just redo the hook." Text ads still regenerate
  the entire ad set on every click; there's no per-channel redo yet.
- **Usage analytics.** There's no dashboard for the app owner to see signup
  counts, plan distribution, or churn — that data all exists in the `User`
  table, just with no UI built on top of it yet.

## Responsible use

Scraped product info is only as accurate as the page's own meta tags — the
model is instructed not to invent claims, prices, or guarantees beyond what
was given (scraped page info for text ads, your typed name/description for
video ads), but always read/watch the generated result before publishing
it. Nothing here checks ad-platform policy compliance (TikTok/Facebook/
Google each have their own content and disclosure rules, including around
synthetic voices in some jurisdictions) — that's still on you before you
spend real ad budget on it.
