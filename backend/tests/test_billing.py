import pytest

from app import billing
from app.db import Base, SessionLocal, User, engine


@pytest.fixture()
def session():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    s = SessionLocal()
    yield s
    s.close()


def _make_user(session, **kwargs):
    user = User(email="u@example.com", hashed_password="x", **kwargs)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def test_checkout_completed_upgrades_user_and_resets_usage(session):
    user = _make_user(session, plan="free", videos_used=5)
    data = {
        "client_reference_id": str(user.id),
        "customer": "cus_123",
        "subscription": "sub_123",
        "metadata": {"user_id": str(user.id), "plan": "pro"},
    }
    billing._on_checkout_completed(data, session)
    session.refresh(user)
    assert user.plan == "pro"
    assert user.stripe_customer_id == "cus_123"
    assert user.stripe_subscription_id == "sub_123"
    assert user.videos_used == 0
    assert user.usage_period_start is not None


def test_checkout_completed_ignores_unknown_user(session):
    # Should not raise even if the user_id in metadata doesn't exist.
    billing._on_checkout_completed({"client_reference_id": "99999", "metadata": {"plan": "pro"}}, session)


def test_subscription_updated_changes_plan_on_upgrade(session):
    user = _make_user(session, plan="pro", stripe_customer_id="cus_123")
    data = {
        "customer": "cus_123",
        "status": "active",
        "items": {"data": [{"price": {"id": billing.STRIPE_PRICE_ID_MAX or "price_max"}}]},
    }
    # Simulate a configured price mapping regardless of env by patching directly.
    billing.PRICE_TO_PLAN[data["items"]["data"][0]["price"]["id"]] = "max"
    billing._on_subscription_updated(data, session)
    session.refresh(user)
    assert user.plan == "max"


def test_subscription_updated_ignores_inactive_status(session):
    user = _make_user(session, plan="pro", stripe_customer_id="cus_123")
    price_id = "price_test_inactive"
    billing.PRICE_TO_PLAN[price_id] = "max"
    data = {"customer": "cus_123", "status": "canceled", "items": {"data": [{"price": {"id": price_id}}]}}
    billing._on_subscription_updated(data, session)
    session.refresh(user)
    assert user.plan == "pro"  # unchanged — cancellation is handled by subscription.deleted, not this


def test_subscription_deleted_reverts_to_free(session):
    user = _make_user(session, plan="max", stripe_customer_id="cus_123", stripe_subscription_id="sub_123")
    billing._on_subscription_deleted({"customer": "cus_123"}, session)
    session.refresh(user)
    assert user.plan == "free"
    assert user.stripe_subscription_id is None


def test_invoice_paid_resets_monthly_usage(session):
    user = _make_user(session, plan="pro", stripe_customer_id="cus_123", videos_used=18)
    billing._on_invoice_paid({"customer": "cus_123"}, session)
    session.refresh(user)
    assert user.videos_used == 0
    assert user.usage_period_start is not None


def test_invoice_paid_ignores_free_plan_users(session):
    """A stray invoice.paid for a free-plan user (shouldn't happen, but
    defensively) must not touch their usage."""
    user = _make_user(session, plan="free", stripe_customer_id="cus_123", videos_used=3)
    billing._on_invoice_paid({"customer": "cus_123"}, session)
    session.refresh(user)
    assert user.videos_used == 3


def test_create_checkout_session_requires_stripe_key(monkeypatch):
    monkeypatch.setattr(billing, "STRIPE_SECRET_KEY", "")
    user = User(id=1, email="u@example.com", hashed_password="x", plan="free")
    with pytest.raises(Exception):
        billing.create_checkout_session(user, "pro")


def test_create_portal_session_requires_existing_customer(monkeypatch):
    monkeypatch.setattr(billing, "STRIPE_SECRET_KEY", "sk_test_fake")
    user = User(id=1, email="u@example.com", hashed_password="x", plan="free", stripe_customer_id=None)
    with pytest.raises(Exception):
        billing.create_portal_session(user)


def test_webhook_rejects_invalid_signature(monkeypatch, session):
    monkeypatch.setattr(billing, "STRIPE_SECRET_KEY", "sk_test_fake")

    def _raise(*args, **kwargs):
        raise ValueError("bad payload")

    monkeypatch.setattr(billing.stripe.Webhook, "construct_event", _raise)
    with pytest.raises(Exception):
        billing.handle_webhook_event(b"{}", "bad-signature", session)


def test_credit_purchase_completed_adds_video_credits(session):
    user = _make_user(session, plan="free")
    data = {"mode": "payment", "metadata": {"user_id": str(user.id), "sku": "standard_5"}}
    billing._on_credit_purchase_completed(data, session)
    session.refresh(user)
    assert user.purchased_video_credits == 5
    assert user.purchased_ugc_credits == 0


def test_credit_purchase_completed_adds_ugc_credits(session):
    user = _make_user(session, plan="free")
    data = {"mode": "payment", "metadata": {"user_id": str(user.id), "sku": "ugc_1"}}
    billing._on_credit_purchase_completed(data, session)
    session.refresh(user)
    assert user.purchased_ugc_credits == 1
    assert user.purchased_video_credits == 0


def test_credit_purchase_completed_ignores_unknown_sku(session):
    user = _make_user(session, plan="free")
    data = {"mode": "payment", "metadata": {"user_id": str(user.id), "sku": "not-a-real-sku"}}
    billing._on_credit_purchase_completed(data, session)  # should not raise
    session.refresh(user)
    assert user.purchased_video_credits == 0
    assert user.purchased_ugc_credits == 0


def test_webhook_routes_payment_mode_checkout_to_credit_purchase(monkeypatch, session):
    """checkout.session.completed fires for both subscription and one-time
    Checkout Sessions — mode is what the webhook uses to tell them apart."""
    monkeypatch.setattr(billing, "STRIPE_SECRET_KEY", "sk_test_fake")
    user = _make_user(session, plan="free")
    fake_event = {
        "type": "checkout.session.completed",
        "data": {"object": {"mode": "payment", "metadata": {"user_id": str(user.id), "sku": "standard_1"}}},
    }
    monkeypatch.setattr(billing.stripe.Webhook, "construct_event", lambda *a, **k: fake_event)
    billing.handle_webhook_event(b"{}", "sig", session)
    session.refresh(user)
    assert user.purchased_video_credits == 1
    assert user.plan == "free"  # unaffected — this must not run the subscription handler


def test_create_credit_checkout_requires_stripe_key(monkeypatch):
    monkeypatch.setattr(billing, "STRIPE_SECRET_KEY", "")
    user = User(id=1, email="u@example.com", hashed_password="x", plan="free")
    with pytest.raises(Exception):
        billing.create_credit_checkout_session(user, "standard_1")


def test_create_credit_checkout_rejects_unknown_sku(monkeypatch):
    monkeypatch.setattr(billing, "STRIPE_SECRET_KEY", "sk_test_fake")
    user = User(id=1, email="u@example.com", hashed_password="x", plan="free")
    with pytest.raises(Exception):
        billing.create_credit_checkout_session(user, "not-a-real-sku")
