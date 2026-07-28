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
# renders both count against the same quota — text ads don't, and remain
# available to any signed-in account (see README for why that's a
# deliberate, flagged tradeoff rather than an oversight). Numbers are
# plain config, not load-bearing — revisit once real D-ID/ElevenLabs
# per-video costs are known from actual usage.
PLAN_LIMITS = {"free": 5, "pro": 20, "max": 60}
PLAN_PRICE_SEK = {"free": 0, "pro": 199, "max": 499}
OWNER_PLAN = "owner"  # the seeded OWNER_EMAIL account — unlimited, not a paid plan

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

