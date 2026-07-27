"""Turns scraped product info into a full ad set via the Claude API — one
call, one product, every channel. There's no free substitute for this part:
generating copy that actually reads like a real ad (not a templated
mad-lib) needs an actual language model, so this module is the one place in
the app that costs money to run, gated behind ANTHROPIC_API_KEY."""

import anthropic
from fastapi import HTTPException

from app.config import ANTHROPIC_MODEL
from app.llm import extract_json, get_client
from app.scraper import ProductInfo

SYSTEM_PROMPT = """You are a senior direct-response copywriter. Given a \
product's scraped page info, write a complete, ready-to-post ad set for it.

Respond with ONLY a single JSON object (no markdown fences, no commentary) \
with exactly this shape:

{
  "tiktok_ad": {"hook": string, "script": string, "caption": string, "hashtags": [string, ...]},
  "facebook_ad": {"primary_text": string, "headline": string, "description": string},
  "google_ads": {"headlines": [string, ...], "descriptions": [string, ...]},
  "instagram_caption": string,
  "headlines": [string, ...],
  "product_description": string,
  "email_campaign": {"subject": string, "preview_text": string, "body": string}
}

Rules:
- tiktok_ad.hook: one punchy spoken line for the first 2 seconds of video.
- tiktok_ad.script: a short 15-30 second voiceover/on-screen script, native \
to TikTok's casual tone, not a formal ad read.
- facebook_ad.headline: under 40 characters. facebook_ad.description: under \
30 characters.
- google_ads.headlines: exactly 8 variants, each 30 characters or fewer. \
google_ads.descriptions: exactly 3 variants, each 90 characters or fewer.
- instagram_caption: include relevant hashtags inline, conversational tone.
- headlines: 5 punchy standalone headline variants usable anywhere (ads, \
landing pages, banners).
- product_description: a persuasive, SEO-friendly product description, \
120-180 words, benefit-led not just feature-listed.
- email_campaign.body: plain text, 100-200 words, with a clear call to action.
- Base every claim only on the product info given. Never invent specs, \
prices, or guarantees that weren't provided.
- Match the tone to the product (playful for fun/casual items, trustworthy \
for higher-consideration ones).
"""


def generate_ad_set(product: ProductInfo) -> dict:
    client = get_client()
    user_message = (
        f"Product URL: {product.url}\n"
        f"Title: {product.title}\n"
        f"Description: {product.description or '(none found on page)'}\n"
        f"Price: {product.price or '(not found)'}\n"
        f"Site: {product.site_name or '(unknown)'}\n"
    )

    try:
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except anthropic.APIError as exc:
        raise HTTPException(status_code=502, detail=f"Ad generation failed: {exc}") from exc

    text = "".join(block.text for block in response.content if block.type == "text")
    return extract_json(text)
