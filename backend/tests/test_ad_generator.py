from types import SimpleNamespace

import pytest

from app import ad_generator
from app.scraper import ProductInfo

VALID_JSON = """{
  "tiktok_ad": {"hook": "h", "script": "s", "caption": "c", "hashtags": ["#a"]},
  "facebook_ad": {"primary_text": "p", "headline": "h", "description": "d"},
  "google_ads": {"headlines": ["h1"], "descriptions": ["d1"]},
  "instagram_caption": "ig",
  "headlines": ["H1"],
  "product_description": "desc",
  "email_campaign": {"subject": "s", "preview_text": "p", "body": "b"}
}"""


def _fake_product():
    return ProductInfo(
        url="https://example.com/p",
        title="Widget",
        description="A great widget.",
        price="19.99 USD",
        image="https://example.com/w.jpg",
        site_name="ExampleShop",
    )


def _fake_anthropic_client(response_text):
    text_block = SimpleNamespace(type="text", text=response_text)
    fake_response = SimpleNamespace(content=[text_block])
    messages = SimpleNamespace(create=lambda **kwargs: fake_response)
    return SimpleNamespace(messages=messages)


def test_generate_ad_set_parses_valid_json(monkeypatch):
    monkeypatch.setattr(ad_generator, "ANTHROPIC_API_KEY", "fake-key")
    monkeypatch.setattr(ad_generator, "_client", lambda: _fake_anthropic_client(VALID_JSON))
    result = ad_generator.generate_ad_set(_fake_product())
    assert result["tiktok_ad"]["hook"] == "h"
    assert result["google_ads"]["headlines"] == ["h1"]


def test_generate_ad_set_strips_markdown_fences(monkeypatch):
    fenced = f"```json\n{VALID_JSON}\n```"
    monkeypatch.setattr(ad_generator, "ANTHROPIC_API_KEY", "fake-key")
    monkeypatch.setattr(ad_generator, "_client", lambda: _fake_anthropic_client(fenced))
    result = ad_generator.generate_ad_set(_fake_product())
    assert result["instagram_caption"] == "ig"


def test_generate_ad_set_raises_on_missing_api_key(monkeypatch):
    monkeypatch.setattr(ad_generator, "ANTHROPIC_API_KEY", "")
    with pytest.raises(Exception):
        ad_generator.generate_ad_set(_fake_product())


def test_generate_ad_set_raises_on_invalid_json(monkeypatch):
    monkeypatch.setattr(ad_generator, "ANTHROPIC_API_KEY", "fake-key")
    monkeypatch.setattr(ad_generator, "_client", lambda: _fake_anthropic_client("not json"))
    with pytest.raises(Exception):
        ad_generator.generate_ad_set(_fake_product())
