export interface TikTokAd {
  hook: string;
  script: string;
  caption: string;
  hashtags: string[];
}

export interface FacebookAd {
  primary_text: string;
  headline: string;
  description: string;
}

export interface GoogleAds {
  headlines: string[];
  descriptions: string[];
}

export interface EmailCampaign {
  subject: string;
  preview_text: string;
  body: string;
}

export interface AdSet {
  product_url: string;
  product_title: string;
  product_image: string | null;
  tiktok_ad: TikTokAd;
  facebook_ad: FacebookAd;
  google_ads: GoogleAds;
  instagram_caption: string;
  headlines: string[];
  product_description: string;
  email_campaign: EmailCampaign;
}

export interface AdGeneration {
  id: number;
  product_url: string;
  product_title: string | null;
  product_image: string | null;
  created_at: string;
  result: AdSet;
}

export interface VideoScene {
  text: string;
  duration: number;
}

export interface VideoAd {
  id: number;
  product_title: string | null;
  requested_duration_seconds: number;
  actual_duration_seconds: number;
  scenes: VideoScene[];
  video_url: string;
}

export interface VideoGeneration extends VideoAd {
  created_at: string;
}

export const VIDEO_DURATIONS = [20, 30, 40, 50, 60] as const;

export interface Presenter {
  id: string;
  name: string;
  gender: string | null;
  thumbnail_url: string | null;
}

export interface Voice {
  id: string;
  name: string;
  preview_url: string | null;
}

export interface UGCScript {
  hook: string;
  intro: string;
  benefits: string[];
  cta_line: string;
}

export interface UGCAd {
  id: number;
  product_title: string | null;
  presenter_name: string;
  voice_name: string;
  cta_text: string;
  script: UGCScript;
  video_url: string;
}

export interface UGCGeneration extends UGCAd {
  created_at: string;
}

export const CTA_OPTIONS = ["Buy Now", "Shop Today", "Limited Offer", "Order Today", "Learn More", "Visit Website"] as const;

export interface Me {
  email: string;
  plan: string;
  videos_used: number;
  videos_remaining: number | null; // null means unlimited (the owner account)
  ugc_videos_used: number;
  ugc_videos_remaining: number | null; // null means unlimited (the owner account)
}

export interface Plan {
  id: string;
  name: string;
  price_sek: number;
  video_limit: number;
  ugc_video_limit: number;
}

