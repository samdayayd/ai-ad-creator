import { AdSet } from "@/lib/types";
import CopyButton from "./CopyButton";

function Section({ title, copyText, children }: { title: string; copyText: string; children: React.ReactNode }) {
  return (
    <section className="panel p-4">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="font-display text-sm font-bold uppercase tracking-wide glow-text">{title}</h2>
        <CopyButton text={copyText} />
      </div>
      <div className="space-y-2 text-sm text-slate-200">{children}</div>
    </section>
  );
}

export default function AdResults({ adSet }: { adSet: AdSet }) {
  const { tiktok_ad, facebook_ad, google_ads, instagram_caption, headlines, product_description, email_campaign } =
    adSet;

  return (
    <div className="space-y-4">
      <div className="panel flex items-center gap-3 p-4">
        {adSet.product_image && (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={adSet.product_image} alt="" className="h-16 w-16 rounded-lg object-cover" />
        )}
        <div>
          <p className="font-bold text-white">{adSet.product_title}</p>
          <a href={adSet.product_url} target="_blank" rel="noreferrer" className="text-xs text-volt-300 underline">
            {adSet.product_url}
          </a>
        </div>
      </div>

      <Section
        title="TikTok Ad"
        copyText={`${tiktok_ad.hook}\n\n${tiktok_ad.script}\n\n${tiktok_ad.caption}\n${tiktok_ad.hashtags.join(" ")}`}
      >
        <p>
          <span className="font-semibold text-white">Hook:</span> {tiktok_ad.hook}
        </p>
        <p className="whitespace-pre-line">
          <span className="font-semibold text-white">Script:</span> {tiktok_ad.script}
        </p>
        <p>
          <span className="font-semibold text-white">Caption:</span> {tiktok_ad.caption}
        </p>
        <p className="text-volt-300">{tiktok_ad.hashtags.join(" ")}</p>
      </Section>

      <Section
        title="Facebook Ad"
        copyText={`${facebook_ad.primary_text}\n\n${facebook_ad.headline}\n${facebook_ad.description}`}
      >
        <p>{facebook_ad.primary_text}</p>
        <p className="font-semibold text-white">{facebook_ad.headline}</p>
        <p className="text-slate-400">{facebook_ad.description}</p>
      </Section>

      <Section
        title="Google Ads"
        copyText={`Headlines:\n${google_ads.headlines.join("\n")}\n\nDescriptions:\n${google_ads.descriptions.join("\n")}`}
      >
        <div>
          <p className="mb-1 text-xs font-semibold text-slate-400">Headlines</p>
          <ul className="list-inside list-disc">
            {google_ads.headlines.map((h, i) => (
              <li key={i}>{h}</li>
            ))}
          </ul>
        </div>
        <div>
          <p className="mb-1 text-xs font-semibold text-slate-400">Descriptions</p>
          <ul className="list-inside list-disc">
            {google_ads.descriptions.map((d, i) => (
              <li key={i}>{d}</li>
            ))}
          </ul>
        </div>
      </Section>

      <Section title="Instagram Caption" copyText={instagram_caption}>
        <p className="whitespace-pre-line">{instagram_caption}</p>
      </Section>

      <Section title="Headlines" copyText={headlines.join("\n")}>
        <ul className="list-inside list-disc">
          {headlines.map((h, i) => (
            <li key={i}>{h}</li>
          ))}
        </ul>
      </Section>

      <Section title="Product Description" copyText={product_description}>
        <p className="whitespace-pre-line">{product_description}</p>
      </Section>

      <Section
        title="Email Campaign"
        copyText={`Subject: ${email_campaign.subject}\nPreview: ${email_campaign.preview_text}\n\n${email_campaign.body}`}
      >
        <p>
          <span className="font-semibold text-white">Subject:</span> {email_campaign.subject}
        </p>
        <p className="text-slate-400">
          <span className="font-semibold text-white">Preview:</span> {email_campaign.preview_text}
        </p>
        <p className="whitespace-pre-line">{email_campaign.body}</p>
      </Section>
    </div>
  );
}
