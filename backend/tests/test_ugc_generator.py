import shutil
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from app import ugc_generator as ug

FFMPEG_AVAILABLE = shutil.which("ffmpeg") and shutil.which("ffprobe")
skip_without_ffmpeg = pytest.mark.skipif(not FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe not installed here")

VALID_SCRIPT_JSON = """{
  "hook": "Stop scrolling.",
  "intro": "This is the new wireless earbuds everyone's talking about.",
  "benefits": ["30-hour battery.", "Crystal clear calls.", "Fits in your pocket."],
  "cta_line": "You need these."
}"""


def _fake_anthropic_client(response_text):
    text_block = SimpleNamespace(type="text", text=response_text)
    fake_response = SimpleNamespace(content=[text_block])
    messages = SimpleNamespace(create=lambda **kwargs: fake_response)
    return SimpleNamespace(messages=messages)


def _tiny_test_image(path: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=0x336699:s=1080x1920:d=1", "-frames:v", "1", str(path)],
        capture_output=True,
        check=True,
    )


def _tiny_test_video(path: Path) -> None:
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=c=0x224466:s=640x360:d=1",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
            str(path),
        ],
        capture_output=True,
        check=True,
    )


def test_write_ugc_script_parses_valid_json(monkeypatch):
    monkeypatch.setattr(ug, "get_client", lambda: _fake_anthropic_client(VALID_SCRIPT_JSON))
    script = ug.write_ugc_script("Make it fun", "Earbuds", "Wireless earbuds")
    assert script.hook == "Stop scrolling."
    assert len(script.benefits) == 3
    assert "Stop scrolling." in script.full_text()


def test_write_ugc_script_raises_on_invalid_json(monkeypatch):
    monkeypatch.setattr(ug, "get_client", lambda: _fake_anthropic_client("not json"))
    with pytest.raises(Exception):
        ug.write_ugc_script("prompt", "Product", "desc")


def test_write_ugc_script_raises_on_missing_fields(monkeypatch):
    monkeypatch.setattr(ug, "get_client", lambda: _fake_anthropic_client('{"hook": "only this"}'))
    with pytest.raises(Exception):
        ug.write_ugc_script("prompt", "Product", "desc")


def test_synthesize_voice_raises_without_api_key(monkeypatch):
    monkeypatch.setattr(ug, "ELEVENLABS_API_KEY", "")
    with pytest.raises(Exception):
        ug.synthesize_voice("hello", "voice123")


def test_list_voices_raises_without_api_key(monkeypatch):
    monkeypatch.setattr(ug, "ELEVENLABS_API_KEY", "")
    with pytest.raises(Exception):
        ug.list_voices()


def test_list_presenters_raises_without_api_key(monkeypatch):
    monkeypatch.setattr(ug, "D_ID_API_KEY", "")
    with pytest.raises(Exception):
        ug.list_presenters()


@skip_without_ffmpeg
def test_generate_ugc_ad_produces_a_real_mp4(tmp_path, monkeypatch):
    monkeypatch.setattr(ug, "VIDEO_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setattr(
        ug,
        "write_ugc_script",
        lambda prompt, name, desc: ug.UGCScript(
            hook="Hook.", intro="Intro.", benefits=["A.", "B.", "C."], cta_line="Go now."
        ),
    )
    monkeypatch.setattr(ug, "synthesize_voice", lambda text, voice_id: b"fake-mp3-bytes")
    monkeypatch.setattr(ug, "_upload_audio_to_did", lambda audio_bytes: "https://example.com/audio.mp3")
    monkeypatch.setattr(ug, "_create_talk_clip", lambda presenter_id, audio_url: "clip123")
    monkeypatch.setattr(ug, "_wait_for_clip", lambda clip_id: "https://example.com/result.mp4")

    def fake_download(url, dest_path):
        _tiny_test_video(dest_path)

    monkeypatch.setattr(ug, "_download", fake_download)

    image = tmp_path / "product.jpg"
    _tiny_test_image(image)
    workdir = Path(tempfile.mkdtemp(dir=tmp_path))

    result = ug.generate_ugc_ad(
        prompt="Make it fun",
        product_name="Earbuds",
        product_description="Wireless earbuds",
        presenter_id="presenter123",
        voice_id="voice123",
        cta_text="Buy Now",
        product_image_paths=[image],
        workdir=workdir,
    )

    assert result.file_path.exists()
    assert result.file_path.suffix == ".mp4"
    assert result.script.hook == "Hook."

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(result.file_path)],
        capture_output=True,
        text=True,
    )
    stream_types = probe.stdout.split()
    assert "video" in stream_types
    assert "audio" in stream_types
