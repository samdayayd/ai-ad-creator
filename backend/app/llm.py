"""Tiny shared layer over the Claude API — the one thing both ad_generator.py
(text ad copy) and video_generator.py (video ad scripts) both need: a client
that fails with a clear message when there's no API key, and a JSON parser
that tolerates markdown code fences."""

import json
import re

import anthropic
from fastapi import HTTPException

from app.config import ANTHROPIC_API_KEY


def get_client() -> anthropic.Anthropic:
    if not ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=503,
            detail=(
                "This needs an Anthropic API key. Set ANTHROPIC_API_KEY in the "
                "backend environment (get one at console.anthropic.com) — this "
                "is the one part of the app that costs money to run."
            ),
        )
    return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)


def extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\n?|\n?```$", "", text.strip())
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail="The AI's response wasn't valid JSON — try again.",
        ) from exc
