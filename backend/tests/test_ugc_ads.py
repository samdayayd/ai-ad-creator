import io
import tempfile
from pathlib import Path

from app.routers import ugc_ads as ugc_ads_router
from app.ugc_generator import UGCAdResult, UGCScript

FAKE_SCRIPT = UGCScript(hook="Hook.", intro="Intro.", benefits=["A.", "B.", "C."], cta_line="Go now.")


def _fake_generate_ugc_ad(*args, **kwargs):
    fd, path = tempfile.mkstemp(suffix=".mp4")
    with open(fd, "wb") as f:
        f.write(b"fake ugc mp4 bytes")
    return UGCAdResult(file_path=Path(path), script=kwargs.get("script") or FAKE_SCRIPT)


def _create_payload(**overrides):
    payload = {
        "prompt": "Make it fun",
        "product_name": "Earbuds",
        "presenter_id": "p1",
        "presenter_name": "Alex",
        "voice_id": "v1",
        "voice_name": "Rachel",
        "cta_text": "Buy Now",
    }
    payload.update(overrides)
    return payload


def _signup(client, email="free-ugc@example.com"):
    r = client.post("/api/auth/signup", json={"email": email, "password": "longenough"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_create_ugc_ad_requires_auth(client):
    r = client.post("/api/ugc-ads/create", data=_create_payload())
    assert r.status_code in (401, 403)


def test_create_ugc_ad_rejects_invalid_cta(client, token, monkeypatch):
    monkeypatch.setattr(ugc_ads_router, "generate_ugc_ad", _fake_generate_ugc_ad)
    r = client.post(
        "/api/ugc-ads/create",
        data=_create_payload(cta_text="Not A Real CTA"),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400


def test_create_ugc_ad_returns_metadata(client, token, monkeypatch):
    monkeypatch.setattr(ugc_ads_router, "generate_ugc_ad", _fake_generate_ugc_ad)
    r = client.post(
        "/api/ugc-ads/create",
        data=_create_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["presenter_name"] == "Alex"
    assert body["voice_name"] == "Rachel"
    assert body["cta_text"] == "Buy Now"
    assert body["script"]["hook"] == "Hook."
    assert body["video_url"] == f"/api/ugc-ads/{body['id']}/file"


def test_create_ugc_ad_watermarks_free_plan_but_not_owner(client, token, monkeypatch):
    calls = []

    def _recording_fake(*args, **kwargs):
        calls.append(kwargs.get("watermark"))
        return _fake_generate_ugc_ad(*args, **kwargs)

    monkeypatch.setattr(ugc_ads_router, "generate_ugc_ad", _recording_fake)
    free_token = _signup(client)

    client.post("/api/ugc-ads/create", data=_create_payload(), headers={"Authorization": f"Bearer {free_token}"})
    client.post("/api/ugc-ads/create", data=_create_payload(), headers={"Authorization": f"Bearer {token}"})
    assert calls == [True, False]


def test_create_ugc_ad_blocks_free_plan_after_ugc_specific_limit(client, monkeypatch):
    """Free plan allows 5 videos total but only 1 UGC ad — the tighter,
    UGC-specific sub-cap (config.UGC_PLAN_LIMITS) should kick in first."""
    monkeypatch.setattr(ugc_ads_router, "generate_ugc_ad", _fake_generate_ugc_ad)
    free_token = _signup(client)
    first = client.post("/api/ugc-ads/create", data=_create_payload(), headers={"Authorization": f"Bearer {free_token}"})
    assert first.status_code == 200, first.text
    blocked = client.post(
        "/api/ugc-ads/create", data=_create_payload(), headers={"Authorization": f"Bearer {free_token}"}
    )
    assert blocked.status_code == 402


def test_create_ugc_ad_blocked_by_general_video_quota_too(client, monkeypatch):
    """The overall video quota is checked before the UGC-specific one — a
    plan with its general quota exhausted should block a UGC ad even if
    the UGC-specific sub-quota still has room left."""
    from app.routers import video_ads as video_ads_router
    from app.video_generator import VideoAdResult, VideoScene

    def _fake_video(*args, **kwargs):
        fd, path = tempfile.mkstemp(suffix=".mp4")
        with open(fd, "wb"):
            pass
        return VideoAdResult(file_path=Path(path), actual_duration_seconds=18.5, scenes=[VideoScene(text="x", duration=5.0)])

    monkeypatch.setattr(video_ads_router, "generate_video_ad", _fake_video)
    free_token = _signup(client, email="quota-edge@example.com")

    # Exhaust the free plan's overall 5-video quota with cheap Ken-Burns ads.
    for _ in range(5):
        r = client.post(
            "/api/video-ads/create",
            data={"product_name": "Widget", "duration_seconds": "20"},
            files=[("images", ("p.jpg", io.BytesIO(b"fake"), "image/jpeg"))],
            headers={"Authorization": f"Bearer {free_token}"},
        )
        assert r.status_code == 200, r.text

    blocked = client.post(
        "/api/ugc-ads/create", data=_create_payload(), headers={"Authorization": f"Bearer {free_token}"}
    )
    assert blocked.status_code == 402
    assert "videos" in blocked.json()["detail"]  # the general-quota message, not the UGC-specific one


def test_create_ugc_ad_accepts_prewritten_script_and_skips_script_generation(client, token, monkeypatch):
    def _write_script_should_not_be_called(*args, **kwargs):
        raise AssertionError("write_ugc_script should be skipped when a script is provided")

    monkeypatch.setattr(ugc_ads_router, "generate_ugc_ad", _fake_generate_ugc_ad)
    monkeypatch.setattr("app.ugc_generator.write_ugc_script", _write_script_should_not_be_called)

    r = client.post(
        "/api/ugc-ads/create",
        data=_create_payload(
            script_hook="Edited hook.",
            script_intro="Edited intro.",
            script_benefits=["Edited A.", "Edited B.", "Edited C."],
            script_cta_line="Edited cta.",
        ),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["script"]["hook"] == "Edited hook."


def test_ugc_script_endpoint_requires_auth(client):
    r = client.post("/api/ugc-ads/script", json={"prompt": "p", "product_name": "n"})
    assert r.status_code in (401, 403)


def test_ugc_script_endpoint_returns_script_without_rendering(client, token, monkeypatch):
    monkeypatch.setattr(ugc_ads_router, "write_ugc_script", lambda prompt, name, desc: FAKE_SCRIPT)
    r = client.post(
        "/api/ugc-ads/script",
        json={"prompt": "Make it fun", "product_name": "Earbuds"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["hook"] == "Hook."
    assert r.json()["benefits"] == ["A.", "B.", "C."]


def test_ugc_history_starts_empty(client, token):
    r = client.get("/api/ugc-ads/history", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == []


def test_ugc_file_returns_404_for_missing_id(client, token):
    r = client.get("/api/ugc-ads/9999/file", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


def test_full_ugc_flow_history_and_file_download(client, token, monkeypatch):
    monkeypatch.setattr(ugc_ads_router, "generate_ugc_ad", _fake_generate_ugc_ad)
    create = client.post(
        "/api/ugc-ads/create",
        data=_create_payload(),
        headers={"Authorization": f"Bearer {token}"},
    )
    ugc_id = create.json()["id"]

    history = client.get("/api/ugc-ads/history", headers={"Authorization": f"Bearer {token}"})
    assert len(history.json()) == 1
    assert history.json()[0]["id"] == ugc_id

    file_response = client.get(f"/api/ugc-ads/{ugc_id}/file", headers={"Authorization": f"Bearer {token}"})
    assert file_response.status_code == 200
    assert file_response.content == b"fake ugc mp4 bytes"
