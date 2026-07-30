from datetime import datetime, timedelta, timezone

import pytest

from app import quota
from app.db import Base, SessionLocal, User, engine


@pytest.fixture()
def session():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    s = SessionLocal()
    yield s
    s.close()


def _make_user(session, plan="free", videos_used=0, ugc_videos_used=0, usage_period_start=None):
    user = User(
        email="u@example.com",
        hashed_password="x",
        plan=plan,
        videos_used=videos_used,
        ugc_videos_used=ugc_videos_used,
    )
    if usage_period_start:
        user.usage_period_start = usage_period_start
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_free_plan_lifetime_cap(session):
    user = _make_user(session, plan="free", videos_used=2)
    quota.ensure_video_quota_available(user, session)  # 3rd is still allowed
    quota.consume_video_quota(user, session)
    assert user.videos_used == 3

    with pytest.raises(Exception):
        quota.ensure_video_quota_available(user, session)  # 4th is rejected


def test_free_plan_never_rolls_over_even_after_a_long_time(session):
    long_ago = datetime.now(timezone.utc) - timedelta(days=400)
    user = _make_user(session, plan="free", videos_used=3, usage_period_start=long_ago)
    with pytest.raises(Exception):
        quota.ensure_video_quota_available(user, session)


def test_pro_plan_monthly_limit(session):
    # A real pro user always has usage_period_start set (billing.py sets it
    # together with the plan on every checkout/renewal) — set it here too,
    # otherwise _maybe_roll_over treats a missing period_start as "never
    # started a period yet" and resets the counter (see the dedicated test
    # for that fallback behavior below).
    now = datetime.now(timezone.utc)
    user = _make_user(session, plan="pro", videos_used=9, usage_period_start=now)
    quota.ensure_video_quota_available(user, session)
    quota.consume_video_quota(user, session)
    assert user.videos_used == 10

    with pytest.raises(Exception):
        quota.ensure_video_quota_available(user, session)


def test_pro_plan_rolls_over_after_fallback_window(session):
    long_ago = datetime.now(timezone.utc) - timedelta(days=31)
    user = _make_user(session, plan="pro", videos_used=10, usage_period_start=long_ago)
    quota.ensure_video_quota_available(user, session)  # should reset, not raise
    assert user.videos_used == 0


def test_paid_plan_with_no_period_start_resets_rather_than_errors(session):
    """A pro/max user should always have usage_period_start set (billing.py
    sets it alongside every plan change), but if that invariant is ever
    violated — a data-integrity edge case, not a normal path — failing open
    (start a fresh period) is the safer default than either crashing or
    treating a possibly-new paying customer as already over quota."""
    user = _make_user(session, plan="pro", videos_used=9, usage_period_start=None)
    quota.ensure_video_quota_available(user, session)
    assert user.videos_used == 0
    assert user.usage_period_start is not None


def test_owner_plan_is_unlimited(session):
    user = _make_user(session, plan="owner", videos_used=99999)
    quota.ensure_video_quota_available(user, session)  # never raises
    assert quota.remaining_videos(user) is None


def test_remaining_videos_never_goes_negative(session):
    user = _make_user(session, plan="free", videos_used=999)
    assert quota.remaining_videos(user) == 0


def test_failed_render_does_not_consume_quota(session):
    """ensure_video_quota_available() alone (without consume_video_quota())
    must not increment the counter — a render that fails after the check
    but before completion shouldn't cost the user a unit."""
    user = _make_user(session, plan="free", videos_used=0)
    quota.ensure_video_quota_available(user, session)
    assert user.videos_used == 0


def test_ugc_sub_quota_is_tighter_than_general_video_quota_on_free_plan(session):
    """Free allows 3 videos total but only 1 UGC ad — the UGC-specific
    ceiling should bind well before the general one would."""
    user = _make_user(session, plan="free", ugc_videos_used=0)
    quota.ensure_ugc_quota_available(user, session)  # 1st is allowed
    quota.consume_ugc_quota(user, session)
    quota.consume_video_quota(user, session)  # a UGC ad also spends a general video
    assert user.ugc_videos_used == 1
    assert user.videos_used == 1

    with pytest.raises(Exception):
        quota.ensure_ugc_quota_available(user, session)  # 2nd UGC ad rejected, well under the 3-video cap


def test_ugc_sub_quota_rolls_over_with_the_general_quota(session):
    now = datetime.now(timezone.utc)
    user = _make_user(session, plan="pro", videos_used=7, ugc_videos_used=3, usage_period_start=now)
    with pytest.raises(Exception):
        quota.ensure_ugc_quota_available(user, session)  # pro's UGC cap is 3, already hit

    long_ago = now - timedelta(days=31)
    user.usage_period_start = long_ago
    session.add(user)
    session.commit()
    quota.ensure_ugc_quota_available(user, session)  # rollover resets both counters
    assert user.ugc_videos_used == 0
    assert user.videos_used == 0


def test_owner_plan_ugc_is_unlimited(session):
    user = _make_user(session, plan="owner", ugc_videos_used=99999)
    quota.ensure_ugc_quota_available(user, session)  # never raises
    assert quota.remaining_ugc_videos(user) is None


def test_purchased_video_credit_covers_render_after_plan_quota_exhausted(session):
    user = _make_user(session, plan="free", videos_used=3)  # free's cap is 3, already hit
    user.purchased_video_credits = 2
    session.add(user)
    session.commit()

    quota.ensure_video_quota_available(user, session)  # doesn't raise — a purchased credit covers it
    quota.consume_video_quota(user, session)
    assert user.videos_used == 3  # plan counter untouched
    assert user.purchased_video_credits == 1  # drew from the purchased balance instead


def test_video_quota_blocked_when_plan_and_purchased_credits_both_exhausted(session):
    user = _make_user(session, plan="free", videos_used=3)
    with pytest.raises(Exception):
        quota.ensure_video_quota_available(user, session)


def test_purchased_ugc_credit_covers_render_after_plan_ugc_quota_exhausted(session):
    now = datetime.now(timezone.utc)
    user = _make_user(session, plan="pro", ugc_videos_used=3, usage_period_start=now)  # pro's UGC cap is 3
    user.purchased_ugc_credits = 2
    session.add(user)
    session.commit()

    quota.ensure_ugc_quota_available(user, session)  # doesn't raise
    assert quota.ugc_covered_by_purchased_credit(user) is True

    quota.consume_ugc_quota(user, session)
    assert user.ugc_videos_used == 3  # plan counter untouched
    assert user.purchased_ugc_credits == 1


def test_ugc_covered_by_purchased_credit_is_false_when_plan_quota_has_room(session):
    user = _make_user(session, plan="free", ugc_videos_used=0)
    assert quota.ugc_covered_by_purchased_credit(user) is False
