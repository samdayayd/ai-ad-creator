from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.billing import create_checkout_session, create_portal_session, handle_webhook_event
from app.config import PLAN_LIMITS, PLAN_PRICE_SEK, UGC_PLAN_LIMITS
from app.db import User, get_session
from app.schemas import CheckoutRequest, CheckoutResponse, PlanOut, PortalResponse

router = APIRouter(prefix="/api/billing", tags=["billing"])


@router.get("/plans", response_model=list[PlanOut])
def plans():
    """Publicly readable — the pricing page needs this before a visitor is
    signed in. PLAN_LIMITS only ever contains the purchasable plans (free/
    pro/max) — the owner account's unlimited access lives outside it
    entirely (see config.OWNER_PLAN), so there's nothing to filter out here."""
    return [
        PlanOut(
            id=plan_id,
            name=plan_id.capitalize(),
            price_sek=PLAN_PRICE_SEK[plan_id],
            video_limit=limit,
            ugc_video_limit=UGC_PLAN_LIMITS[plan_id],
        )
        for plan_id, limit in PLAN_LIMITS.items()
    ]


@router.post("/checkout", response_model=CheckoutResponse)
def checkout(body: CheckoutRequest, user: User = Depends(get_current_user)):
    url = create_checkout_session(user, body.plan)
    return CheckoutResponse(checkout_url=url)


@router.post("/portal", response_model=PortalResponse)
def portal(user: User = Depends(get_current_user)):
    url = create_portal_session(user)
    return PortalResponse(portal_url=url)


@router.post("/webhook")
async def webhook(
    request: Request,
    stripe_signature: str = Header(None),
    session: Session = Depends(get_session),
):
    """Called directly by Stripe, not by our own frontend — authenticated by
    the Stripe-Signature header (verified inside handle_webhook_event), not
    a JWT. Must read the raw body: signature verification hashes the exact
    bytes Stripe sent, which a parsed-then-reserialized JSON body would not
    reproduce byte-for-byte."""
    payload = await request.body()
    handle_webhook_event(payload, stripe_signature, session)
    return {"received": True}
