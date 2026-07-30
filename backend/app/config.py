import os

OWNER_EMAIL = os.environ.get("OWNER_EMAIL", "owner@example.com")
OWNER_PASSWORD = os.environ.get("OWNER_PASSWORD", "changeme123")
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24 * 7  # a week — a personal single-owner tool, not a public multi-session product

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")

CORS_ORIGINS = [o.strip() for o in os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./ai_ad_creator.db")

VIDEO_STORAGE_DIR = os.environ.get("VIDEO_STORAGE_DIR", "./generated_videos")
ALLOWED_VIDEO_DURATIONS = (20, 30, 40, 50, 60)

# UGC ad pipeline: D-ID animates one of its own pre-licensed stock presenters
# to speak ElevenLabs-generated audio. Both are separate paid third-party
# accounts from ANTHROPIC_API_KEY — see ugc_generator.py's module docstring
# for why (no API sells a presenter that actually holds/uses an arbitrary
# uploaded product, so this is a talking presenter + product-cutaway edit,
# not literal product handling).
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
D_ID_API_KEY = os.environ.get("D_ID_API_KEY", "")
UGC_CTA_OPTIONS = ("Buy Now", "Shop Today", "Limited Offer", "Order Today", "Learn More", "Visit Website")

# Subscriptions. "free" is a lifetime cap (never resets) since it exists to
# let someone try the product, not as a recurring allowance; "pro"/"max" are
# monthly quotas that reset on each paid billing cycle. Video ad and UGC ad
# renders both count against the same overall quota — text ads don't, and
# remain available to any signed-in account (see README for why that's a
# deliberate, flagged tradeoff rather than an oversight).
#
# These numbers were tightened from an earlier, more generous pass (5/20/60)
# after working through real per-video cost math: Claude ($0.01-0.10) +
# ElevenLabs ($0.02-0.10) + D-ID (the dominant cost, billed by video
# time/credits) + hosting + Stripe's cut + an allowance for failed/
# regenerated renders puts a realistic video cost at $0.50-1.20, and
# possibly $1.50+ for premium avatars/voices. 20 videos for $19 (pro's old
# number) could lose money on a single heavy month; 10 does not, with room
# to spare. Still not measured against real usage — revisit once actual
# D-ID/ElevenLabs bills exist, in either direction.
PLAN_LIMITS = {"free": 3, "pro": 10, "max": 25}
PLAN_PRICE_SEK = {"free": 0, "pro": 199, "max": 499}

# UGC ads cost meaningfully more per generation than Ken-Burns video ads —
# one Claude call either way, but UGC also pays for ElevenLabs voice
# synthesis and D-ID presenter animation, both of which are subscription
# platforms with their own fixed monthly cost on top of per-generation
# charges. Without a separate, tighter cap, a plan's entire video quota
# could be spent on the expensive path, which the flat PLAN_LIMITS numbers
# above were never sized for. This is a second, smaller ceiling that
# applies only to UGC ads, subtracted from (not in addition to) the
# regular video quota above — same period/rollover behavior. Revisit both
# sets of numbers once real ElevenLabs/D-ID per-generation costs are known
# from actual usage; these are a deliberately conservative starting point,
# not measured data.
UGC_PLAN_LIMITS = {"free": 1, "pro": 3, "max": 8}
OWNER_PLAN = "owner"  # the seeded OWNER_EMAIL account — unlimited, not a paid plan

# Pay-as-you-go: one-time purchases, on top of (not instead of) a plan, that
# add non-expiring credits — lets a Free user try the product without
# subscribing, and lets a paid user who blows through their monthly
# allowance keep going instead of hitting a hard wall. Priced in USD
# directly (unlike the subscription plans, which are actually charged in
# SEK and only *displayed* in USD — see PricingPage's USD_PRICE comment)
# since these are real new charges, not a display conversion of an
# existing price. Priced well above the estimated per-video cost (see the
# PLAN_LIMITS comment above) so every purchase is independently profitable,
# regardless of which plan the buyer is on. Volume packs give a discount to
# reward committing to more up front while keeping subscriptions the best
# per-video deal for regular users.
CREDIT_PACKS = {
    "standard_1": {"kind": "video", "credits": 1, "price_usd_cents": 300, "label": "1 Standard Video"},
    "standard_5": {"kind": "video", "credits": 5, "price_usd_cents": 1300, "label": "5 Standard Videos"},
    "standard_10": {"kind": "video", "credits": 10, "price_usd_cents": 2400, "label": "10 Standard Videos"},
    "ugc_1": {"kind": "ugc", "credits": 1, "price_usd_cents": 600, "label": "1 UGC Video"},
    "ugc_5": {"kind": "ugc", "credits": 5, "price_usd_cents": 2200, "label": "5 UGC Videos"},
    "ugc_10": {"kind": "ugc", "credits": 10, "price_usd_cents": 4000, "label": "10 UGC Videos"},
}

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PRICE_ID_PRO = os.environ.get("STRIPE_PRICE_ID_PRO", "")
STRIPE_PRICE_ID_MAX = os.environ.get("STRIPE_PRICE_ID_MAX", "")

# Contact form — relays a visitor's message to the owner's private inbox via
# SMTP. CONTACT_EMAIL is never sent to the frontend/client; it only lives
# here, server-side. Works with any SMTP provider — Gmail + an App Password
# (myaccount.google.com/apppasswords) needs no new third-party signup at
# all if you're fine sending from your own address.
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "")

