"""Generates a talking-presenter UGC-style ad: Claude writes the script,
ElevenLabs voices it, D-ID animates one of its own pre-licensed stock
presenters speaking that audio, and ffmpeg edits the result together with
short Ken-Burns cutaways of your uploaded product photos and a text card for
the call to action.

Why "presenter + product cutaways" and not a presenter that actually holds
or uses your product: no commercial API — D-ID, HeyGen, and Synthesia
included — generates a photorealistic person physically interacting with an
arbitrary uploaded object today. That capability doesn't exist yet at any
price. What real UGC-ad tools do under the hood is exactly this: a talking
avatar shot edited together with separate product shots, the way a real ad
would be cut. This module does the same, honestly, instead of pretending to
offer something nobody actually sells.

Two paid third-party accounts, both separate from ANTHROPIC_API_KEY:
- ELEVENLABS_API_KEY (elevenlabs.io) — real neural voice synthesis.
- D_ID_API_KEY (studio.d-id.com) — presenter animation, using D-ID's own
  pre-licensed stock actors (their "Clips" presenters) — never a face image
  you'd have to source and clear usage rights for yourself.

Both APIs are called here from documented shapes, not verified against a
live account (this repo doesn't hold API keys for either service). Expect
the first real run to need small field-name fixes once you plug in real
keys, the same way the Cloud Run deploy needed a few IAM permission fixes
before it worked — that's normal for a fresh third-party integration, not a
sign something is fundamentally wrong.
"""

import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import anthropic
import httpx
from fastapi import HTTPException

from app.config import ANTHROPIC_MODEL, D_ID_API_KEY, ELEVENLABS_API_KEY, VIDEO_STORAGE_DIR
from app.llm import extract_json, get_client
from app.video_generator import FONT_PATH, FPS, VIDEO_HEIGHT, VIDEO_WIDTH, apply_watermark

D_ID_BASE_URL = "https://api.d-id.com"
ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"
D_ID_POLL_INTERVAL_SECONDS = 3
D_ID_POLL_TIMEOUT_SECONDS = 180
PRODUCT_CUTAWAY_SECONDS = 2.5
CTA_CARD_SECONDS = 2.5

SYSTEM_PROMPT = """You are a scriptwriter for short UGC-style talking-presenter \
video ads (the kind a real person films for TikTok/Instagram, not a formal \
commercial). Given product info and a one-line creative brief, write a script \
for a single presenter to speak straight to camera.

Respond with ONLY a single JSON object (no markdown fences, no commentary):
{"hook": string, "intro": string, "benefits": [string, string, string], "cta_line": string}

Rules:
- hook: one attention-grabbing spoken line, under 12 words, said in the first \
2 seconds.
- intro: 1-2 spoken sentences introducing the product naturally, like a real \
person talking to a friend, not an ad voiceover.
- benefits: exactly 3 short spoken lines, each one clear benefit, conversational.
- cta_line: one closing spoken line that naturally leads into a call to action \
(the exact CTA button text is added separately as an on-screen card — don't \
restate it verbatim).
- Base every claim only on the product info given. Never invent specs, \
prices, or guarantees that weren't provided.
- Write everything to be spoken aloud — no stage directions, no emojis.
"""


@dataclass
class UGCScript:
    hook: str
    intro: str
    benefits: list[str]
    cta_line: str

    def full_text(self) -> str:
        return " ".join([self.hook, self.intro, *self.benefits, self.cta_line])


@dataclass
class UGCAdResult:
    file_path: Path
    script: UGCScript


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Video rendering step failed: {result.stderr[-500:]}")


def write_ugc_script(prompt: str, product_name: str, product_description: str) -> UGCScript:
    client = get_client()
    user_message = (
        f"Creative brief: {prompt}\n"
        f"Product: {product_name}\n"
        f"Description: {product_description or '(none provided)'}\n"
    )
    try:
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
    except anthropic.APIError as exc:
        raise HTTPException(status_code=502, detail=f"Script generation failed: {exc}") from exc

    text = "".join(block.text for block in response.content if block.type == "text")
    data = extract_json(text)
    try:
        return UGCScript(
            hook=data["hook"],
            intro=data["intro"],
            benefits=list(data["benefits"]),
            cta_line=data["cta_line"],
        )
    except (KeyError, TypeError) as exc:
        raise HTTPException(status_code=502, detail="The AI didn't return a usable script — try again.") from exc


def _elevenlabs_headers() -> dict:
    if not ELEVENLABS_API_KEY:
        raise HTTPException(
            status_code=503,
            detail=(
                "This needs an ElevenLabs API key for real voice generation. Set "
                "ELEVENLABS_API_KEY in the backend environment (get one at "
                "elevenlabs.io) — a paid account, separate from your Anthropic key."
            ),
        )
    return {"xi-api-key": ELEVENLABS_API_KEY}


def list_voices() -> list[dict]:
    with httpx.Client(timeout=30) as client:
        resp = client.get(f"{ELEVENLABS_BASE_URL}/voices", headers=_elevenlabs_headers())
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Couldn't fetch voices from ElevenLabs: {resp.text[:300]}")
    return resp.json().get("voices", [])


def synthesize_voice(text: str, voice_id: str) -> bytes:
    with httpx.Client(timeout=60) as client:
        resp = client.post(
            f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}",
            headers={**_elevenlabs_headers(), "Content-Type": "application/json"},
            json={"text": text, "model_id": "eleven_multilingual_v2"},
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Voice generation failed: {resp.text[:300]}")
    return resp.content


def _d_id_auth() -> tuple[str, str]:
    if not D_ID_API_KEY:
        raise HTTPException(
            status_code=503,
            detail=(
                "This needs a D-ID API key for the talking presenter. Set "
                "D_ID_API_KEY in the backend environment (get one at "
                "studio.d-id.com) — a paid account, separate from your Anthropic key."
            ),
        )
    return (D_ID_API_KEY, "")


def list_presenters() -> list[dict]:
    with httpx.Client(timeout=30) as client:
        resp = client.get(f"{D_ID_BASE_URL}/clips/presenters", auth=_d_id_auth())
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Couldn't fetch presenters from D-ID: {resp.text[:300]}")
    return resp.json().get("presenters", [])


def _upload_audio_to_did(audio_bytes: bytes) -> str:
    with httpx.Client(timeout=60) as client:
        resp = client.post(
            f"{D_ID_BASE_URL}/audios",
            auth=_d_id_auth(),
            files={"audio": ("voice.mp3", audio_bytes, "audio/mpeg")},
        )
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail=f"Couldn't upload audio to D-ID: {resp.text[:300]}")
    return resp.json()["url"]


def _create_talk_clip(presenter_id: str, audio_url: str) -> str:
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{D_ID_BASE_URL}/clips",
            auth=_d_id_auth(),
            json={"presenter_id": presenter_id, "script": {"type": "audio", "audio_url": audio_url}},
        )
    if resp.status_code not in (200, 201):
        raise HTTPException(status_code=502, detail=f"D-ID couldn't start the presenter video: {resp.text[:300]}")
    return resp.json()["id"]


def _wait_for_clip(clip_id: str) -> str:
    deadline = time.monotonic() + D_ID_POLL_TIMEOUT_SECONDS
    with httpx.Client(timeout=30) as client:
        while time.monotonic() < deadline:
            resp = client.get(f"{D_ID_BASE_URL}/clips/{clip_id}", auth=_d_id_auth())
            if resp.status_code != 200:
                raise HTTPException(
                    status_code=502, detail=f"Couldn't check presenter video status: {resp.text[:300]}"
                )
            data = resp.json()
            status = data.get("status")
            if status == "done":
                result_url = data.get("result_url")
                if not result_url:
                    raise HTTPException(
                        status_code=502,
                        detail=f"D-ID marked the video done but returned no result_url. Raw response: {data}",
                    )
                return result_url
            if status == "error":
                raise HTTPException(
                    status_code=502, detail=f"D-ID failed to render the presenter video: {data.get('error')}"
                )
            time.sleep(D_ID_POLL_INTERVAL_SECONDS)
    raise HTTPException(status_code=504, detail="The presenter video took too long to render — try again.")


def _download(url: str, dest_path: Path) -> None:
    with httpx.Client(timeout=60) as client:
        resp = client.get(url)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail="Couldn't download the rendered presenter video.")
    dest_path.write_bytes(resp.content)


def _render_cta_card(cta_text: str, duration: float, out_path: Path) -> None:
    escaped = cta_text.replace("'", "")
    vf = (
        f"drawtext=fontfile={FONT_PATH}:text='{escaped}':fontcolor=white:fontsize=90:"
        f"x=(w-text_w)/2:y=(h-text_h)/2"
    )
    _run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"color=c=0x111111:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:d={duration}",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-vf", vf,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-shortest", "-t", str(duration),
            str(out_path),
            "-loglevel", "error",
        ]
    )


def _render_product_cutaway(image_path: Path, duration: float, out_path: Path) -> None:
    frames = max(1, round(duration * FPS))
    vf = (
        f"scale={VIDEO_WIDTH * 2}:-1,"
        f"zoompan=z='min(zoom+0.002,1.3)':d={frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={FPS}"
    )
    _run(
        [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(image_path),
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-vf", vf,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-shortest", "-t", str(duration),
            str(out_path),
            "-loglevel", "error",
        ]
    )


def _normalize_presenter_clip(presenter_path: Path, out_path: Path) -> None:
    """D-ID renders at whatever resolution/codec it uses internally — the
    concat demuxer below needs every clip on matching codec/dimensions, so
    this re-encodes to the same vertical frame the cutaways and CTA card
    use, letterboxing rather than cropping so nothing of the presenter is
    cut off."""
    vf = (
        f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,"
        f"pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2"
    )
    _run(
        [
            "ffmpeg", "-y",
            "-i", str(presenter_path),
            "-vf", vf,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac",
            str(out_path),
            "-loglevel", "error",
        ]
    )


def generate_ugc_ad(
    prompt: str,
    product_name: str,
    product_description: str,
    presenter_id: str,
    voice_id: str,
    cta_text: str,
    product_image_paths: list[Path],
    workdir: Path,
    script: UGCScript | None = None,
    watermark: bool = False,
) -> UGCAdResult:
    if script is None:
        script = write_ugc_script(prompt, product_name, product_description)
    audio_bytes = synthesize_voice(script.full_text(), voice_id)
    audio_url = _upload_audio_to_did(audio_bytes)
    clip_id = _create_talk_clip(presenter_id, audio_url)
    result_url = _wait_for_clip(clip_id)

    presenter_raw_path = workdir / "presenter_raw.mp4"
    _download(result_url, presenter_raw_path)
    presenter_path = workdir / "presenter.mp4"
    _normalize_presenter_clip(presenter_raw_path, presenter_path)

    parts = [presenter_path]
    for i, image_path in enumerate(product_image_paths[:2]):
        cutaway_path = workdir / f"cutaway_{i}.mp4"
        _render_product_cutaway(image_path, PRODUCT_CUTAWAY_SECONDS, cutaway_path)
        parts.append(cutaway_path)

    cta_path = workdir / "cta.mp4"
    _render_cta_card(cta_text, CTA_CARD_SECONDS, cta_path)
    parts.append(cta_path)

    list_file = workdir / "concat.txt"
    list_file.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    concatenated_path = workdir / "concatenated.mp4"
    _run(
        [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
            str(concatenated_path),
            "-loglevel", "error",
        ]
    )

    final_path = concatenated_path
    if watermark:
        watermarked_path = workdir / "watermarked.mp4"
        apply_watermark(final_path, watermarked_path)
        final_path = watermarked_path

    storage_dir = Path(VIDEO_STORAGE_DIR)
    storage_dir.mkdir(parents=True, exist_ok=True)
    dest_path = storage_dir / f"{uuid.uuid4().hex}.mp4"
    final_path.replace(dest_path)

    return UGCAdResult(file_path=dest_path, script=script)
