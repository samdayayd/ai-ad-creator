import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from app import video_generator as vg

FFMPEG_AVAILABLE = shutil.which("ffmpeg") and shutil.which("ffprobe") and shutil.which("espeak-ng")
skip_without_ffmpeg = pytest.mark.skipif(
    not FFMPEG_AVAILABLE, reason="ffmpeg/ffprobe/espeak-ng not installed in this environment"
)


def _tiny_test_image(path: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=0x336699:s=1080x1920:d=1", "-frames:v", "1", str(path)],
        capture_output=True,
        check=True,
    )


@skip_without_ffmpeg
def test_generate_video_ad_produces_a_real_mp4(tmp_path, monkeypatch):
    monkeypatch.setattr(vg, "VIDEO_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setattr(
        vg,
        "write_video_script",
        lambda title, desc, count: ["Short hook line for scene one.", "Buy it now, link in bio."],
    )

    image = tmp_path / "product.jpg"
    _tiny_test_image(image)

    workdir = Path(tempfile.mkdtemp(dir=tmp_path))
    result = vg.generate_video_ad("Test Product", "A test description.", 20, [image], workdir)

    assert result.file_path.exists()
    assert result.file_path.suffix == ".mp4"
    assert len(result.scenes) == 2
    assert result.actual_duration_seconds > 0

    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(result.file_path)],
        capture_output=True,
        text=True,
    )
    stream_types = probe.stdout.split()
    assert "video" in stream_types
    assert "audio" in stream_types


@skip_without_ffmpeg
def test_generate_video_ad_requires_at_least_one_image(tmp_path):
    workdir = Path(tempfile.mkdtemp(dir=tmp_path))
    with pytest.raises(Exception):
        vg.generate_video_ad("Test Product", "desc", 20, [], workdir)


@skip_without_ffmpeg
def test_generate_video_ad_cycles_through_fewer_images_than_scenes(tmp_path, monkeypatch):
    """Three scenes but only one image — the pipeline should reuse it rather
    than fail, since a real user might only upload a single product photo."""
    monkeypatch.setattr(vg, "VIDEO_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setattr(
        vg,
        "write_video_script",
        lambda title, desc, count: ["One.", "Two.", "Three."],
    )
    image = tmp_path / "product.jpg"
    _tiny_test_image(image)

    workdir = Path(tempfile.mkdtemp(dir=tmp_path))
    result = vg.generate_video_ad("Test Product", "desc", 20, [image], workdir)
    assert len(result.scenes) == 3


def test_wrap_caption_breaks_long_lines():
    wrapped = vg._wrap_caption("This is a fairly long caption that should wrap across multiple lines", width=20)
    lines = wrapped.split("\n")
    assert len(lines) > 1
    assert all(len(line) <= 25 for line in lines)  # textwrap allows slight overflow on unbreakable words
