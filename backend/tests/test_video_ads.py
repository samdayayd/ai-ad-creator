import io
import tempfile
from pathlib import Path

from app.routers import video_ads as video_ads_router
from app.video_generator import VideoAdResult, VideoScene


def _fake_generate_video_ad(
    product_name, product_description, duration_seconds, image_paths, workdir, script_lines=None, watermark=False
):
    # Written outside `workdir` — the router deletes that temp dir the
    # moment the request handler returns, same as the real generate_video_ad
    # moving its output into VIDEO_STORAGE_DIR before that cleanup happens.
    fd, path = tempfile.mkstemp(suffix=".mp4")
    with open(fd, "wb") as f:
        f.write(b"fake mp4 bytes")
    return VideoAdResult(
        file_path=Path(path),
        actual_duration_seconds=duration_seconds - 1.5,
        scenes=[VideoScene(text="Scene one.", duration=5.0), VideoScene(text="Scene two.", duration=5.0)],
    )


def _upload_files():
    return [("images", ("product.jpg", io.BytesIO(b"fake image bytes"), "image/jpeg"))]


def _signup(client, email="free-user@example.com"):
    r = client.post("/api/auth/signup", json={"email": email, "password": "longenough"})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_create_video_ad_requires_auth(client):
    r = client.post(
        "/api/video-ads/create",
        data={"product_name": "Widget", "duration_seconds": "20"},
        files=_upload_files(),
    )
    assert r.status_code in (401, 403)


def test_create_video_ad_rejects_invalid_duration(client, token):
    r = client.post(
        "/api/video-ads/create",
        data={"product_name": "Widget", "duration_seconds": "25"},
        files=_upload_files(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400


def test_create_video_ad_requires_at_least_one_image(client, token):
    r = client.post(
        "/api/video-ads/create",
        data={"product_name": "Widget", "duration_seconds": "20"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400


def test_create_video_ad_rejects_unsupported_file_type(client, token):
    r = client.post(
        "/api/video-ads/create",
        data={"product_name": "Widget", "duration_seconds": "20"},
        files=[("images", ("product.gif", io.BytesIO(b"fake"), "image/gif"))],
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400


def test_create_video_ad_returns_video_metadata(client, token, monkeypatch):
    monkeypatch.setattr(video_ads_router, "generate_video_ad", _fake_generate_video_ad)
    r = client.post(
        "/api/video-ads/create",
        data={"product_name": "Widget", "product_description": "A great widget.", "duration_seconds": "20"},
        files=_upload_files(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["product_title"] == "Widget"
    assert body["requested_duration_seconds"] == 20
    assert body["actual_duration_seconds"] == 18.5
    assert len(body["scenes"]) == 2
    assert body["video_url"] == f"/api/video-ads/{body['id']}/file"


def test_video_history_starts_empty(client, token):
    r = client.get("/api/video-ads/history", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json() == []


def test_video_file_requires_auth(client):
    r = client.get("/api/video-ads/1/file")
    assert r.status_code in (401, 403)


def test_video_file_returns_404_for_missing_id(client, token):
    r = client.get("/api/video-ads/9999/file", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404


def test_create_video_ad_watermarks_free_plan_but_not_owner(client, token, monkeypatch):
    calls = []

    def _recording_fake(*args, **kwargs):
        calls.append(kwargs.get("watermark"))
        return _fake_generate_video_ad(*args, **kwargs)

    monkeypatch.setattr(video_ads_router, "generate_video_ad", _recording_fake)

    free_token = _signup(client)
    client.post(
        "/api/video-ads/create",
        data={"product_name": "Widget", "duration_seconds": "20"},
        files=_upload_files(),
        headers={"Authorization": f"Bearer {free_token}"},
    )
    client.post(
        "/api/video-ads/create",
        data={"product_name": "Widget", "duration_seconds": "20"},
        files=_upload_files(),
        headers={"Authorization": f"Bearer {token}"},  # owner account
    )
    assert calls == [True, False]


def test_create_video_ad_blocks_free_plan_after_lifetime_limit(client, monkeypatch):
    monkeypatch.setattr(video_ads_router, "generate_video_ad", _fake_generate_video_ad)
    free_token = _signup(client)
    for _ in range(3):
        r = client.post(
            "/api/video-ads/create",
            data={"product_name": "Widget", "duration_seconds": "20"},
            files=_upload_files(),
            headers={"Authorization": f"Bearer {free_token}"},
        )
        assert r.status_code == 200, r.text
    blocked = client.post(
        "/api/video-ads/create",
        data={"product_name": "Widget", "duration_seconds": "20"},
        files=_upload_files(),
        headers={"Authorization": f"Bearer {free_token}"},
    )
    assert blocked.status_code == 402


def test_create_video_ad_accepts_prewritten_script_and_skips_script_generation(client, token, monkeypatch):
    def _write_script_should_not_be_called(*args, **kwargs):
        raise AssertionError("write_video_script should be skipped when a script is provided")

    monkeypatch.setattr(video_ads_router, "generate_video_ad", _fake_generate_video_ad)
    monkeypatch.setattr("app.video_generator.write_video_script", _write_script_should_not_be_called)

    r = client.post(
        "/api/video-ads/create",
        data={"product_name": "Widget", "duration_seconds": "20", "script": ["Edited line one.", "Edited line two."]},
        files=_upload_files(),
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text


def test_video_script_endpoint_returns_scenes_without_rendering(client, token, monkeypatch):
    monkeypatch.setattr(video_ads_router, "write_video_script", lambda title, desc, count: ["Line one.", "Line two."])
    r = client.post(
        "/api/video-ads/script",
        json={"product_name": "Widget", "product_description": "desc", "duration_seconds": 20},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["scenes"] == ["Line one.", "Line two."]


def test_video_script_endpoint_rejects_invalid_duration(client, token):
    r = client.post(
        "/api/video-ads/script",
        json={"product_name": "Widget", "duration_seconds": 25},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400


def test_full_flow_history_and_file_download(client, token, monkeypatch):
    monkeypatch.setattr(video_ads_router, "generate_video_ad", _fake_generate_video_ad)
    create = client.post(
        "/api/video-ads/create",
        data={"product_name": "Widget", "duration_seconds": "30"},
        files=_upload_files(),
        headers={"Authorization": f"Bearer {token}"},
    )
    video_id = create.json()["id"]

    history = client.get("/api/video-ads/history", headers={"Authorization": f"Bearer {token}"})
    assert len(history.json()) == 1
    assert history.json()[0]["id"] == video_id

    file_response = client.get(f"/api/video-ads/{video_id}/file", headers={"Authorization": f"Bearer {token}"})
    assert file_response.status_code == 200
    assert file_response.content == b"fake mp4 bytes"
