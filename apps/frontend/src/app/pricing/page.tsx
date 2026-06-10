"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Script from "next/script";
import { notify } from "@/lib/toast";
import { subscription, tiers, profile, type TierConfigRow } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Icon } from "@/components/ui/Icon";
import { Button } from "@/components/ui/button";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  formatMatchesLimit,
  formatPriceLabel,
  UNLIMITED_MATCHES,
} from "@/lib/tier-config";
import {
  getLencoPublicKey,
  getLencoScriptUrl,
  isLencoReady,
  lencoPhone,
  openLencoCheckout,
  setLencoMerchantLabel,
} from "@/lib/lenco";
import type { LencoPayOptions } from "@/types/lenco-pay";
import {
  buildTierComparisonFeatures,
  TIER_MARKETING_FEATURES,
  tierMatchesFaqAnswer,
  type TierComparisonFeature,
} from "@/lib/tier-marketing";
import { PricingSkeleton } from "@/components/shared/skeletons/PageSkeletons";
import { TrustSection } from "@/components/marketing/TrustSection";
import { surfaceCardClass } from "@/lib/cn-ui";
import { cn } from "@/lib/utils";

const LENCO_SCRIPT_URL = getLencoScriptUrl();

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
    features: TIER_MARKETING_FEATURES.free,
    highlight: false,
  },
  {
    name: "Starter",
    subtitle: "Most Popular",
    price: "K125",
    period: "/month",
    tier: "starter",
    features: TIER_MARKETING_FEATURES.starter,
    highlight: true,
  },
  {
    name: "Professional",
    subtitle: "For power users",
    price: "K250",
    period: "/month",
    tier: "professional",
    features: TIER_MARKETING_FEATURES.professional,
    highlight: false,
  },
  {
    name: "Super Standard",
    subtitle: "Top tier",
    price: "K500",
    period: "/month",
    tier: "super_standard",
    features: TIER_MARKETING_FEATURES.super_standard,
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
    a: tierMatchesFaqAnswer(),
  },
  {
    q: "Is my CV data secure?",
    a: "Absolutely. Your CV is encrypted at rest and in transit. We never share your personal data with employers without your explicit consent.",
  },
];

function applyTierConfig(base: Plan[], config: TierConfigRow[], period: 30 | 365 = 30): Plan[] {
  const byTier = Object.fromEntries(config.filter((t) => t.billing_period_days === period || (t.tier === "free" && t.billing_period_days === 30)).map((t) => [t.tier, t]));
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
      period: plan.tier === "free" ? "forever" : period === 365 ? "/year" : "/month",
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

export default function PricingPage() {
  const router = useRouter();
  const { token, user, isAuthenticated, isLoading: authLoading } = useAuth();
  const [displayPlans, setDisplayPlans] = useState<Plan[]>(plans);
  const [tierRows, setTierRows] = useState<TierConfigRow[]>([]);
  const [comparisonFeatures, setComparisonFeatures] = useState<TierComparisonFeature[]>(
    () => buildTierComparisonFeatures(),
  );
  const [payingTier, setPayingTier] = useState<string | null>(null);
  const [currentTier, setCurrentTier] = useState<string>("free");
  const [billingPeriod, setBillingPeriod] = useState<30 | 365>(30);
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
      .list(token ?? undefined)
      .then((r) => {
        setTierRows(r.tiers);
        setDisplayPlans(applyTierConfig(plans, r.tiers, billingPeriod));
        setComparisonFeatures(buildTierComparisonFeatures(r.tiers));
      })
      .catch(() => {
        setDisplayPlans(plans);
        setComparisonFeatures(buildTierComparisonFeatures());
      });
  }, [token, billingPeriod]);

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
      const row = tierRows.find((t) => t.tier === tier && (t.billing_period_days === billingPeriod || tier === "free"));
      if (row) {
        const ngwee = row.checkout_price_ngwee ?? row.price_ngwee;
        return ngwee / 100;
      }
      const fallback: Record<string, number> = {
        starter: 125,
        professional: 250,
        super_standard: 500,
      };
      return fallback[tier] ?? 0;
    },
    [tierRows, billingPeriod],
  );

  const showPromoBadge = useCallback(
    (tier: string): boolean => {
      if (tier === "free") return false;
      const row = tierRows.find((t) => t.tier === tier && t.billing_period_days === billingPeriod);
      return row?.promotion_active === true;
    },
    [tierRows, billingPeriod],
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
    if (!token || !user?.id) {
      router.push("/auth?next=/pricing");
      return;
    }

    const publicKey = getLencoPublicKey();
    if (!publicKey) {
      notify.error("Payments are not configured. Please try again later.");
      return;
    }

    if (!isLencoReady()) {
      notify.error("Payment widget is loading — please wait a moment and try again.");
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
      if (!Number.isFinite(amount) || amount <= 0) {
        notify.error("Invalid plan amount. Please refresh and try again.");
        setPayingTier(null);
        return;
      }

      setLencoMerchantLabel("ZedApply");

      const checkout: LencoPayOptions = {
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
          try {
            const result = await subscription.verifyPayment(token, {
              reference: response.reference,
              tier,
              billing_period_days: billingPeriod,
            });
            if (result.status === "processing") {
              notify.info(
                "Payment processing — you will be upgraded shortly",
              );
            } else {
              notify.custom.success(
                "Payment confirmed — your tier has been upgraded",
              );
              setCurrentTier(tier);
              router.push("/matches");
            }
          } catch (err) {
            notify.error(
              err instanceof Error ? err.message : "Payment verification failed",
            );
          } finally {
            setPayingTier(null);
          }
        },
        onClose: () => {
          notify.info("Payment cancelled");
          setPayingTier(null);
        },
        onConfirmationPending: () => {
          notify.info(
            "Payment processing — you will be upgraded shortly",
          );
        },
      };

      openLencoCheckout(checkout);
    } catch (err) {
      console.error("[upgrade-click] failed", err);
      notify.error(
        err instanceof Error ? err.message : "Could not start checkout",
      );
      setPayingTier(null);
    }
  };

  const handlePlanClick = (tier: string) => {
    if (tier === "free") {
      if (!isAuthenticated) router.push("/auth?next=/pricing");
      return;
    }

    const action = planAction(tier);
    if (action === "current") {
      notify.info("You are already on this plan.");
      return;
    }
    if (action === "downgrade") {
      notify.info("To downgrade, contact support or wait until your billing cycle ends.");
      return;
    }
    if (!isAuthenticated) {
      router.push("/auth?next=/pricing");
      return;
    }
    if (authLoading) {
      notify.info("Signing you in — try again in a moment.");
      return;
    }

    void startLencoPayment(tier);
  };

  return (
    <div className="max-w-[1280px] mx-auto px-6 py-12 md:py-20">
      <Script
        src={LENCO_SCRIPT_URL}
        strategy="afterInteractive"
        onLoad={() => {
          if (isLencoReady()) setLencoReady(true);
        }}
        onError={() => {
          console.error("[lenco-script] failed to load");
          notify.error("Payment widget failed to load. Refresh and try again.");
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
        {/*
          The first-month 50% welcome promo only applies to MONTHLY tiers
          (PR #306 deliberately skips it for annual rows so we never stack
          a second discount on top of the long-commit annual sticker).
          Hide the banner on the Yearly tab so users aren't misled into
          expecting K525 at first checkout for an annual plan.
        */}
        {billingPeriod === 30 ? (
          <div
            className="mt-6 mx-auto max-w-2xl rounded-lg px-4 py-3 text-sm font-medium"
            style={{
              background: "color-mix(in srgb, var(--copper-500) 12%, transparent)",
              border: "1px solid var(--copper-500)",
              color: "var(--ink)",
            }}
            role="status"
          >
            First month: 50% off for paid tiers, 7 free matches/month for Free
          </div>
        ) : (
          <div
            className="mt-6 mx-auto max-w-2xl rounded-lg px-4 py-3 text-sm font-medium"
            style={{
              background: "color-mix(in srgb, var(--green-500, #2F7D3A) 10%, transparent)",
              border: "1px solid var(--green-500, #2F7D3A)",
              color: "var(--ink)",
            }}
            role="status"
          >
            Pay annually and save 30% — locks in a full year at today&apos;s price.
          </div>
        )}
        <div className="mt-8 flex justify-center">
          <div className="inline-flex items-center rounded-full border p-1" style={{ borderColor: "var(--line)", background: "var(--surface)" }}>
            <button
              onClick={() => setBillingPeriod(30)}
              className={`px-6 py-2 rounded-full text-sm font-medium transition-colors ${billingPeriod === 30 ? "bg-[var(--ink)] text-[var(--surface)] shadow-sm" : "text-[var(--muted)] hover:text-[var(--ink)]"}`}
            >
              Monthly
            </button>
            <button
              onClick={() => setBillingPeriod(365)}
              className={`px-6 py-2 rounded-full text-sm font-medium transition-colors flex items-center gap-2 ${billingPeriod === 365 ? "bg-[var(--ink)] text-[var(--surface)] shadow-sm" : "text-[var(--muted)] hover:text-[var(--ink)]"}`}
            >
              Yearly <span className="text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider" style={{ background: "var(--copper-500)", color: "#fff" }}>Save 30%</span>
            </button>
          </div>
        </div>
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
                {showPromoBadge(plan.tier) && (
                  <span
                    className="tag tag-copper text-xs font-semibold mb-2 inline-block"
                  >
                    First month: 50% off
                  </span>
                )}
                <div>
                  <span className="font-display text-5xl">{plan.price}</span>
                  <span className="text-sm ml-1" style={{ color: "var(--muted)" }}>
                    {plan.period}
                  </span>
                </div>
                {showPromoBadge(plan.tier) && (
                  <p className="text-xs mt-1" style={{ color: "var(--copper-600)" }}>
                    You pay K{amountKwacha(plan.tier)} at checkout while your launch
                    discount is active.
                  </p>
                )}
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

              <Button
                type="button"
                onClick={() => handlePlanClick(plan.tier)}
                disabled={isCurrent || isPaying || checkoutBlocked}
                variant={isCurrent ? "outline" : plan.highlight ? "accent" : "outline"}
                size="lg"
                className="w-full"
                loading={isPaying}
              >
                {isCurrent && <Icon name="check" size={14} />} {label}
              </Button>
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

      <TrustSection className="mb-16 md:mb-24" />

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

        <Accordion className="space-y-2">
          {faqs.map((faq, i) => (
            <AccordionItem key={faq.q} value={`faq-${i}`} className={cn(surfaceCardClass, "px-0")}>
              <AccordionTrigger className="px-5 py-4 text-left text-sm font-medium hover:no-underline">
                {faq.q}
              </AccordionTrigger>
              <AccordionContent className="px-5 pb-5 text-sm leading-relaxed text-muted-foreground">
                {faq.a}
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      </div>
    </div>
  );
}
