"use client";

import { useState, useRef, useEffect } from "react";
import { useRouter } from "next/navigation";
import { auth } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { z } from "zod";
import { Icon } from "@/components/ui/Icon";
import { Logo } from "@/components/ui/Logo";
import { ChevronMotif } from "@/components/ui/ChevronMotif";
import { ZambiaFlag } from "@/components/ui/ZambiaFlag";

const phoneSchema = z
  .string()
  .regex(/^\+260[0-9]{9}$/, "Enter a valid Zambian number");
const otpSchema = z.string().length(6, "OTP must be 6 digits");

export default function AuthPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [step, setStep] = useState<"phone" | "otp" | "success">("phone");
  const [phoneDigits, setPhoneDigits] = useState("");
  const [otp, setOtp] = useState(["", "", "", "", "", ""]);
  const [resendIn, setResendIn] = useState(30);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const otpRefs = useRef<(HTMLInputElement | null)[]>([]);

  const fullPhone = `+260${phoneDigits.replace(/\s/g, "")}`;

  // Resend countdown
  useEffect(() => {
    if (step !== "otp") return;
    setResendIn(30);
    const id = setInterval(
      () => setResendIn((r) => Math.max(0, r - 1)),
      1000
    );
    return () => clearInterval(id);
  }, [step]);

  const handlePhoneSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const result = phoneSchema.safeParse(fullPhone);
    if (!result.success) {
      setError("Enter a valid Zambian number (9 digits after +260)");
      return;
    }
    setError("");
    setLoading(true);
    try {
      await auth.requestOTP(fullPhone);
      setStep("otp");
      setTimeout(() => otpRefs.current[0]?.focus(), 50);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to send OTP");
    } finally {
      setLoading(false);
    }
  };

  const handleOtpChange = async (i: number, value: string) => {
    const val = value.replace(/\D/g, "").slice(-1);
    const next = [...otp];
    next[i] = val;
    setOtp(next);

    if (val && i < 5) otpRefs.current[i + 1]?.focus();

    if (next.every((d) => d !== "")) {
      const code = next.join("");
      const result = otpSchema.safeParse(code);
      if (!result.success) return;

      setLoading(true);
      setError("");
      try {
        const tokens = await auth.verifyOTP(fullPhone, code);
        login(tokens.access_token, tokens.user_id);
        setStep("success");
        setTimeout(() => router.push("/matches"), 1400);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Invalid OTP");
        setLoading(false);
      }
    }
  };

  const handleOtpKey = (i: number, e: React.KeyboardEvent) => {
    if (e.key === "Backspace" && !otp[i] && i > 0) {
      otpRefs.current[i - 1]?.focus();
    }
  };

  return (
    <main
      className="auth-grid"
      style={{
        minHeight: "calc(100vh - 70px)",
        display: "grid",
        gridTemplateColumns: "1.05fr 1fr",
      }}
    >
      {/* LEFT — brand panel */}
      <aside
        className="auth-aside relative overflow-hidden flex flex-col justify-between"
        style={{
          background:
            "linear-gradient(165deg, var(--green-800) 0%, var(--green-700) 60%, var(--copper-700) 130%)",
          color: "#faf7f2",
          padding: "72px 64px",
        }}
      >
        <div
          className="grain"
          style={{ position: "absolute", inset: 0, opacity: 0.6 }}
        />
        <div className="absolute -top-16 -right-16 opacity-30">
          <ChevronMotif w={400} h={300} />
        </div>

        <div className="relative z-10">
          <button
            onClick={() => router.push("/")}
            className="inline-flex items-center gap-2 text-sm opacity-85 hover:opacity-100 transition-opacity"
            style={{
              background: "none",
              border: "none",
              color: "inherit",
              cursor: "pointer",
            }}
          >
            <Icon name="arrowLeft" size={14} /> Back to home
          </button>
        </div>

        <div className="relative z-10">
          <div className="eyebrow" style={{ color: "rgba(255,255,255,0.65)" }}>
            Welcome back
          </div>
          <h1
            className="font-display my-3"
            style={{
              fontSize: "clamp(48px, 6vw, 80px)",
              lineHeight: 1,
              letterSpacing: "-0.02em",
            }}
          >
            Two taps.{" "}
            <span
              className="italic"
              style={{ color: "var(--copper-300)" }}
            >
              Zero passwords.
            </span>
          </h1>
          <p
            className="text-base leading-relaxed max-w-[420px]"
            style={{ opacity: 0.85 }}
          >
            Sign in with your Zambian phone number. We send a one-time code to
            your WhatsApp — no email, no password to forget.
          </p>

          <div className="mt-10 flex flex-col gap-3.5">
            {[
              ["shield", "End-to-end encrypted"],
              ["whatsapp", "WhatsApp verified — no SMS spam"],
              ["zap", "Average sign-in: 12 seconds"],
            ].map(([icon, text]) => (
              <div
                key={text}
                className="flex items-center gap-3 text-sm"
                style={{ opacity: 0.9 }}
              >
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center"
                  style={{
                    background: "rgba(255,255,255,0.12)",
                    color: "var(--copper-300)",
                  }}
                >
                  <Icon name={icon} size={14} />
                </div>
                {text}
              </div>
            ))}
          </div>
        </div>

        <div
          className="relative z-10 text-xs font-mono"
          style={{ opacity: 0.6 }}
        >
          ZED CV &middot; VERGEO &middot; LUSAKA &middot; 2026
        </div>
      </aside>

      {/* RIGHT — form */}
      <section
        className="flex items-center justify-center"
        style={{ padding: "72px 32px", background: "var(--bg)" }}
      >
        <div className="w-full max-w-[420px]">
          {/* Mobile logo */}
          <div className="show-mobile mb-10">
            <Logo size={28} />
          </div>

          {step === "phone" && (
            <div className="fade-up">
              <div className="eyebrow">Step 01 / 02</div>
              <h2
                className="font-display mt-2 mb-2"
                style={{ fontSize: 44, letterSpacing: "-0.02em" }}
              >
                Enter your number
              </h2>
              <p
                className="text-sm mb-8"
                style={{ color: "var(--muted)" }}
              >
                We&apos;ll WhatsApp you a 6-digit code.
              </p>

              <form onSubmit={handlePhoneSubmit}>
                <label
                  className="text-sm font-medium block mb-2"
                  style={{ color: "var(--ink-2)" }}
                >
                  Phone number
                </label>
                <div
                  className="flex items-stretch overflow-hidden"
                  style={{
                    border: error
                      ? "1px solid var(--danger)"
                      : "1px solid var(--line-2)",
                    borderRadius: "var(--r-sm)",
                    background: "var(--surface)",
                  }}
                >
                  <div
                    className="flex items-center gap-2 px-3.5 font-mono text-sm"
                    style={{
                      borderRight: "1px solid var(--line-2)",
                      color: "var(--ink-2)",
                      background: "var(--bg-2)",
                    }}
                  >
                    <ZambiaFlag />
                    +260
                  </div>
                  <input
                    type="tel"
                    value={phoneDigits}
                    onChange={(e) => setPhoneDigits(e.target.value)}
                    placeholder="97 123 4567"
                    className="flex-1 px-3.5 h-[52px] text-base bg-transparent outline-none"
                    style={{
                      border: "none",
                      color: "var(--ink)",
                    }}
                  />
                </div>
                {error && (
                  <div
                    className="mt-2 text-sm"
                    style={{ color: "var(--danger)" }}
                  >
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={loading}
                  className="btn btn-primary btn-lg w-full mt-6"
                >
                  {loading ? (
                    <span className="spinner" />
                  ) : (
                    <>
                      Send code <Icon name="arrowRight" size={16} />
                    </>
                  )}
                </button>
              </form>

              <div
                className="mt-6 text-center text-xs leading-relaxed"
                style={{ color: "var(--muted)" }}
              >
                By continuing, you agree to our{" "}
                <a href="#" style={{ color: "var(--ink-2)" }}>
                  Terms
                </a>{" "}
                and{" "}
                <a href="#" style={{ color: "var(--ink-2)" }}>
                  Privacy Policy
                </a>
                .
              </div>
            </div>
          )}

          {step === "otp" && (
            <div className="fade-up">
              <button
                onClick={() => {
                  setStep("phone");
                  setOtp(["", "", "", "", "", ""]);
                  setError("");
                }}
                className="inline-flex items-center gap-1.5 text-sm mb-4"
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--muted)",
                  cursor: "pointer",
                }}
              >
                <Icon name="arrowLeft" size={13} /> Change number
              </button>
              <div className="eyebrow">Step 02 / 02</div>
              <h2
                className="font-display mt-2 mb-2"
                style={{ fontSize: 44, letterSpacing: "-0.02em" }}
              >
                Enter the code
              </h2>
              <p
                className="text-sm mb-8"
                style={{ color: "var(--muted)" }}
              >
                Sent to{" "}
                <span className="font-mono" style={{ color: "var(--ink)" }}>
                  +260 {phoneDigits}
                </span>{" "}
                on WhatsApp.
              </p>

              <div className="grid grid-cols-6 gap-2.5">
                {otp.map((d, i) => (
                  <input
                    key={i}
                    ref={(el) => {
                      otpRefs.current[i] = el;
                    }}
                    value={d}
                    onChange={(e) => handleOtpChange(i, e.target.value)}
                    onKeyDown={(e) => handleOtpKey(i, e)}
                    inputMode="numeric"
                    maxLength={1}
                    aria-label={`Digit ${i + 1}`}
                    className="h-16 text-center font-display outline-none"
                    style={{
                      fontSize: 32,
                      border: d
                        ? "1px solid var(--green-500)"
                        : "1px solid var(--line-2)",
                      borderRadius: 12,
                      background: "var(--surface)",
                      color: "var(--ink)",
                      transition: "all 150ms ease",
                    }}
                  />
                ))}
              </div>

              {error && (
                <div
                  className="mt-3 text-sm"
                  style={{ color: "var(--danger)" }}
                >
                  {error}
                </div>
              )}

              <div className="mt-6 flex justify-between items-center">
                <span className="text-sm" style={{ color: "var(--muted)" }}>
                  {loading ? "Verifying..." : "Didn't receive it?"}
                </span>
                {!loading && (
                  <button
                    onClick={() => resendIn === 0 && setResendIn(30)}
                    disabled={resendIn > 0}
                    className="text-sm font-mono font-medium"
                    style={{
                      background: "none",
                      border: "none",
                      cursor: resendIn > 0 ? "default" : "pointer",
                      color:
                        resendIn > 0
                          ? "var(--muted)"
                          : "var(--green-700)",
                    }}
                  >
                    {resendIn > 0 ? `Resend in ${resendIn}s` : "Resend code"}
                  </button>
                )}
              </div>
            </div>
          )}

          {step === "success" && (
            <div className="fade-up text-center">
              <div
                className="w-20 h-20 mx-auto mb-6 rounded-full inline-flex items-center justify-center"
                style={{
                  background: "var(--green-100)",
                  color: "var(--green-700)",
                }}
              >
                <Icon name="check" size={36} />
              </div>
              <h2
                className="font-display mb-2"
                style={{ fontSize: 44, letterSpacing: "-0.02em" }}
              >
                Welcome back!
              </h2>
              <p className="text-sm" style={{ color: "var(--muted)" }}>
                Loading your matches...
              </p>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
