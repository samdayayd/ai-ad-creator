from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ad_generator import generate_ad_set
from app.auth import get_current_user
from app.db import AdGeneration, User, get_session
from app.scraper import fetch_product_info
from app.schemas import AdGenerationOut, AdSetOut, CreateAdsRequest

router = APIRouter(prefix="/api/ads", tags=["ads"])


@router.post("/create", response_model=AdSetOut)
def create_ads(
    body: CreateAdsRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """The one-click flow: paste a product URL, get a full ad set back.
    Scrapes the page for title/description/price/image, then makes one
    Claude API call to write every channel's copy from that same info, so
    everything stays consistent with the actual product instead of each
    channel inventing its own details."""
    product = fetch_product_info(body.url)
    result = generate_ad_set(product)
    ad_set = AdSetOut(
        product_url=product.url,
        product_title=product.title,
        product_image=product.image,
        **result,
    )

    session.add(
        AdGeneration(
            user_id=user.id,
            product_url=product.url,
            product_title=product.title,
            product_image=product.image,
            result_json=ad_set.model_dump(),
        )
    )
    session.commit()

    return ad_set


@router.get("/history", response_model=list[AdGenerationOut])
def ad_history(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    """Past generations for this owner — so revisiting an old ad set doesn't
    cost another API call."""
    rows = (
        session.query(AdGeneration)
        .filter(AdGeneration.user_id == user.id)
        .order_by(AdGeneration.created_at.desc())
        .all()
    )
    return [
        AdGenerationOut(
            id=r.id,
            product_url=r.product_url,
            product_title=r.product_title,
            product_image=r.product_image,
            created_at=r.created_at,
            result=r.result_json,
        )
        for r in rows
    ]
