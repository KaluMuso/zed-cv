"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  auth,
  clearStoredReferralRef,
  DEVICE_TOKEN_KEY,
  readStoredReferralRef,
  REFERRAL_STORAGE_KEY,
  type OtpChannel,
  ApiError,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { z } from "zod";
import { Icon } from "@/components/ui/Icon";
import { Logo } from "@/components/ui/Logo";
import { ChevronMotif } from "@/components/ui/ChevronMotif";
import { LoginPage } from "@/components/auth/LoginPage";
import { OtpPage } from "@/components/auth/OtpPage";

const phoneSchema = z
  .string()
  .regex(/^\+260[0-9]{9}$/, "Enter a valid Zambian number");
const emailSchema = z.string().email("Enter a valid email address");
const otpSchema = z.string().length(6, "OTP must be 6 digits");

export default function AuthPageClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, isAuthenticated, isLoading: authLoading } = useAuth();
  const [step, setStep] = useState<"phone" | "otp" | "success">("phone");
  const [phoneDigits, setPhoneDigits] = useState("");
  const [email, setEmail] = useState("");
  const [otpCode, setOtpCode] = useState("");
  const [resendIn, setResendIn] = useState(30);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [consentChecked, setConsentChecked] = useState(false);
  const [rememberDevice, setRememberDevice] = useState(true);
  const [otpChannel, setOtpChannel] = useState<OtpChannel>("email");
  const [userTier, setUserTier] = useState<string | null>(null);
  const [trustedLogin, setTrustedLogin] = useState(false);

  const fullPhone = `+260${phoneDigits.replace(/\s/g, "")}`;
  const isFreeTier =
    userTier === null || userTier === "free" || userTier === undefined;

  const handleOtpRequestError = useCallback((err: unknown) => {
    if (err instanceof ApiError) {
      if (err.code?.startsWith("email_") && isFreeTier) {
        setOtpChannel("whatsapp");
      }
      setError(err.detail);
      return;
    }
    setError(err instanceof Error ? err.message : "Failed to send OTP");
  }, [isFreeTier]);

  // Where to send the user after sign-in. `?next=/path` (set by pages
  // that redirected here on 401) wins; otherwise we drop them on
  // /matches. Guard against open-redirect by requiring the next param
  // to be a same-origin relative path (starts with `/`, no `//`).
  const rawNext = searchParams?.get("next") || "";
  const safeNext =
    rawNext.startsWith("/") && !rawNext.startsWith("//") ? rawNext : "/matches";

  // Preserve referral attribution until OTP verify sends it to the backend.
  useEffect(() => {
    const ref = searchParams?.get("ref")?.trim();
    if (!ref) return;
    try {
      sessionStorage.setItem(REFERRAL_STORAGE_KEY, ref);
    } catch {
      /* private mode */
    }
  }, [searchParams]);

  // Redirect if already authenticated
  useEffect(() => {
    if (!authLoading && isAuthenticated) {
      router.replace(safeNext);
    }
  }, [authLoading, isAuthenticated, router, safeNext]);

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
    if (!consentChecked) return;
    const phoneResult = phoneSchema.safeParse(fullPhone);
    const emailResult = emailSchema.safeParse(email.trim());
    if (!phoneResult.success) {
      setError("Enter a valid Zambian number (9 digits after +260)");
      return;
    }
    if (!emailResult.success) {
      setError(emailResult.error.issues[0]?.message ?? "Enter a valid email");
      return;
    }
    setError("");
    setLoading(true);
    try {
      try {
        const tokens = await auth.login(fullPhone);
        if (tokens.device_token) {
          localStorage.setItem(DEVICE_TOKEN_KEY, tokens.device_token);
        }
        login(tokens.access_token, tokens.user_id);
        setTrustedLogin(!!tokens.trusted_device_login);
        setStep("success");
        setTimeout(() => router.push(safeNext), tokens.trusted_device_login ? 800 : 1400);
        return;
      } catch (loginErr) {
        if (!(loginErr instanceof ApiError) || loginErr.status !== 401) {
          throw loginErr;
        }
      }

      const channel = isFreeTier ? otpChannel : "whatsapp";
      const otpResp = await auth.requestOTP(fullPhone, channel);
      if (otpResp.tier) {
        setUserTier(otpResp.tier);
      }
      if (otpResp.default_channel === "email" || otpResp.default_channel === "whatsapp") {
        setOtpChannel(otpResp.default_channel);
      }
      setStep("otp");
      setOtpCode("");
    } catch (err) {
      handleOtpRequestError(err);
    } finally {
      setLoading(false);
    }
  };

  const handleResendOtp = useCallback(async () => {
    if (resendIn > 0 || loading) return;
    setError("");
    setLoading(true);
    try {
      const channel = isFreeTier ? otpChannel : "whatsapp";
      await auth.requestOTP(fullPhone, channel);
      setResendIn(30);
      setOtpCode("");
    } catch (err) {
      handleOtpRequestError(err);
    } finally {
      setLoading(false);
    }
  }, [fullPhone, handleOtpRequestError, isFreeTier, loading, otpChannel, resendIn]);

  const verifyOtp = useCallback(
    async (code: string) => {
      const result = otpSchema.safeParse(code);
      if (!result.success) return;

      setLoading(true);
      setError("");
      try {
        const tokens = await auth.verifyOTP(fullPhone, code, {
          consentAccepted: consentChecked,
          email: email.trim(),
          rememberDevice,
          referralRef: readStoredReferralRef(),
        });
        if (tokens.device_token) {
          localStorage.setItem(DEVICE_TOKEN_KEY, tokens.device_token);
        }
        clearStoredReferralRef();
        login(tokens.access_token, tokens.user_id);
        setStep("success");
        setTimeout(() => router.push(safeNext), 1400);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Invalid OTP");
        setLoading(false);
      }
    },
    [consentChecked, email, fullPhone, login, rememberDevice, router, safeNext]
  );

  useEffect(() => {
    if (step !== "otp" || otpCode.length !== 6 || loading) return;
    void verifyOtp(otpCode);
  }, [otpCode, step, loading, verifyOtp]);

  return (
    <main className="auth-grid w-full max-w-7xl mx-auto">
      {/* LEFT — brand panel */}
      <aside
        className="auth-aside relative overflow-hidden flex flex-col justify-between"
        style={{
          background:
            "linear-gradient(165deg, var(--green-800) 0%, var(--green-700) 60%, var(--copper-700) 130%)",
          color: "#faf7f2",
          padding: "clamp(2rem, 6vw, 4.5rem) clamp(1.5rem, 5vw, 4rem)",
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

          <div className="mt-10 flex flex-col gap-4">
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
          ZED APPLY &middot; VERGEO &middot; LUSAKA &middot; 2026
        </div>
      </aside>

      {/* RIGHT — form */}
      <section
        className="auth-form-panel flex items-center justify-center"
        style={{ background: "var(--bg)" }}
      >
        <div className="w-full max-w-[420px] px-1">
          {/* Mobile logo */}
          <div className="show-mobile mb-10">
            <Logo size={28} />
          </div>

          {step === "phone" && (
            <LoginPage
              phoneDigits={phoneDigits}
              email={email}
              consentChecked={consentChecked}
              loading={loading}
              error={error}
              otpChannel={otpChannel}
              isFreeTier={isFreeTier}
              onPhoneChange={setPhoneDigits}
              onEmailChange={setEmail}
              onConsentChange={setConsentChecked}
              onOtpChannelChange={setOtpChannel}
              onSubmit={handlePhoneSubmit}
            />
          )}

          {step === "otp" && (
            <OtpPage
              phoneDigits={phoneDigits}
              email={email}
              otpCode={otpCode}
              otpChannel={otpChannel}
              loading={loading}
              error={error}
              resendIn={resendIn}
              rememberDevice={rememberDevice}
              onOtpChange={setOtpCode}
              onRememberChange={setRememberDevice}
              onBack={() => {
                setStep("phone");
                setOtpCode("");
                setError("");
              }}
              onResend={() => void handleResendOtp()}
            />
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
                {trustedLogin ? "Welcome back!" : "You're in!"}
              </h2>
              <p className="text-sm" style={{ color: "var(--muted)" }}>
                {trustedLogin
                  ? "Signed in on this trusted device — no code needed."
                  : "Loading your matches..."}
              </p>
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
