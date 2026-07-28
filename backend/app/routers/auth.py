from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.auth import create_access_token, verify_password
from app.db import User, get_session
from app.schemas import LoginRequest, LoginResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_MINUTES = 15
# In-memory per-instance only — Cloud Run can run more than one instance, so
# this doesn't guarantee a global lockout, but it's a real deterrent for a
# single-owner login sitting on the open internet (--allow-unauthenticated),
# raised well above what's worth the extra complexity of a shared store
# (Redis, etc.) for a personal tool.
_failed_attempts: dict[str, list[datetime]] = defaultdict(list)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


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

    user = session.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        _failed_attempts[ip].append(now)
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    _failed_attempts.pop(ip, None)
    return LoginResponse(access_token=create_access_token(user.id))
