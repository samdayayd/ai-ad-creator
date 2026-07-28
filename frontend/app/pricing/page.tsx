"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ApiError, createBillingPortal, createCheckout, getMe, getPlans } from "@/lib/api";
import { Me, Plan } from "@/lib/types";
import { useAuth } from "@/lib/auth";

const PLAN_BLURBS: Record<string, string> = {
  free: "Try it out — watermarked, no card required.",
  pro: "For regular use — no watermark.",
  max: "For heavy use — no watermark, higher monthly limit.",
};

export default function PricingPage() {
  return (
    <Suspense fallback={<p className="text-slate-400">Loading plans…</p>}>
      <PricingContent />
    </Suspense>
  );
}

function PricingContent() {
  const { token } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [busyPlan, setBusyPlan] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const checkoutStatus = searchParams.get("checkout");

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
        <h1 className="text-2xl font-extrabold text-white">Pricing</h1>
        <p className="mt-1 text-sm text-slate-400">
          Video and UGC ads count against your plan&apos;s quota. Text ads (paste a URL, get copy) are free on every
          plan.
        </p>
      </div>

      {checkoutStatus === "success" && (
        <p className="rounded-md border border-emerald-700 bg-emerald-950/40 px-4 py-3 text-sm text-emerald-300">
          Subscription active — thanks! It may take a few seconds to reflect here.
        </p>
      )}
      {checkoutStatus === "cancelled" && (
        <p className="rounded-md border border-ink-700 bg-ink-900 px-4 py-3 text-sm text-slate-400">
          Checkout cancelled — no charge was made.
        </p>
      )}
      {error && <p className="text-sm text-rose-400">{error}</p>}

      <div className="grid gap-4 sm:grid-cols-3">
        {plans.map((plan) => {
          const isCurrent = me?.plan === plan.id;
          return (
            <div
              key={plan.id}
              className={`rounded-xl border p-6 ${
                isCurrent ? "border-spark-500 bg-ink-900" : "border-ink-700 bg-ink-900"
              }`}
            >
              <h2 className="text-lg font-bold capitalize text-white">{plan.name}</h2>
              <p className="mt-1 text-2xl font-extrabold text-white">
                {plan.price_sek === 0 ? "Free" : `${plan.price_sek} kr`}
                {plan.price_sek > 0 && <span className="text-sm font-normal text-slate-400">/month</span>}
              </p>
              <p className="mt-2 text-sm text-slate-400">{PLAN_BLURBS[plan.id]}</p>
              <p className="mt-3 text-sm text-slate-300">
                {plan.video_limit} video{plan.video_limit === 1 ? "" : "s"}{" "}
                {plan.id === "free" ? "total" : "per month"}
              </p>

              <button
                onClick={() => handleChoosePlan(plan.id)}
                disabled={isCurrent || busyPlan === plan.id}
                className={`mt-5 w-full rounded-md px-4 py-2 text-sm font-bold disabled:opacity-60 ${
                  isCurrent
                    ? "border border-ink-700 text-slate-400"
                    : "bg-spark-500 text-white hover:bg-spark-400"
                }`}
              >
                {isCurrent
                  ? "Current plan"
                  : busyPlan === plan.id
                  ? "Redirecting…"
                  : !token
                  ? "Sign up"
                  : plan.id === "free"
                  ? "Downgrade via billing portal"
                  : "Subscribe"}
              </button>
            </div>
          );
        })}
      </div>

      {me && me.plan !== "free" && me.plan !== "owner" && (
        <button
          onClick={handleManageBilling}
          disabled={busyPlan === "portal"}
          className="rounded-md border border-ink-700 px-4 py-2 text-sm text-slate-300 hover:border-spark-500 hover:text-white disabled:opacity-60"
        >
          {busyPlan === "portal" ? "Opening…" : "Manage billing / cancel subscription"}
        </button>
      )}
    </div>
  );
}
