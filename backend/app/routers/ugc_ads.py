import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import UGC_CTA_OPTIONS
from app.db import User, UGCGeneration, get_session
from app.quota import consume_video_quota, ensure_video_quota_available
from app.schemas import (
    PresenterOut,
    UGCAdOut,
    UGCGenerationOut,
    UGCScriptOut,
    UGCScriptRequest,
    VoiceOut,
)
from app.ugc_generator import UGCScript, generate_ugc_ad, list_presenters, list_voices, write_ugc_script

router = APIRouter(prefix="/api/ugc-ads", tags=["ugc-ads"])

ALLOWED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGES = 2  # only used as short product cutaways between/after the presenter clip


@router.get("/presenters", response_model=list[PresenterOut])
def presenters(user: User = Depends(get_current_user)):
    """D-ID's own pre-licensed stock presenters — never a face you'd have to
    source and clear usage rights for yourself. Fetched live rather than
    hardcoded, since D-ID's available presenter catalog can change."""
    raw = list_presenters()
    return [
        PresenterOut(
            id=p.get("presenter_id", p.get("id", "")),
            name=p.get("name", "Presenter"),
            gender=p.get("gender"),
            thumbnail_url=p.get("thumbnail_url") or p.get("preview_url"),
        )
        for p in raw
    ]


@router.get("/voices", response_model=list[VoiceOut])
def voices(user: User = Depends(get_current_user)):
    """The ElevenLabs voices available on this account, fetched live rather
    than hardcoded since voice IDs are account-specific (default premade
    voices plus anything cloned/added)."""
    raw = list_voices()
    return [
        VoiceOut(
            id=v["voice_id"],
            name=v.get("name", "Voice"),
            preview_url=v.get("preview_url"),
        )
        for v in raw
    ]


@router.get("/cta-options")
def cta_options():
    return list(UGC_CTA_OPTIONS)


@router.post("/script", response_model=UGCScriptOut)
def create_ugc_script(body: UGCScriptRequest, user: User = Depends(get_current_user)):
    """Writes the script only — no rendering, no ElevenLabs/D-ID calls, no
    quota spent. Lets the UI show an editable draft before committing to
    the expensive render step. Still requires login: it spends a real
    Anthropic API call, so it can't be left open to anonymous callers."""
    script = write_ugc_script(body.prompt, body.product_name, body.product_description)
    return UGCScriptOut(hook=script.hook, intro=script.intro, benefits=script.benefits, cta_line=script.cta_line)


@router.post("/create", response_model=UGCAdOut)
async def create_ugc_ad(
    prompt: str = Form(...),
    product_name: str = Form(...),
    product_description: str = Form(""),
    presenter_id: str = Form(...),
    presenter_name: str = Form(...),
    voice_id: str = Form(...),
    voice_name: str = Form(...),
    cta_text: str = Form(...),
    script_hook: str | None = Form(default=None),
    script_intro: str | None = Form(default=None),
    script_benefits: list[str] | None = Form(default=None),
    script_cta_line: str | None = Form(default=None),
    images: list[UploadFile] = File(default=[]),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """One sentence + a product + a presenter/voice/CTA choice → a real MP4:
    Claude writes the talking script (or pass your own edited script_* fields
    from POST .../script to skip that call), ElevenLabs voices it, D-ID
    animates a pre-licensed stock presenter speaking it, and ffmpeg cuts in
    short product-photo cutaways plus a CTA card at the end. See
    ugc_generator.py for why this is a presenter + cutaways edit and not a
    presenter that literally holds your product — no API sells that today.
    Counts against the caller's plan quota; free-plan renders are
    watermarked."""
    if cta_text not in UGC_CTA_OPTIONS:
        raise HTTPException(status_code=400, detail=f"cta_text must be one of: {', '.join(UGC_CTA_OPTIONS)}")
    if len(images) > MAX_IMAGES:
        raise HTTPException(status_code=400, detail=f"Upload at most {MAX_IMAGES} product images.")

    script = None
    if script_hook and script_intro and script_benefits and script_cta_line:
        script = UGCScript(hook=script_hook, intro=script_intro, benefits=script_benefits, cta_line=script_cta_line)

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

        result = generate_ugc_ad(
            prompt=prompt,
            product_name=product_name,
            product_description=product_description,
            presenter_id=presenter_id,
            voice_id=voice_id,
            cta_text=cta_text,
            product_image_paths=image_paths,
            workdir=workdir,
            script=script,
            watermark=(user.plan == "free"),
        )
        consume_video_quota(user, session)

        script_json = {
            "hook": result.script.hook,
            "intro": result.script.intro,
            "benefits": result.script.benefits,
            "cta_line": result.script.cta_line,
        }
        row = UGCGeneration(
            user_id=user.id,
            product_title=product_name,
            presenter_name=presenter_name,
            voice_name=voice_name,
            cta_text=cta_text,
            file_path=str(result.file_path),
            script_json=script_json,
        )
        session.add(row)
        session.commit()
        session.refresh(row)

        return UGCAdOut(
            id=row.id,
            product_title=row.product_title,
            presenter_name=row.presenter_name,
            voice_name=row.voice_name,
            cta_text=row.cta_text,
            script=UGCScriptOut(**script_json),
            video_url=f"/api/ugc-ads/{row.id}/file",
        )


@router.get("/history", response_model=list[UGCGenerationOut])
def ugc_history(session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    rows = (
        session.query(UGCGeneration)
        .filter(UGCGeneration.user_id == user.id)
        .order_by(UGCGeneration.created_at.desc())
        .all()
    )
    return [
        UGCGenerationOut(
            id=r.id,
            product_title=r.product_title,
            presenter_name=r.presenter_name,
            voice_name=r.voice_name,
            cta_text=r.cta_text,
            script=UGCScriptOut(**r.script_json),
            video_url=f"/api/ugc-ads/{r.id}/file",
            created_at=r.created_at,
        )
        for r in rows
    ]


@router.get("/{ugc_id}/file")
def ugc_file(ugc_id: int, session: Session = Depends(get_session), user: User = Depends(get_current_user)):
    row = session.get(UGCGeneration, ugc_id)
    if not row or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Video not found.")
    if not Path(row.file_path).exists():
        raise HTTPException(status_code=410, detail="This video file is no longer available on disk.")
    return FileResponse(row.file_path, media_type="video/mp4")
