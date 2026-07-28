"""Plan/quota logic shared by the video-ads and UGC-ads routers. Text ads
aren't gated here — see README for why that's a deliberate, flagged
tradeoff rather than an oversight."""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import OWNER_PLAN, PLAN_LIMITS
from app.db import User

PAID_PLANS = ("pro", "max")
ROLLOVER_FALLBACK_DAYS = 30


def _limit_for(plan: str) -> int | None:
    """None means unlimited (the owner account)."""
    if plan == OWNER_PLAN:
        return None
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])


def _maybe_roll_over(user: User, now: datetime) -> None:
    """Paid plans reset their counter roughly monthly; free's cap is a
    lifetime total by design (it's a "try it" tier, not a recurring
    allowance), so it never rolls over. The real reset trigger is the
    Stripe webhook's invoice.paid event on each actual renewal — this is
    only a fallback in case a webhook was ever missed, so someone's not
    stuck locked out forever over an infra hiccup."""
    if user.plan in PAID_PLANS:
        period_start = user.usage_period_start
        # SQLite (used for local dev/tests) doesn't round-trip tzinfo through
        # a DateTime column even with timezone=True, so a value written as
        # UTC-aware can come back naive — comparing that directly against
        # `now` (always UTC-aware) raises TypeError. Every write in this
        # codebase uses UTC, so a naive read is always UTC; treat it as such.
        if period_start and period_start.tzinfo is None:
            period_start = period_start.replace(tzinfo=timezone.utc)
        if not period_start or now >= period_start + timedelta(days=ROLLOVER_FALLBACK_DAYS):
            user.videos_used = 0
            user.usage_period_start = now


def remaining_videos(user: User) -> int | None:
    """None means unlimited. Read-only — does not roll over or mutate."""
    limit = _limit_for(user.plan)
    if limit is None:
        return None
    return max(0, limit - user.videos_used)


def ensure_video_quota_available(user: User, session: Session) -> None:
    """Call BEFORE starting a render — rejects up front so an
    already-over-quota request never spends a real TTS/D-ID/ffmpeg call
    that would just get discarded. Persists any rollover so the check and
    the later consume() agree on the same period."""
    now = datetime.now(timezone.utc)
    _maybe_roll_over(user, now)
    session.add(user)
    session.commit()

    limit = _limit_for(user.plan)
    if limit is not None and user.videos_used >= limit:
        period = "this month" if user.plan in PAID_PLANS else "in total"
        raise HTTPException(
            status_code=402,
            detail=(
                f"You've used all {limit} videos on your {user.plan} plan {period}. "
                "Upgrade at /pricing to keep creating."
            ),
        )


def consume_video_quota(user: User, session: Session) -> None:
    """Call AFTER a render actually succeeds — a failed render shouldn't
    cost the user a unit of their plan."""
    user.videos_used += 1
    session.add(user)
    session.commit()
