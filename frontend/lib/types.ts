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
