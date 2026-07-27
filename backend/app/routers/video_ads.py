import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import ALLOWED_VIDEO_DURATIONS
from app.db import User, VideoGeneration, get_session
from app.schemas import VideoAdOut, VideoGenerationOut, VideoSceneOut
from app.video_generator import generate_video_ad

router = APIRouter(prefix="/api/video-ads", tags=["video-ads"])

ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGES = 8


def _scenes_out(scenes_json: list[dict]) -> list[VideoSceneOut]:
    return [VideoSceneOut(**s) for s in scenes_json]


@router.post("/create", response_model=VideoAdOut)
async def create_video_ad(
    product_name: str = Form(...),
    product_description: str = Form(""),
    duration_seconds: int = Form(...),
    images: list[UploadFile] = File(default=[]),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Upload product photos, pick a target length, get a real MP4 video ad
    back — script written by Claude, voiced by a local TTS engine, product
    images panned/zoomed across with the script as captions, a generated
    background tone mixed in underneath. See video_generator.py for exactly
    what "AI video ad" means here versus a full photorealistic AI-video
    generator (which this deliberately isn't — see that module's docstring)."""
    if duration_seconds not in ALLOWED_VIDEO_DURATIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Duration must be one of: {', '.join(str(d) for d in ALLOWED_VIDEO_DURATIONS)} seconds.",
        )
    if not images:
        raise HTTPException(status_code=400, detail="Upload at least one product image.")
    if len(images) > MAX_IMAGES:
        raise HTTPException(status_code=400, detail=f"Upload at most {MAX_IMAGES} images.")

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

        result = generate_video_ad(product_name, product_description, duration_seconds, image_paths, workdir)

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
