from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.db import User, get_session
from app.quota import remaining_ugc_videos, remaining_videos
from app.schemas import LoginRequest, LoginResponse, MeOut, SignupRequest

router = APIRouter(prefix="/api/auth", tags=["auth"])

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_MINUTES = 15
MIN_PASSWORD_LENGTH = 8
MAX_SIGNUPS_PER_WINDOW = 5
SIGNUP_WINDOW_MINUTES = 60
# In-memory per-instance only — Cloud Run can run more than one instance, so
# this doesn't guarantee a global limit, but it's a real deterrent now that
# this is a public multi-account product rather than a single-owner tool:
# unprotected login invites brute-forcing, and unprotected signup invites
# scripted mass account creation to farm the free plan's video quota.
_failed_attempts: dict[str, list[datetime]] = defaultdict(list)
_signup_attempts: dict[str, list[datetime]] = defaultdict(list)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/signup", response_model=LoginResponse)
def signup(body: SignupRequest, request: Request, session: Session = Depends(get_session)):
    ip = _client_ip(request)
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=SIGNUP_WINDOW_MINUTES)
    recent = [t for t in _signup_attempts[ip] if t > window_start]
    _signup_attempts[ip] = recent
    if len(recent) >= MAX_SIGNUPS_PER_WINDOW:
        raise HTTPException(status_code=429, detail="Too many accounts created from this network. Try again later.")

    email = body.email.strip().lower()
    if len(body.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(status_code=400, detail=f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if session.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="An account with that email already exists.")

    _signup_attempts[ip].append(now)
    user = User(email=email, hashed_password=hash_password(body.password), plan="free")
    session.add(user)
    session.commit()
    session.refresh(user)
    return LoginResponse(access_token=create_access_token(user.id))


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, request: Request, session: Session = Depends(get_session)):
    ip = _client_ip(request)
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=LOCKOUT_WINDOW_MINUTES)
    recent_failures = [t for t in _failed_attempts[ip] if t > window_start]
    _failed_attempts[ip] = recent_failures
    if len(recent_failures) >= MAX_FAILED_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail=f"Too many failed login attempts. Try again in {LOCKOUT_WINDOW_MINUTES} minutes.",
        )

    user = session.query(User).filter(User.email == body.email.strip().lower()).first()
    if not user or not verify_password(body.password, user.hashed_password):
        _failed_attempts[ip].append(now)
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    _failed_attempts.pop(ip, None)
    return LoginResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user)):
    return MeOut(
        email=user.email,
        plan=user.plan,
        videos_used=user.videos_used,
        videos_remaining=remaining_videos(user),
        ugc_videos_used=user.ugc_videos_used,
        ugc_videos_remaining=remaining_ugc_videos(user),
    )
