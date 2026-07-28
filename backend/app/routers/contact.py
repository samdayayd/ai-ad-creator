from collections import defaultdict
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request

from app.contact import send_contact_email
from app.schemas import ContactRequest

router = APIRouter(prefix="/api/contact", tags=["contact"])

MAX_SUBMISSIONS_PER_WINDOW = 5
WINDOW_MINUTES = 60
# Same in-memory-per-instance tradeoff as the login/signup rate limiters —
# not a global guarantee across multiple Cloud Run instances, but a real
# deterrent against a public, unauthenticated endpoint being used to spam
# the owner's inbox.
_submissions: dict[str, list[datetime]] = defaultdict(list)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("")
def contact(body: ContactRequest, request: Request):
    """Public — no login required, since someone stuck on a broken feature
    might not be able to sign in at all. Rate-limited per IP instead."""
    ip = _client_ip(request)
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=WINDOW_MINUTES)
    recent = [t for t in _submissions[ip] if t > window_start]
    _submissions[ip] = recent
    if len(recent) >= MAX_SUBMISSIONS_PER_WINDOW:
        raise HTTPException(status_code=429, detail="Too many messages sent. Try again later.")

    name = body.name.strip()
    email = body.email.strip()
    message = body.message.strip()
    if not name or not email or not message:
        raise HTTPException(status_code=400, detail="Name, email, and message are all required.")

    send_contact_email(name, email, message)
    _submissions[ip].append(now)
    return {"sent": True}
