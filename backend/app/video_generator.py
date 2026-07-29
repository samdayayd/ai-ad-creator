"""Turns product images + a short description into a real MP4 video ad:
Claude writes a scene-by-scene script, a local text-to-speech engine
(espeak-ng) voices each scene, ffmpeg pans/zooms across the product images
(a "Ken Burns" effect) with the script as animated captions, and a simple
procedurally-generated background tone bed gets mixed in underneath.

Deliberately NOT the same thing as a photorealistic AI-video generator
(Runway/Luma/Sora-style tools that synthesize footage from a text prompt) —
those cost real money per second of output and need a third-party video-gen
API this app doesn't integrate. This is a template-based video composed
from your own product images instead, which keeps the only paid step the
same one this app already had: one Claude call to write the script.
Everything after that (speech, music, rendering) runs locally via ffmpeg/
espeak-ng, so making a video costs nothing beyond that one text call.

Honest tradeoffs, by design:
- The voiceover is a free, local, synthetic voice (espeak-ng) — genuinely
  robotic-sounding compared to a paid neural TTS service. Swap in a paid
  provider later if voice quality matters more than cost.
- The "music" is a procedurally-generated ambient tone bed, not licensed
  music — there's no reliable, legal way to source real royalty-free
  tracks for free at request time.
- The video's actual length is whatever the narration naturally takes,
  not force-stretched to match the requested duration exactly (distorting
  speech speed to hit an exact number would sound worse than being
  honest that a "30-second" ad rendered in 27 seconds).
"""

import shutil
import subprocess
import textwrap
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import anthropic
from fastapi import HTTPException

from app.config import ANTHROPIC_MODEL, VIDEO_STORAGE_DIR
from app.llm import extract_json, get_client

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920  # vertical — TikTok/Reels/Stories, the platforms this is built for
FPS = 25
SECONDS_PER_SCENE = 5  # rough pacing target for the script-writing prompt only

SYSTEM_PROMPT = """You are a scriptwriter for fast-paced vertical video ads \
(TikTok / Instagram Reels style). Given product info and a target number of \
scenes, write a scene-by-scene script.

Respond with ONLY a single JSON object (no markdown fences, no commentary):
{"scenes": [{"text": string}, ...]}

Rules:
- Write exactly the requested number of scenes.
- Each scene's "text" is BOTH the spoken narration line and the on-screen \
caption for that scene — write it to be naturally speakable in about 5 \
seconds (roughly 12-16 words), punchy and conversational, not a formal ad \
read.
- Scene 1 must hook attention in the first line.
- The last scene must include a clear call to action.
- Base every claim only on the product info given. Never invent specs, \
prices, or guarantees that weren't provided.
"""


@dataclass
class VideoScene:
    text: str
    duration: float


@dataclass
class VideoAdResult:
    file_path: Path
    actual_duration_seconds: float
    scenes: list[VideoScene] = field(default_factory=list)


def _run(cmd: list[str]) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Video rendering step failed: {result.stderr[-500:]}")


def _probe_duration(path: Path) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True,
        text=True,
    )
    return float(result.stdout.strip())


def _wrap_caption(text: str, width: int = 24) -> str:
    """Manual word-wrap — drawtext never wraps text on its own, it just runs
    off the edge of the frame (confirmed the hard way with a frame grab
    during development). Written to a file and referenced via drawtext's
    textfile= option rather than embedded inline, which also sidesteps
    having to escape colons/quotes/backslashes in the script line."""
    return "\n".join(textwrap.wrap(text, width=width)) or text


def write_video_script(product_title: str, product_description: str, scene_count: int) -> list[str]:
    client = get_client()
    user_message = (
        f"Product: {product_title}\n"
        f"Description: {product_description or '(none provided)'}\n"
        f"Number of scenes: {scene_count}\n"
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
    scenes = [s["text"] for s in data.get("scenes", [])]
    if not scenes:
        raise HTTPException(status_code=502, detail="The AI didn't return a usable script — try again.")
    return scenes


def synthesize_speech(text: str, out_path: Path) -> float:
    result = subprocess.run(
        ["espeak-ng", "-v", "en", "-s", "165", "-w", str(out_path), text],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Voiceover generation failed: {result.stderr[-500:]}")
    return _probe_duration(out_path)


def generate_background_music(duration_seconds: float, out_path: Path) -> None:
    """A simple procedurally-generated ambient tone bed — three slowly
    detuning sine waves, nothing sampled or downloaded. See module docstring
    for why this isn't real licensed music."""
    expr = (
        "0.10*sin(2*PI*220*t)+0.07*sin(2*PI*330*t)"
        "+0.05*sin(2*PI*440*t*(1+0.02*sin(2*PI*0.2*t)))"
    )
    _run(
        [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", f"aevalsrc={expr}:s=44100:d={duration_seconds}",
            "-ac", "2",
            str(out_path),
            "-loglevel", "error",
        ]
    )


def render_scene(image_path: Path, caption: str, audio_path: Path, duration: float, out_path: Path) -> None:
    frames = max(1, round(duration * FPS))
    caption_path = out_path.parent / f"{out_path.stem}_caption.txt"
    caption_path.write_text(_wrap_caption(caption))
    vf = (
        f"scale={VIDEO_WIDTH * 2}:-1,"
        f"zoompan=z='min(zoom+0.0015,1.3)':d={frames}:s={VIDEO_WIDTH}x{VIDEO_HEIGHT}:fps={FPS},"
        f"drawtext=fontfile={FONT_PATH}:textfile={caption_path}:fontcolor=white:fontsize=52:"
        f"line_spacing=10:box=1:boxcolor=black@0.55:boxborderw=24:"
        f"x=(w-text_w)/2:y=h-500:text_align=C"
    )
    _run(
        [
            "ffmpeg", "-y",
            "-loop", "1", "-i", str(image_path),
            "-i", str(audio_path),
            "-vf", vf,
            "-map", "0:v", "-map", "1:a",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(FPS),
            "-c:a", "aac", "-shortest",
            str(out_path),
            "-loglevel", "error",
        ]
    )


def concat_scenes(scene_paths: list[Path], out_path: Path, workdir: Path) -> None:
    list_file = workdir / "concat.txt"
    list_file.write_text("".join(f"file '{p.resolve()}'\n" for p in scene_paths))
    _run(
        [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(list_file),
            "-c", "copy",
            str(out_path),
            "-loglevel", "error",
        ]
    )


def mix_music(video_path: Path, music_path: Path, out_path: Path) -> None:
    _run(
        [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(music_path),
            "-filter_complex",
            "[0:a]volume=1.0[a0];[1:a]volume=0.15[a1];[a0][a1]amix=inputs=2:duration=first:dropout_transition=0[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-shortest",
            str(out_path),
            "-loglevel", "error",
        ]
    )


def apply_watermark(video_path: Path, out_path: Path) -> None:
    """Burns a persistent "Made with ZeTruth Studio" mark into free-plan
    output — a final ffmpeg pass over the whole rendered video, bottom-right
    corner, applied after every other rendering step so it can't be cropped
    out by anything upstream. Paid plans skip this entirely."""
    vf = (
        "drawtext=fontfile=" + FONT_PATH + ":text='Made with ZeTruth Studio':"
        "fontcolor=white@0.85:fontsize=28:box=1:boxcolor=black@0.4:boxborderw=10:"
        "x=w-text_w-24:y=h-text_h-24"
    )
    _run(
        [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", vf,
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy",
            str(out_path),
            "-loglevel", "error",
        ]
    )


def scene_count_for_duration(duration_seconds: int) -> int:
    return max(3, round(duration_seconds / SECONDS_PER_SCENE))


def generate_video_ad(
    product_title: str,
    product_description: str,
    duration_seconds: int,
    image_paths: list[Path],
    workdir: Path,
    script_lines: list[str] | None = None,
    watermark: bool = False,
) -> VideoAdResult:
    if not image_paths:
        raise HTTPException(status_code=400, detail="At least one product image is required.")

    if script_lines is None:
        script_lines = write_video_script(product_title, product_description, scene_count_for_duration(duration_seconds))
    elif not script_lines:
        raise HTTPException(status_code=400, detail="The script can't be empty.")

    scenes: list[VideoScene] = []
    scene_video_paths: list[Path] = []
    for i, line in enumerate(script_lines):
        audio_path = workdir / f"speech_{i}.wav"
        scene_duration = synthesize_speech(line, audio_path)
        scene_duration = max(scene_duration, 1.5) + 0.3  # a little breathing room after each line

        image_path = image_paths[i % len(image_paths)]
        scene_path = workdir / f"scene_{i}.mp4"
        render_scene(image_path, line, audio_path, scene_duration, scene_path)

        scenes.append(VideoScene(text=line, duration=round(scene_duration, 2)))
        scene_video_paths.append(scene_path)

    concatenated_path = workdir / "concatenated.mp4"
    concat_scenes(scene_video_paths, concatenated_path, workdir)

    total_duration = sum(s.duration for s in scenes)
    music_path = workdir / "music.wav"
    generate_background_music(total_duration, music_path)

    final_path = workdir / "final.mp4"
    mix_music(concatenated_path, music_path, final_path)

    if watermark:
        watermarked_path = workdir / "watermarked.mp4"
        apply_watermark(final_path, watermarked_path)
        final_path = watermarked_path

    storage_dir = Path(VIDEO_STORAGE_DIR)
    storage_dir.mkdir(parents=True, exist_ok=True)
    dest_path = storage_dir / f"{uuid.uuid4().hex}.mp4"
    shutil.move(str(final_path), str(dest_path))

    actual_duration = _probe_duration(dest_path)
    return VideoAdResult(file_path=dest_path, actual_duration_seconds=round(actual_duration, 1), scenes=scenes)
