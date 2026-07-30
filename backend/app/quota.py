"""Plan/quota logic shared by the video-ads and UGC-ads routers. Text ads
aren't gated here — see README for why that's a deliberate, flagged
tradeoff rather than an oversight.

Two ceilings, not one: every plan has an overall video quota (PLAN_LIMITS)
plus a tighter UGC-specific sub-quota (UGC_PLAN_LIMITS), since a UGC ad
costs meaningfully more than a Ken-Burns video ad (ElevenLabs + D-ID on
top of the Claude call every video already makes) and, left uncapped
separately, could let a plan's entire quota be spent on the expensive
path. A UGC ad counts against both counters; a Ken-Burns video ad counts
against only the general one."""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import OWNER_PLAN, PLAN_LIMITS, UGC_PLAN_LIMITS
from app.db import User

PAID_PLANS = ("pro", "max")
ROLLOVER_FALLBACK_DAYS = 30


def _limit_for(plan: str, limits: dict[str, int]) -> int | None:
    """None means unlimited (the owner account)."""
    if plan == OWNER_PLAN:
        return None
    return limits.get(plan, limits["free"])


def _maybe_roll_over(user: User, now: datetime) -> None:
    """Paid plans reset both counters roughly monthly, together — they
    share one billing period. Free's cap is a lifetime total by design
    (it's a "try it" tier, not a recurring allowance), so it never rolls
    over. The real reset trigger is the Stripe webhook's invoice.paid
    event on each actual renewal — this is only a fallback in case a
    webhook was ever missed, so someone's not stuck locked out forever
    over an infra hiccup."""
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
            user.ugc_videos_used = 0
            user.usage_period_start = now


def remaining_videos(user: User) -> int | None:
    """None means unlimited. Read-only — does not roll over or mutate."""
    limit = _limit_for(user.plan, PLAN_LIMITS)
    if limit is None:
        return None
    return max(0, limit - user.videos_used)


def remaining_ugc_videos(user: User) -> int | None:
    """None means unlimited. Read-only — does not roll over or mutate."""
    limit = _limit_for(user.plan, UGC_PLAN_LIMITS)
    if limit is None:
        return None
    return max(0, limit - user.ugc_videos_used)


def ensure_video_quota_available(user: User, session: Session) -> None:
    """Call BEFORE starting a render — rejects up front so an
    already-over-quota request never spends a real TTS/D-ID/ffmpeg call
    that would just get discarded. Persists any rollover so the check and
    the later consume() agree on the same period.

    A plan's monthly/lifetime allowance is checked first; only once that's
    exhausted do purchased_video_credits (see config.CREDIT_PACKS) come
    into play — a paid top-up shouldn't let someone skip ahead of their
    own already-included videos."""
    now = datetime.now(timezone.utc)
    _maybe_roll_over(user, now)
    session.add(user)
    session.commit()

    limit = _limit_for(user.plan, PLAN_LIMITS)
    if limit is not None and user.videos_used >= limit and user.purchased_video_credits <= 0:
        period = "this month" if user.plan in PAID_PLANS else "in total"
        raise HTTPException(
            status_code=402,
            detail=(
                f"You've used all {limit} videos on your {user.plan} plan {period}. "
                "Upgrade at /pricing or buy extra videos to keep creating."
            ),
        )


def ensure_ugc_quota_available(user: User, session: Session) -> None:
    """Call BEFORE starting a UGC render, in addition to (not instead of)
    ensure_video_quota_available — UGC ads are subject to both ceilings,
    unless a purchased UGC credit is what will actually cover this one (see
    ugc_covered_by_purchased_credit) — a purchased UGC credit is priced to
    cover its own real cost standalone and shouldn't also require the
    general quota/a purchased video credit."""
    now = datetime.now(timezone.utc)
    _maybe_roll_over(user, now)
    session.add(user)
    session.commit()

    limit = _limit_for(user.plan, UGC_PLAN_LIMITS)
    if limit is not None and user.ugc_videos_used >= limit and user.purchased_ugc_credits <= 0:
        period = "this month" if user.plan in PAID_PLANS else "in total"
        raise HTTPException(
            status_code=402,
            detail=(
                f"You've used all {limit} UGC ads on your {user.plan} plan {period}. "
                "Upgrade at /pricing, buy extra UGC videos, or use the Video Ad tab instead — "
                "it doesn't count against this limit."
            ),
        )


def ugc_covered_by_purchased_credit(user: User) -> bool:
    """True if the plan's own UGC allowance is exhausted and this UGC ad
    will therefore be paid for out of purchased_ugc_credits instead. Call
    AFTER ensure_ugc_quota_available (which handles rollover) so the
    caller — the UGC-ads router — knows whether to also check/consume the
    general video quota for this request, or skip it entirely since a
    purchased UGC credit is a standalone, already-fully-paid-for unit."""
    limit = _limit_for(user.plan, UGC_PLAN_LIMITS)
    return limit is not None and user.ugc_videos_used >= limit


def consume_video_quota(user: User, session: Session) -> None:
    """Call AFTER a render actually succeeds — a failed render shouldn't
    cost the user a unit of their plan (or a purchased credit). Draws from
    the plan allowance first, purchased credits only once that's spent —
    must mirror the same condition ensure_video_quota_available checked."""
    limit = _limit_for(user.plan, PLAN_LIMITS)
    if limit is None or user.videos_used < limit:
        user.videos_used += 1
    else:
        user.purchased_video_credits -= 1
    session.add(user)
    session.commit()


def consume_ugc_quota(user: User, session: Session) -> None:
    """Call AFTER a UGC render actually succeeds. When the plan's UGC
    allowance still has room, this also implies consume_video_quota should
    be called (a UGC ad spends one unit of both plan quotas) — when it
    doesn't (ugc_covered_by_purchased_credit was True), this alone is the
    whole cost and consume_video_quota must NOT also be called; the
    UGC-ads router decides which based on that same check."""
    limit = _limit_for(user.plan, UGC_PLAN_LIMITS)
    if limit is None or user.ugc_videos_used < limit:
        user.ugc_videos_used += 1
    else:
        user.purchased_ugc_credits -= 1
    session.add(user)
    session.commit()
