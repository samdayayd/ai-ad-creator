import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import ALLOWED_VIDEO_DURATIONS
from app.db import User, VideoGeneration, get_session
from app.quota import consume_video_quota, ensure_video_quota_available
from app.schemas import VideoAdOut, VideoGenerationOut, VideoSceneOut, VideoScriptOut, VideoScriptRequest
from app.video_generator import generate_video_ad, scene_count_for_duration, write_video_script

router = APIRouter(prefix="/api/video-ads", tags=["video-ads"])

ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGES = 8


def _scenes_out(scenes_json: list[dict]) -> list[VideoSceneOut]:
    return [VideoSceneOut(**s) for s in scenes_json]


@router.post("/script", response_model=VideoScriptOut)
def create_video_script(body: VideoScriptRequest, user: User = Depends(get_current_user)):
    """Writes the script only — no rendering, no quota spent. Lets the UI
    show an editable draft before committing to the expensive render step.
    Still requires login: it's ungated by plan quota, but it still spends a
    real Anthropic API call, so it can't be left open to anonymous callers."""
    if body.duration_seconds not in ALLOWED_VIDEO_DURATIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Duration must be one of: {', '.join(str(d) for d in ALLOWED_VIDEO_DURATIONS)} seconds.",
        )
    scenes = write_video_script(
        body.product_name, body.product_description, scene_count_for_duration(body.duration_seconds)
    )
    return VideoScriptOut(scenes=scenes)


@router.post("/create", response_model=VideoAdOut)
async def create_video_ad(
    product_name: str = Form(...),
    product_description: str = Form(""),
    duration_seconds: int = Form(...),
    script: list[str] | None = Form(default=None),
    images: list[UploadFile] = File(default=[]),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Upload product photos, pick a target length, get a real MP4 video ad
    back — script written by Claude (or pass your own edited `script` lines
    from POST .../script to skip that call), voiced by a local TTS engine,
    product images panned/zoomed across with the script as captions, a
    generated background tone mixed in underneath. See video_generator.py
    for exactly what "AI video ad" means here versus a full photorealistic
    AI-video generator (which this deliberately isn't — see that module's
    docstring). Counts against the caller's plan quota; free-plan renders
    are watermarked."""
    if duration_seconds not in ALLOWED_VIDEO_DURATIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Duration must be one of: {', '.join(str(d) for d in ALLOWED_VIDEO_DURATIONS)} seconds.",
        )
    if not images:
        raise HTTPException(status_code=400, detail="Upload at least one product image.")
    if len(images) > MAX_IMAGES:
        raise HTTPException(status_code=400, detail=f"Upload at most {MAX_IMAGES} images.")

    ensure_video_quota_available(user, session)

    with tempfile.TemporaryDirectory() as tmpdir:
        workdir = Path(tmpdir)
        image_paths = []
        for i, upload in enumerate(images):
            suffix = Path(upload.filename or "").suffix.lower()
            if suffix not in ALLOWED_IMAGE_SUFFIXES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported image type: {upload.filename}. Use JPG, PNG, or WEBP.",
                )
            image_path = workdir / f"upload_{i}{suffix}"
            image_path.write_bytes(await upload.read())
            image_paths.append(image_path)

        result = generate_video_ad(
            product_name,
            product_description,
            duration_seconds,
            image_paths,
            workdir,
            script_lines=script,
            watermark=(user.plan == "free"),
        )
        consume_video_quota(user, session)

        scenes_json = [{"text": s.text, "duration": s.duration} for s in result.scenes]
        row = VideoGeneration(
            user_id=user.id,
            product_title=product_name,
            requested_duration_seconds=duration_seconds,
            actual_duration_seconds=result.actual_duration_seconds,
            file_path=str(result.file_path),
            scenes_json=scenes_json,
        )
        session.add(row)
        session.commit()
        session.refresh(row)

        return VideoAdOut(
            id=row.id,
            product_title=row.product_title,
            requested_duration_seconds=row.requested_duration_seconds,
            actual_duration_seconds=row.actual_duration_seconds,
            scenes=_scenes_out(scenes_json),
            video_url=f"/api/video-ads/{row.id}/file",
        )


@router.get("/history", response_model=list[VideoGenerationOut])
def video_history(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    rows = (
        session.query(VideoGeneration)
        .filter(VideoGeneration.user_id == user.id)
        .order_by(VideoGeneration.created_at.desc())
        .all()
    )
    return [
        VideoGenerationOut(
            id=r.id,
            product_title=r.product_title,
            requested_duration_seconds=r.requested_duration_seconds,
            actual_duration_seconds=r.actual_duration_seconds,
            scenes=_scenes_out(r.scenes_json),
            video_url=f"/api/video-ads/{r.id}/file",
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/{video_id}/file")
def video_file(video_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    row = session.get(VideoGeneration, video_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Video not found.")
    if not Path(row.file_path).exists():
        raise HTTPException(status_code=410, detail="This video file is no longer available on disk.")
    return FileResponse(row.file_path, media_type="video/mp4")
