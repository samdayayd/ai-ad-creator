from datetime import datetime

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class SignupRequest(BaseModel):
    email: str
    password: str


class ContactRequest(BaseModel):
    name: str
    email: str
    message: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeOut(BaseModel):
    email: str
    plan: str
    videos_used: int
    videos_remaining: int | None  # None means unlimited (the owner account)
    ugc_videos_used: int
    ugc_videos_remaining: int | None  # None means unlimited (the owner account)


class PlanOut(BaseModel):
    id: str
    name: str
    price_sek: int
    video_limit: int
    ugc_video_limit: int


class CheckoutRequest(BaseModel):
    plan: str


class CheckoutResponse(BaseModel):
    checkout_url: str


class PortalResponse(BaseModel):
    portal_url: str


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


class VideoScriptRequest(BaseModel):
    product_name: str
    product_description: str = ""
    duration_seconds: int


class VideoScriptOut(BaseModel):
    scenes: list[str]


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


class UGCScriptRequest(BaseModel):
    prompt: str
    product_name: str
    product_description: str = ""


class PresenterOut(BaseModel):
    id: str
    name: str
    gender: str | None = None
    thumbnail_url: str | None = None


class VoiceOut(BaseModel):
    id: str
    name: str
    preview_url: str | None = None


class UGCScriptOut(BaseModel):
    hook: str
    intro: str
    benefits: list[str]
    cta_line: str


class UGCAdOut(BaseModel):
    id: int
    product_title: str | None
    presenter_name: str
    voice_name: str
    cta_text: str
    script: UGCScriptOut
    video_url: str


class UGCGenerationOut(UGCAdOut):
    created_at: datetime
