from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CreateAdsRequest(BaseModel):
    url: str


class TikTokAdOut(BaseModel):
    hook: str
    script: str
    caption: str
    hashtags: list[str]


class FacebookAdOut(BaseModel):
    primary_text: str
    headline: str
    description: str


class GoogleAdsOut(BaseModel):
    headlines: list[str]  # short punchy variants, <=30 chars each — Google Ads' own headline limit
    descriptions: list[str]  # <=90 chars each


class EmailCampaignOut(BaseModel):
    subject: str
    preview_text: str
    body: str


class AdSetOut(BaseModel):
    product_url: str
    product_title: str
    product_image: str | None
    tiktok_ad: TikTokAdOut
    facebook_ad: FacebookAdOut
    google_ads: GoogleAdsOut
    instagram_caption: str
    headlines: list[str]
    product_description: str
    email_campaign: EmailCampaignOut


class AdGenerationOut(BaseModel):
    id: int
    product_url: str
    product_title: str | None
    product_image: str | None
    created_at: datetime
    result: AdSetOut


class VideoSceneOut(BaseModel):
    text: str
    duration: float


class VideoAdOut(BaseModel):
    id: int
    product_title: str | None
    requested_duration_seconds: int
    actual_duration_seconds: float
    scenes: list[VideoSceneOut]
    video_url: str


class VideoGenerationOut(BaseModel):
    id: int
    product_title: str | None
    requested_duration_seconds: int
    actual_duration_seconds: float
    scenes: list[VideoSceneOut]
    video_url: str
    created_at: datetime
