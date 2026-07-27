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

