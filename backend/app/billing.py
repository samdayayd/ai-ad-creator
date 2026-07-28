"""Stripe subscription billing: Checkout for upgrading, the Customer Portal
for self-service plan management/cancellation, and a webhook that keeps
each User row's plan/quota state in sync with what Stripe actually charged.

Requires a real Stripe account — set STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET,
STRIPE_PRICE_ID_PRO, STRIPE_PRICE_ID_MAX. None of this has been exercised
against a live Stripe account from this repo — expect the first real
checkout/webhook test to need a small fix, the same way every other
third-party integration in this app did (Cloud Run's IAM grants, D-ID/
ElevenLabs' request shapes). That's normal, not a sign of a bug.
"""

from datetime import datetime, timezone

import stripe
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import (
    FRONTEND_URL,
    STRIPE_PRICE_ID_MAX,
    STRIPE_PRICE_ID_PRO,
    STRIPE_SECRET_KEY,
    STRIPE_WEBHOOK_SECRET,
)
from app.db import User

PRICE_TO_PLAN = {STRIPE_PRICE_ID_PRO: "pro", STRIPE_PRICE_ID_MAX: "max"}
PLAN_TO_PRICE = {"pro": STRIPE_PRICE_ID_PRO, "max": STRIPE_PRICE_ID_MAX}


def _require_stripe() -> None:
    if not STRIPE_SECRET_KEY:
        raise HTTPException(
            status_code=503,
            detail="Billing isn't set up yet. Set STRIPE_SECRET_KEY in the backend environment.",
        )
    stripe.api_key = STRIPE_SECRET_KEY


def create_checkout_session(user: User, plan: str) -> str:
    _require_stripe()
    price_id = PLAN_TO_PRICE.get(plan)
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Unknown or unconfigured plan: {plan}")

    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        customer=user.stripe_customer_id or None,
        customer_email=None if user.stripe_customer_id else user.email,
        client_reference_id=str(user.id),
        success_url=f"{FRONTEND_URL}/pricing?checkout=success",
        cancel_url=f"{FRONTEND_URL}/pricing?checkout=cancelled",
        metadata={"user_id": str(user.id), "plan": plan},
    )
    return session.url


def create_portal_session(user: User) -> str:
    _require_stripe()
    if not user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account yet — subscribe to a plan first.")
    session = stripe.billing_portal.Session.create(
        customer=user.stripe_customer_id,
        return_url=f"{FRONTEND_URL}/pricing",
    )
    return session.url


def handle_webhook_event(payload: bytes, signature: str, session: Session) -> None:
    _require_stripe()
    try:
        event = stripe.Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid webhook payload: {exc}") from exc
    except Exception as exc:
        # Covers stripe.SignatureVerificationError — caught broadly since its
        # exact import path has moved between SDK major versions.
        raise HTTPException(status_code=400, detail=f"Invalid webhook signature: {exc}") from exc

    event_type = event["type"]
    data = event["data"]["object"]
    if event_type == "checkout.session.completed":
        _on_checkout_completed(data, session)
    elif event_type == "customer.subscription.updated":
        _on_subscription_updated(data, session)
    elif event_type == "customer.subscription.deleted":
        _on_subscription_deleted(data, session)
    elif event_type == "invoice.paid":
        _on_invoice_paid(data, session)


def _find_user(session: Session, *, user_id: str | None = None, customer_id: str | None = None) -> User | None:
    if user_id:
        user = session.get(User, int(user_id))
        if user:
            return user
    if customer_id:
        return session.query(User).filter(User.stripe_customer_id == customer_id).first()
    return None


def _on_checkout_completed(data: dict, session: Session) -> None:
    user_id = data.get("client_reference_id") or (data.get("metadata") or {}).get("user_id")
    plan = (data.get("metadata") or {}).get("plan")
    user = _find_user(session, user_id=user_id)
    if not user or not plan:
        return
    user.stripe_customer_id = data.get("customer")
    user.stripe_subscription_id = data.get("subscription")
    user.plan = plan
    user.videos_used = 0
    user.usage_period_start = datetime.now(timezone.utc)
    session.add(user)
    session.commit()


def _on_subscription_updated(data: dict, session: Session) -> None:
    user = _find_user(session, customer_id=data.get("customer"))
    if not user:
        return
    items = (data.get("items") or {}).get("data") or []
    price_id = items[0]["price"]["id"] if items else None
    plan = PRICE_TO_PLAN.get(price_id)
    if plan and data.get("status") in ("active", "trialing"):
        user.plan = plan
        session.add(user)
        session.commit()


def _on_subscription_deleted(data: dict, session: Session) -> None:
    user = _find_user(session, customer_id=data.get("customer"))
    if not user:
        return
    user.plan = "free"
    user.stripe_subscription_id = None
    session.add(user)
    session.commit()


def _on_invoice_paid(data: dict, session: Session) -> None:
    user = _find_user(session, customer_id=data.get("customer"))
    if not user or user.plan not in ("pro", "max"):
        return
    user.videos_used = 0
    user.usage_period_start = datetime.now(timezone.utc)
    session.add(user)
    session.commit()
