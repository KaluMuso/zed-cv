"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Script from "next/script";
import { toast } from "sonner";
import { subscription, tiers, profile, type TierConfigRow } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Icon } from "@/components/ui/Icon";
import {
  formatMatchesLimit,
  formatPriceLabel,
  UNLIMITED_MATCHES,
} from "@/lib/tier-config";

const LENCO_WIDGET_URL =
  process.env.NEXT_PUBLIC_LENCO_WIDGET_URL?.trim() ||
  "https://pay.sandbox.lenco.co/js/v1/inline.js";

const TIER_RANK: Record<string, number> = {
  free: 0,
  starter: 1,
  professional: 2,
  super_standard: 3,
};

interface Plan {
  name: string;
  subtitle: string;
  price: string;
  period: string;
  tier: string;
  features: string[];
  highlight: boolean;
}

const plans: Plan[] = [
  {
    name: "Free",
    subtitle: "Get started",
    price: "K0",
    period: "forever",
    tier: "free",
    features: [
      "10 job matches per month",
      "WhatsApp alerts",
      "Basic CV analysis",
      "Job browsing",
    ],
    highlight: false,
  },
  {
    name: "Starter",
    subtitle: "Most Popular",
    price: "K125",
    period: "/month",
    tier: "starter",
    features: [
      "50 job matches per month",
      "AI-generated tailored CVs",
      "Priority matching",
      "WhatsApp + web dashboard",
      "Score breakdowns",
    ],
    highlight: true,
  },
  {
    name: "Professional",
    subtitle: "For power users",
    price: "K250",
    period: "/month",
    tier: "professional",
    features: [
      "125 job matches per month",
      "AI cover letter generation",
      "Career coaching insights",
      "Priority support",
      "CV rewriting per role",
      "Everything in Starter",
    ],
    highlight: false,
  },
  {
    name: "Super Standard",
    subtitle: "Top tier",
    price: "K500",
    period: "/month",
    tier: "super_standard",
    features: [
      "Unlimited job matches",
      "Interview prep notes (Interview Call)",
      "Everything in Professional",
      "Priority delivery",
      "Concierge onboarding",
    ],
    highlight: false,
  },
];

const faqs = [
  {
    q: "How does payment work?",
    a: "Select a paid plan and the secure Lenco checkout opens. Pay with MTN MoMo, Airtel Money, or card. Once Lenco confirms payment, your account upgrades automatically.",
  },
  {
    q: "Can I switch plans at any time?",
    a: "Yes! Upgrade or downgrade anytime. When upgrading, you'll be charged the plan price. When downgrading, the change takes effect at the end of your billing cycle.",
  },
  {
    q: "What counts as a 'match'?",
    a: "Each time our AI scores your CV against a job listing and delivers the result to you (via WhatsApp or dashboard), that counts as one match. The Free tier includes 10 per month.",
  },
  {
    q: "Is my CV data secure?",
    a: "Absolutely. Your CV is encrypted at rest and in transit. We never share your personal data with employers without your explicit consent.",
  },
];

interface ComparisonFeature {
  name: string;
  free: string | boolean;
  starter: string | boolean;
  pro: string | boolean;
  super_standard: string | boolean;
}

const comparisonFeatures: ComparisonFeature[] = [
  { name: "Job matches / month", free: "10", starter: "50", pro: "125", super_standard: "Unlimited" },
  { name: "WhatsApp alerts", free: true, starter: true, pro: true, super_standard: true },
  { name: "CV analysis", free: "Basic", starter: "Advanced", pro: "Advanced", super_standard: "Advanced" },
  { name: "Tailored CVs", free: false, starter: true, pro: true, super_standard: true },
  { name: "Cover letters", free: false, starter: false, pro: true, super_standard: true },
  { name: "Score breakdowns", free: false, starter: true, pro: true, super_standard: true },
  { name: "CV rewriting per role", free: false, starter: false, pro: true, super_standard: true },
  { name: "Priority support", free: false, starter: false, pro: true, super_standard: true },
  { name: "Interview prep notes", free: false, starter: false, pro: false, super_standard: true },
];

function applyTierConfig(base: Plan[], config: TierConfigRow[]): Plan[] {
  const byTier = Object.fromEntries(config.map((t) => [t.tier, t]));
  return base.map((plan) => {
    const row = byTier[plan.tier];
    if (!row) return plan;
    const matchLine =
      row.matches_limit >= UNLIMITED_MATCHES
        ? "Unlimited job matches"
        : `${formatMatchesLimit(row.matches_limit)} job matches per month`;
    const features = plan.features.map((f, i) =>
      i === 0 && /matches/i.test(f) ? matchLine : f,
    );
    return {
      ...plan,
      name: row.display_name || plan.name,
      price: formatPriceLabel(row.price_ngwee, plan.tier),
      features,
    };
  });
}

function splitName(fullName: string | null): { firstName: string; lastName: string } {
  const full = (fullName || "Zed CV User").trim();
  const parts = full.split(/\s+/).filter(Boolean);
  if (parts.length === 0) return { firstName: "Zed", lastName: "User" };
  if (parts.length === 1) return { firstName: parts[0], lastName: parts[0] };
  return { firstName: parts[0], lastName: parts.slice(1).join(" ") };
}

function lencoPhone(phone: string | null | undefined): string {
  const raw = (phone || "").trim();
  if (!raw) return "0961111111";
  if (raw.startsWith("+260")) return `0${raw.slice(4)}`;
  if (raw.startsWith("260")) return `0${raw.slice(3)}`;
  if (raw.startsWith("0")) return raw;
  return `0${raw}`;
}

function isLencoReady(): boolean {
  return typeof window !== "undefined" && typeof window.LencoPay?.getPaid === "function";
}

export default function PricingPage() {
  const router = useRouter();
  const { token, user, isAuthenticated, isLoading: authLoading } = useAuth();
  const [displayPlans, setDisplayPlans] = useState<Plan[]>(plans);
  const [tierRows, setTierRows] = useState<TierConfigRow[]>([]);
  const [payingTier, setPayingTier] = useState<string | null>(null);
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [currentTier, setCurrentTier] = useState<string>("free");
  const [lencoReady, setLencoReady] = useState(false);

  useEffect(() => {
    if (isLencoReady()) setLencoReady(true);
    const id = window.setInterval(() => {
      if (isLencoReady()) {
        setLencoReady(true);
        window.clearInterval(id);
      }
    }, 200);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    tiers
      .list()
      .then((r) => {
        setTierRows(r.tiers);
        setDisplayPlans(applyTierConfig(plans, r.tiers));
      })
      .catch(() => setDisplayPlans(plans));
  }, []);

  useEffect(() => {
    if (!token) {
      setCurrentTier("free");
      return;
    }
    subscription
      .get(token)
      .then((sub) => setCurrentTier(sub?.tier ?? "free"))
      .catch(() => setCurrentTier("free"));
  }, [token]);

  const amountKwacha = useCallback(
    (tier: string): number => {
      const row = tierRows.find((t) => t.tier === tier);
      if (row) return row.price_ngwee / 100;
      const fallback: Record<string, number> = {
        starter: 125,
        professional: 250,
        super_standard: 500,
      };
      return fallback[tier] ?? 0;
    },
    [tierRows],
  );

  const planAction = (
    planTier: string,
  ): "current" | "downgrade" | "upgrade" | "signup" => {
    if (!isAuthenticated) return planTier === "free" ? "signup" : "upgrade";
    const cur = TIER_RANK[currentTier] ?? 0;
    const target = TIER_RANK[planTier] ?? 0;
    if (cur === target) return "current";
    if (target < cur) return "downgrade";
    return "upgrade";
  };

  const startLencoPayment = async (tier: string) => {
    console.log("[upgrade-click]", tier);

    if (!token || !user?.id) {
      router.push("/auth?next=/pricing");
      return;
    }

    const publicKey = process.env.NEXT_PUBLIC_LENCO_PUBLIC_KEY?.trim();
    if (!publicKey) {
      toast.error("Payments are not configured. Please try again later.");
      return;
    }

    if (!isLencoReady()) {
      toast.error("Payment widget is loading — please wait a moment and try again.");
      return;
    }

    setPayingTier(tier);
    try {
      let prof: Awaited<ReturnType<typeof profile.get>> | null = null;
      try {
        prof = await profile.get(token);
      } catch (err) {
        console.warn("[upgrade-click] profile fetch failed, using fallbacks", err);
      }

      const email =
        prof?.email?.trim() || `payments+${user.id.slice(0, 8)}@zedapply.com`;
      const { firstName, lastName } = splitName(prof?.full_name ?? null);
      const reference = `zedapply-${user.id}-${Date.now()}`;
      const amount = amountKwacha(tier);

      window.label = "ZedApply";

      window.LencoPay!.getPaid({
        key: publicKey,
        label: "ZedApply",
        reference,
        email,
        amount,
        currency: "ZMW",
        channels: ["card", "mobile-money"],
        customer: {
          firstName,
          lastName,
          phone: lencoPhone(prof?.phone),
        },
        onSuccess: async (response) => {
          console.log("[lenco-success]", response.reference);
          try {
            const result = await subscription.verifyPayment(token, {
              reference: response.reference,
              tier,
            });
            if (result.status === "processing") {
              toast.info(
                "Payment processing — you will be upgraded shortly",
              );
            } else {
              toast.success(
                "Payment confirmed — your tier has been upgraded",
              );
              setCurrentTier(tier);
              router.push("/matches");
            }
          } catch (err) {
            toast.error(
              err instanceof Error ? err.message : "Payment verification failed",
            );
          } finally {
            setPayingTier(null);
          }
        },
        onClose: () => {
          console.log("[lenco-close]");
          toast.info("Payment cancelled");
          setPayingTier(null);
        },
        onConfirmationPending: () => {
          toast.info(
            "Payment processing — you will be upgraded shortly",
          );
        },
      });
    } catch (err) {
      console.error("[upgrade-click] failed", err);
      toast.error(
        err instanceof Error ? err.message : "Could not start checkout",
      );
      setPayingTier(null);
    }
  };

  const handlePlanClick = (tier: string) => {
    console.log("[plan-click]", tier, {
      isAuthenticated,
      authLoading,
      currentTier,
      lencoReady,
      action: planAction(tier),
    });

    if (tier === "free") {
      if (!isAuthenticated) router.push("/auth?next=/pricing");
      return;
    }

    const action = planAction(tier);
    if (action === "current") {
      toast.info("You are already on this plan.");
      return;
    }
    if (action === "downgrade") {
      toast.info("To downgrade, contact support or wait until your billing cycle ends.");
      return;
    }
    if (!isAuthenticated) {
      router.push("/auth?next=/pricing");
      return;
    }
    if (authLoading) {
      toast.info("Signing you in — try again in a moment.");
      return;
    }

    void startLencoPayment(tier);
  };

  return (
    <div className="max-w-[1280px] mx-auto px-6 py-12 md:py-20">
      <Script
        src={LENCO_WIDGET_URL}
        strategy="afterInteractive"
        onLoad={() => {
          console.log("[lenco-script] loaded");
          if (isLencoReady()) setLencoReady(true);
        }}
        onError={() => {
          console.error("[lenco-script] failed to load");
          toast.error("Payment widget failed to load. Refresh and try again.");
        }}
      />

      <div className="text-center mb-12 md:mb-16">
        <div className="eyebrow mb-3">Pricing</div>
        <h1
          className="font-display mb-3"
          style={{
            fontSize: "clamp(36px, 5vw, 60px)",
            letterSpacing: "-0.025em",
          }}
        >
          Simple,{" "}
          <span className="italic" style={{ color: "var(--copper-500)" }}>
            fair
          </span>{" "}
          pricing
        </h1>
        <p
          className="text-base"
          style={{ color: "var(--muted)", maxWidth: 480, margin: "0 auto" }}
        >
          Pay with MTN Mobile Money, Airtel Money, or card via our secure
          Lenco checkout. All prices in Zambian Kwacha.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 max-w-6xl mx-auto mb-16 md:mb-24">
        {displayPlans.map((plan) => {
          const action = planAction(plan.tier);
          const isCurrent = action === "current";
          const isDowngrade = action === "downgrade";
          const isPaying = payingTier === plan.tier;
          const isPaidTier = plan.tier !== "free";
          const checkoutBlocked = isPaidTier && !lencoReady && isAuthenticated;
          const label = isCurrent
            ? "Current plan"
            : isDowngrade
            ? `Downgrade to ${plan.name}`
            : plan.tier === "free"
            ? "Get Started"
            : checkoutBlocked
            ? "Loading checkout…"
            : `Upgrade to ${plan.name}`;

          return (
            <div
              key={plan.name}
              className={`card p-6 md:p-8 relative ${plan.highlight ? "lift" : ""}`}
              style={{
                borderColor: plan.highlight ? "var(--copper-500)" : undefined,
                borderWidth: plan.highlight ? 2 : undefined,
                background: plan.highlight
                  ? "linear-gradient(180deg, var(--copper-100) 0%, var(--surface) 40%)"
                  : undefined,
              }}
            >
              {plan.highlight && (
                <span className="absolute -top-3 left-1/2 -translate-x-1/2 tag tag-copper font-semibold">
                  {plan.subtitle}
                </span>
              )}

              <h2
                className="font-display text-2xl"
                style={{ letterSpacing: "-0.01em" }}
              >
                {plan.name}
              </h2>
              {!plan.highlight && (
                <p className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
                  {plan.subtitle}
                </p>
              )}

              <div className="mt-5 mb-6">
                <span className="font-display text-5xl">{plan.price}</span>
                <span className="text-sm ml-1" style={{ color: "var(--muted)" }}>
                  {plan.period}
                </span>
              </div>

              <ul className="space-y-3 mb-8">
                {plan.features.map((f) => (
                  <li
                    key={f}
                    className="flex items-start gap-2.5 text-sm"
                    style={{ color: "var(--ink-2)" }}
                  >
                    <span
                      className="mt-0.5 shrink-0"
                      style={{ color: "var(--green-500)" }}
                    >
                      <Icon name="check" size={14} />
                    </span>
                    {f}
                  </li>
                ))}
              </ul>

              <button
                type="button"
                onClick={() => handlePlanClick(plan.tier)}
                disabled={isCurrent || isPaying || checkoutBlocked}
                aria-disabled={isCurrent || checkoutBlocked}
                className={`w-full ${
                  isCurrent
                    ? "btn btn-ghost btn-lg"
                    : plan.highlight
                    ? "btn btn-accent btn-lg"
                    : "btn btn-ghost btn-lg"
                }`}
                style={
                  isCurrent || checkoutBlocked
                    ? { opacity: 0.7, cursor: "not-allowed" }
                    : undefined
                }
              >
                {isPaying ? (
                  <span className="spinner" />
                ) : (
                  <>
                    {isCurrent && <Icon name="check" size={14} />} {label}
                  </>
                )}
              </button>
            </div>
          );
        })}
      </div>

      <div className="max-w-4xl mx-auto mb-16 md:mb-24">
        <div className="text-center mb-8">
          <div className="eyebrow mb-2">Compare plans</div>
          <h2
            className="font-display text-3xl"
            style={{ letterSpacing: "-0.01em" }}
          >
            Feature comparison
          </h2>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr style={{ borderBottom: "1px solid var(--line)" }}>
                <th
                  className="text-left py-3 pr-4 font-medium"
                  style={{ color: "var(--muted)" }}
                >
                  Feature
                </th>
                <th className="py-3 px-4 text-center font-medium">Free</th>
                <th
                  className="py-3 px-4 text-center font-semibold"
                  style={{ color: "var(--copper-600)" }}
                >
                  Starter
                </th>
                <th className="py-3 px-4 text-center font-medium">
                  Professional
                </th>
                <th className="py-3 px-4 text-center font-medium">
                  Super Standard
                </th>
              </tr>
            </thead>
            <tbody>
              {comparisonFeatures.map((feat) => (
                <tr
                  key={feat.name}
                  style={{ borderBottom: "1px solid var(--line)" }}
                >
                  <td className="py-3 pr-4" style={{ color: "var(--ink-2)" }}>
                    {feat.name}
                  </td>
                  {(["free", "starter", "pro", "super_standard"] as const).map(
                    (tier) => {
                      const val = feat[tier];
                      return (
                        <td key={tier} className="py-3 px-4 text-center">
                          {typeof val === "boolean" ? (
                            val ? (
                              <Icon
                                name="check"
                                size={16}
                                className="mx-auto"
                              />
                            ) : (
                              <span style={{ color: "var(--muted-2)" }}>
                                &mdash;
                              </span>
                            )
                          ) : (
                            <span className="font-mono text-xs">{val}</span>
                          )}
                        </td>
                      );
                    },
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="max-w-2xl mx-auto mb-16">
        <div className="text-center mb-8">
          <div className="eyebrow mb-2">FAQ</div>
          <h2
            className="font-display text-3xl"
            style={{ letterSpacing: "-0.01em" }}
          >
            Common questions
          </h2>
        </div>

        <div className="space-y-2">
          {faqs.map((faq, i) => (
            <div key={i} className="card overflow-hidden">
              <button
                type="button"
                onClick={() => setOpenFaq(openFaq === i ? null : i)}
                className="w-full flex items-center justify-between p-5 text-left"
                style={{ background: "none", border: "none", cursor: "pointer" }}
              >
                <span className="font-medium text-sm">{faq.q}</span>
                <span
                  className="shrink-0 ml-4 transition-transform duration-200"
                  style={{
                    transform: openFaq === i ? "rotate(45deg)" : "rotate(0deg)",
                    color: "var(--muted)",
                  }}
                >
                  <Icon name="plus" size={16} />
                </span>
              </button>
              <div
                className="overflow-hidden transition-all duration-300"
                style={{ maxHeight: openFaq === i ? 200 : 0 }}
              >
                <p
                  className="px-5 pb-5 text-sm leading-relaxed"
                  style={{ color: "var(--ink-2)" }}
                >
                  {faq.a}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
