from app.routers import ads as ads_router
from app.scraper import ProductInfo

FAKE_RESULT = {
    "tiktok_ad": {"hook": "h", "script": "s", "caption": "c", "hashtags": ["#a"]},
    "facebook_ad": {"primary_text": "p", "headline": "h", "description": "d"},
    "google_ads": {"headlines": ["h1"], "descriptions": ["d1"]},
    "instagram_caption": "ig",
    "headlines": ["H1"],
    "product_description": "desc",
    "email_campaign": {"subject": "s", "preview_text": "p", "body": "b"},
}


def _fake_product():
    return ProductInfo(
        url="https://example.com/p",
        title="Widget",
        description="A great widget.",
        price="19.99 USD",
        image="https://example.com/w.jpg",
        site_name="ExampleShop",
    )


def _mock_pipeline(monkeypatch):
    monkeypatch.setattr(ads_router, "fetch_product_info", lambda url: _fake_product())
    monkeypatch.setattr(ads_router, "generate_ad_set", lambda product: FAKE_RESULT)


def test_login_success(client):
    r = client.post("/api/auth/login", json={"email": "owner@example.com", "password": "changeme123"})
    assert r.status_code == 200
    assert "access_token" in r.json()


def test_login_wrong_password(client):
    r = client.post("/api/auth/login", json={"email": "owner@example.com", "password": "wrong"})
    assert r.status_code == 401


def test_login_locks_out_after_repeated_failures(client):
    for _ in range(5):
        r = client.post("/api/auth/login", json={"email": "owner@example.com", "password": "wrong"})
        assert r.status_code == 401
    locked = client.post("/api/auth/login", json={"email": "owner@example.com", "password": "wrong"})
    assert locked.status_code == 429
    # Locked out even with the CORRECT password — the whole point of a
    # lockout is stopping further guesses regardless of what's guessed next.
    still_locked = client.post("/api/auth/login", json={"email": "owner@example.com", "password": "changeme123"})
    assert still_locked.status_code == 429


def test_login_success_clears_failure_count(client):
    for _ in range(3):
        client.post("/api/auth/login", json={"email": "owner@example.com", "password": "wrong"})
    ok = client.post("/api/auth/login", json={"email": "owner@example.com", "password": "changeme123"})
    assert ok.status_code == 200
    # Back below the lockout threshold after a successful login.
    r = client.post("/api/auth/login", json={"email": "owner@example.com", "password": "wrong"})
    assert r.status_code == 401


def test_signup_creates_account_and_returns_token(client):
    r = client.post("/api/auth/signup", json={"email": "new@example.com", "password": "longenough"})
    assert r.status_code == 200, r.text
    assert "access_token" in r.json()


def test_signup_new_account_starts_on_free_plan(client):
    signup = client.post("/api/auth/signup", json={"email": "new@example.com", "password": "longenough"})
    token = signup.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["plan"] == "free"
    assert me.json()["videos_remaining"] == 5


def test_signup_rejects_short_password(client):
    r = client.post("/api/auth/signup", json={"email": "new@example.com", "password": "short"})
    assert r.status_code == 400


def test_signup_rejects_duplicate_email(client):
    client.post("/api/auth/signup", json={"email": "dupe@example.com", "password": "longenough"})
    r = client.post("/api/auth/signup", json={"email": "dupe@example.com", "password": "longenough2"})
    assert r.status_code == 400


def test_signup_email_is_case_insensitive_for_duplicates(client):
    client.post("/api/auth/signup", json={"email": "Case@Example.com", "password": "longenough"})
    r = client.post("/api/auth/signup", json={"email": "case@example.com", "password": "longenough2"})
    assert r.status_code == 400


def test_signup_locks_out_after_repeated_signups(client):
    for i in range(5):
        r = client.post("/api/auth/signup", json={"email": f"user{i}@example.com", "password": "longenough"})
        assert r.status_code == 200
    locked = client.post("/api/auth/signup", json={"email": "user5@example.com", "password": "longenough"})
    assert locked.status_code == 429


def test_owner_account_has_unlimited_plan(client, token):
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["plan"] == "owner"
    assert me.json()["videos_remaining"] is None


def test_me_requires_auth(client):
    r = client.get("/api/auth/me")
    assert r.status_code in (401, 403)


def test_create_ads_requires_auth(client):
    r = client.post("/api/ads/create", json={"url": "https://example.com/p"})
    assert r.status_code in (401, 403)


def test_create_ads_returns_full_ad_set(client, token, monkeypatch):
    _mock_pipeline(monkeypatch)
    r = client.post(
        "/api/ads/create",
        json={"url": "https://example.com/p"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["product_title"] == "Widget"
    assert body["tiktok_ad"]["hook"] == "h"
    assert body["google_ads"]["headlines"] == ["h1"]
    assert body["email_campaign"]["subject"] == "s"


def test_ad_history_starts_empty(client, token):
    r = client.get("/api/ads/history", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == []


def test_ad_history_records_each_generation(client, token, monkeypatch):
    _mock_pipeline(monkeypatch)
    client.post(
        "/api/ads/create",
        json={"url": "https://example.com/p"},
        headers={"Authorization": f"Bearer {token}"},
    )
    r = client.get("/api/ads/history", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    history = r.json()
    assert len(history) == 1
    assert history[0]["product_url"] == "https://example.com/p"
    assert history[0]["result"]["headlines"] == ["H1"]
