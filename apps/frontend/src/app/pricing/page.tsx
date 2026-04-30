"use client";

import { useState } from "react";
import { subscription } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Icon } from "@/components/ui/Icon";

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
      "5 job matches per month",
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
      "25 job matches per month",
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
      "Unlimited job matches",
      "AI cover letter generation",
      "Career coaching insights",
      "Priority support",
      "CV rewriting per role",
      "Everything in Starter",
    ],
    highlight: false,
  },
];

const faqs = [
  {
    q: "How does mobile money payment work?",
    a: "After selecting a plan, you'll enter your MTN MoMo or Airtel Money number. You'll receive a prompt on your phone to confirm the payment. Once confirmed, your account is upgraded instantly.",
  },
  {
    q: "Can I switch plans at any time?",
    a: "Yes! Upgrade or downgrade anytime. When upgrading, you'll be charged the difference. When downgrading, the change takes effect at the end of your billing cycle.",
  },
  {
    q: "What counts as a 'match'?",
    a: "Each time our AI scores your CV against a job listing and delivers the result to you (via WhatsApp or dashboard), that counts as one match. The Free tier includes 5 per month.",
  },
  {
    q: "Is my CV data secure?",
    a: "Absolutely. Your CV is encrypted at rest and in transit. We never share your personal data with employers without your explicit consent.",
  },
];

const comparisonFeatures = [
  { name: "Job matches / month", free: "5", starter: "25", pro: "Unlimited" },
  { name: "WhatsApp alerts", free: true, starter: true, pro: true },
  { name: "CV analysis", free: "Basic", starter: "Advanced", pro: "Advanced" },
  { name: "Tailored CVs", free: false, starter: true, pro: true },
  { name: "Cover letters", free: false, starter: false, pro: true },
  { name: "Score breakdowns", free: false, starter: true, pro: true },
  { name: "CV rewriting per role", free: false, starter: false, pro: true },
  { name: "Priority support", free: false, starter: false, pro: true },
];

type PaymentMethod = "mtn" | "airtel" | "card";

export default function PricingPage() {
  const { token, isAuthenticated } = useAuth();
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("mtn");
  const [payPhone, setPayPhone] = useState("");
  const [paying, setPaying] = useState(false);
  const [payMsg, setPayMsg] = useState("");
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  const handlePay = async (tier: string) => {
    if (!isAuthenticated || !token) {
      window.location.href = "/auth";
      return;
    }
    if (tier === "free") return;
    setSelectedPlan(tier);
  };

  const submitPayment = async () => {
    if (!token || !selectedPlan) return;
    setPaying(true);
    setPayMsg("");
    try {
      const res = await subscription.pay(token, {
        tier: selectedPlan,
        payment_method: paymentMethod,
        phone: `+260${payPhone.replace(/\s/g, "")}`,
      });
      setPayMsg(`Payment initiated! ${res.message}`);
      setSelectedPlan(null);
    } catch (err) {
      setPayMsg(err instanceof Error ? err.message : "Payment failed");
    } finally {
      setPaying(false);
    }
  };

  return (
    <div className="max-w-[1280px] mx-auto px-6 py-12 md:py-20">
      {/* Header */}
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
        <p className="text-base" style={{ color: "var(--muted)", maxWidth: 480, margin: "0 auto" }}>
          Pay with MTN Mobile Money or Airtel Money. All prices in Zambian
          Kwacha. No hidden fees.
        </p>
      </div>

      {/* Plan cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto mb-16 md:mb-24">
        {plans.map((plan) => (
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
              <span
                className="absolute -top-3 left-1/2 -translate-x-1/2 tag tag-copper font-semibold"
              >
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
              onClick={() => handlePay(plan.tier)}
              className={`w-full ${
                plan.highlight
                  ? "btn btn-accent btn-lg"
                  : "btn btn-ghost btn-lg"
              }`}
            >
              {plan.tier === "free"
                ? "Get Started"
                : `Upgrade to ${plan.name}`}
            </button>
          </div>
        ))}
      </div>

      {/* Comparison table */}
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
                <th className="text-left py-3 pr-4 font-medium" style={{ color: "var(--muted)" }}>
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
                  {(["free", "starter", "pro"] as const).map((tier) => {
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
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* FAQ */}
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
            <div
              key={i}
              className="card overflow-hidden"
            >
              <button
                onClick={() => setOpenFaq(openFaq === i ? null : i)}
                className="w-full flex items-center justify-between p-5 text-left"
                style={{ background: "none", border: "none", cursor: "pointer" }}
              >
                <span className="font-medium text-sm">{faq.q}</span>
                <span
                  className="shrink-0 ml-4 transition-transform duration-200"
                  style={{
                    transform:
                      openFaq === i ? "rotate(45deg)" : "rotate(0deg)",
                    color: "var(--muted)",
                  }}
                >
                  <Icon name="plus" size={16} />
                </span>
              </button>
              <div
                className="overflow-hidden transition-all duration-300"
                style={{
                  maxHeight: openFaq === i ? 200 : 0,
                }}
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

      {/* Payment Modal */}
      {selectedPlan && (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
          <div
            className="fixed inset-0"
            style={{ background: "rgba(0,0,0,0.5)", backdropFilter: "blur(4px)" }}
            onClick={() => {
              setSelectedPlan(null);
              setPayMsg("");
            }}
          />
          <div
            className="relative z-10 w-full max-w-md rounded-t-2xl sm:rounded-2xl p-6 md:p-8"
            style={{
              background: "var(--surface)",
              boxShadow: "var(--shadow-lg)",
            }}
          >
            <h3
              className="font-display text-2xl mb-6"
              style={{ letterSpacing: "-0.01em" }}
            >
              Pay for {plans.find((p) => p.tier === selectedPlan)?.name}
            </h3>

            <div className="space-y-5">
              {/* Payment methods */}
              <div>
                <label className="eyebrow block mb-3">Payment method</label>
                <div className="grid grid-cols-3 gap-3">
                  {[
                    { key: "mtn" as const, label: "MTN MoMo", color: "#ffcc00" },
                    { key: "airtel" as const, label: "Airtel Money", color: "#e40000" },
                    { key: "card" as const, label: "Visa / MC", color: "#1a1f71" },
                  ].map((method) => (
                    <button
                      key={method.key}
                      onClick={() => setPaymentMethod(method.key)}
                      className="card p-3 text-center text-xs font-medium"
                      style={{
                        borderColor:
                          paymentMethod === method.key
                            ? method.color
                            : "var(--line)",
                        borderWidth: paymentMethod === method.key ? 2 : 1,
                      }}
                    >
                      <div
                        className="w-5 h-5 rounded-full mx-auto mb-1.5"
                        style={{ background: method.color }}
                      />
                      {method.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Phone input */}
              <div>
                <label className="text-sm font-medium block mb-2" style={{ color: "var(--ink-2)" }}>
                  {paymentMethod === "card"
                    ? "Card number"
                    : "Mobile Money Number"}
                </label>
                <div
                  className="flex items-center overflow-hidden"
                  style={{
                    border: "1px solid var(--line-2)",
                    borderRadius: "var(--r-sm)",
                    background: "var(--surface)",
                  }}
                >
                  {paymentMethod !== "card" && (
                    <span
                      className="px-3 font-mono text-sm"
                      style={{
                        borderRight: "1px solid var(--line-2)",
                        background: "var(--bg-2)",
                        color: "var(--ink-2)",
                        height: 48,
                        display: "flex",
                        alignItems: "center",
                      }}
                    >
                      +260
                    </span>
                  )}
                  <input
                    type="tel"
                    value={payPhone}
                    onChange={(e) => setPayPhone(e.target.value)}
                    placeholder={
                      paymentMethod === "card"
                        ? "Card number"
                        : "97 123 4567"
                    }
                    className="flex-1 px-3 h-12 bg-transparent outline-none text-base"
                    style={{ border: "none", color: "var(--ink)" }}
                  />
                </div>
              </div>

              {payMsg && (
                <p
                  className="text-sm"
                  style={{
                    color: payMsg.includes("failed")
                      ? "var(--danger)"
                      : "var(--success)",
                  }}
                >
                  {payMsg}
                </p>
              )}

              <div className="flex gap-3">
                <button
                  onClick={() => {
                    setSelectedPlan(null);
                    setPayMsg("");
                  }}
                  className="btn btn-ghost flex-1"
                >
                  Cancel
                </button>
                <button
                  onClick={submitPayment}
                  disabled={paying}
                  className="btn btn-primary flex-1"
                >
                  {paying ? (
                    <span className="spinner" />
                  ) : (
                    <>
                      Pay{" "}
                      {plans.find((p) => p.tier === selectedPlan)?.price}
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
