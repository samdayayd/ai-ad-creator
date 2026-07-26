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
