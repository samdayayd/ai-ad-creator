"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ApiError, createBillingPortal, createCheckout, getMe, getPlans } from "@/lib/api";
import { Me, Plan } from "@/lib/types";
import { useAuth } from "@/lib/auth";
import { useLanguage } from "@/lib/LanguageProvider";

// Static display-only conversion, given directly by the app owner — the
// actual Stripe charge still happens in SEK regardless of what's shown
// here, since the Stripe Price IDs behind these plans are SEK-denominated.
// True multi-currency billing would need separate per-currency Stripe
// Prices (or Stripe's presentment-currency setup), which isn't wired up —
// see the on-page disclaimer, which exists specifically so this doesn't
// mislead anyone about what they'll actually be charged.
const USD_PRICE: Record<string, number> = { free: 0, pro: 19, max: 49 };

export default function PricingPage() {
  return (
    <Suspense fallback={<p className="text-slate-400">Loading plans…</p>}>
      <PricingContent />
    </Suspense>
  );
}

function PricingContent() {
  const { token } = useAuth();
  const { locale, t } = useLanguage();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyPlan, setBusyPlan] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const checkoutStatus = searchParams.get("checkout");
  const showSek = locale === "sv";

  useEffect(() => {
    Promise.all([getPlans(), token ? getMe(token) : Promise.resolve(null)])
      .then(([p, m]) => {
        setPlans(p);
        setMe(m);
      })
      .catch(() => setPlans([]))
      .finally(() => setLoading(false));
  }, [token]);

  const handleChoosePlan = async (planId: string) => {
    setError(null);
    if (!token) {
      router.push("/signup");
      return;
    }
    if (planId === "free") return; // nothing to buy — free is the default on signup
    setBusyPlan(planId);
    try {
      const { checkout_url } = await createCheckout(token, planId);
      window.location.href = checkout_url;
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Couldn't start checkout.");
      setBusyPlan(null);
    }
  };

  const handleManageBilling = async () => {
    if (!token) return;
    setError(null);
    setBusyPlan("portal");
    try {
      const { portal_url } = await createBillingPortal(token);
      window.location.href = portal_url;
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Couldn't open the billing portal.");
      setBusyPlan(null);
    }
  };

  if (loading) return <p className="text-slate-400">Loading plans…</p>;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold tracking-wide text-white">{t("pricing.title")}</h1>
        <p className="mt-1 text-sm text-slate-400">{t("pricing.subtitle")}</p>
      </div>

      {checkoutStatus === "success" && (
        <p className="rounded-md border border-emerald-700 bg-emerald-950/40 px-4 py-3 text-sm text-emerald-300">
          {t("pricing.checkoutSuccess")}
        </p>
      )}
      {checkoutStatus === "cancelled" && (
        <p className="panel px-4 py-3 text-sm text-slate-400">{t("pricing.checkoutCancelled")}</p>
      )}
      {error && <p className="text-sm text-rose-400">{error}</p>}

      <div className="grid gap-4 sm:grid-cols-3">
        {plans.map((plan) => {
          const isCurrent = me?.plan === plan.id;
          const priceLabel =
            plan.price_sek === 0
              ? t("pricing.free")
              : showSek
              ? `${plan.price_sek} kr`
              : `$${USD_PRICE[plan.id] ?? plan.price_sek}`;
          return (
            <div
              key={plan.id}
              className={`panel p-6 ${isCurrent ? "border-volt-400/60" : ""}`}
            >
              <h2 className="font-display text-lg font-bold capitalize text-white">{plan.name}</h2>
              <p className="mt-1 text-2xl font-extrabold text-white">
                {priceLabel}
                {plan.price_sek > 0 && <span className="text-sm font-normal text-slate-400">{t("pricing.perMonth")}</span>}
              </p>
              <p className="mt-2 text-sm text-slate-400">{t(`pricing.blurb.${plan.id}`)}</p>
              <p className="mt-3 text-sm text-slate-300">
                {plan.video_limit} video{plan.video_limit === 1 ? "" : "s"}{" "}
                {plan.id === "free" ? t("pricing.total") : t("pricing.perMonthSuffix")}
              </p>
              <p className="mt-1 text-xs text-slate-500">
                {t("pricing.ugcNote").replace("{n}", String(plan.ugc_video_limit))}
              </p>

              <button
                onClick={() => handleChoosePlan(plan.id)}
                disabled={isCurrent || busyPlan === plan.id}
                className={`mt-5 w-full ${isCurrent ? "btn-secondary" : "btn-primary"}`}
              >
                {isCurrent
                  ? t("pricing.current")
                  : busyPlan === plan.id
                  ? t("pricing.redirecting")
                  : !token
                  ? t("pricing.signUp")
                  : plan.id === "free"
                  ? t("pricing.downgrade")
                  : t("pricing.subscribe")}
              </button>
            </div>
          );
        })}
      </div>

      {!showSek && <p className="text-xs text-slate-500">{t("pricing.currencyNote")}</p>}

      {me && me.plan !== "free" && me.plan !== "owner" && (
        <button onClick={handleManageBilling} disabled={busyPlan === "portal"} className="btn-secondary">
          {busyPlan === "portal" ? t("pricing.opening") : t("pricing.manageBilling")}
        </button>
      )}
    </div>
  );
}
