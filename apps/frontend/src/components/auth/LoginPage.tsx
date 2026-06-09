"use client";

import Link from "next/link";
import { Icon } from "@/components/ui/Icon";
import { Button } from "@/components/ui/button";
import { PhoneField } from "@/components/shared/PhoneField";
import { StepProgress } from "@/components/shared/StepProgress";
import type { OtpChannel } from "@/lib/api";

export interface LoginPageProps {
  fullName: string;
  phoneDigits: string;
  email: string;
  consentChecked: boolean;
  loading: boolean;
  error: string;
  otpChannel: OtpChannel;
  isFreeTier: boolean;
  onFullNameChange: (fullName: string) => void;
  onPhoneChange: (digits: string) => void;
  onEmailChange: (email: string) => void;
  onConsentChange: (checked: boolean) => void;
  onOtpChannelChange: (channel: OtpChannel) => void;
  onSubmit: (e: React.FormEvent) => void;
}

export function LoginPage({
  fullName = "",
  phoneDigits,
  email,
  consentChecked,
  loading,
  error,
  otpChannel,
  isFreeTier,
  onFullNameChange = () => {},
  onPhoneChange,
  onEmailChange,
  onConsentChange,
  onOtpChannelChange,
  onSubmit,
}: LoginPageProps) {
  return (
    <div className="fade-up">
      <StepProgress current={1} total={2} labels={["Phone", "Verify code"]} className="mb-4" />
      <h2
        className="font-display mt-2 mb-3"
        style={{
          fontSize: "clamp(2rem, 5vw, 2.75rem)",
          letterSpacing: "-0.02em",
          lineHeight: 1.05,
        }}
      >
        Enter your number
      </h2>
      <p className="text-sm mb-4 sm:mb-6 leading-relaxed" style={{ color: "var(--muted)" }}>
        We&apos;ll send a 6-digit code by email or WhatsApp. Your email receives daily match
        digests.
      </p>
      <p
        className="mb-6 sm:mb-8 flex items-center gap-2 text-xs"
        style={{ color: "var(--muted)" }}
      >
        <Icon name="shield" size={14} className="shrink-0 text-primary" aria-hidden />
        <span>
          Encrypted CV storage · no password to phish ·{" "}
          <Link href="/security" className="underline" style={{ color: "var(--green-700)" }}>
            Security overview
          </Link>
        </span>
      </p>

      <form onSubmit={onSubmit}>
        <label htmlFor="auth-fullname" className="mb-2 block text-sm font-medium text-ink-2">
          Your name
        </label>
        <input
          id="auth-fullname"
          type="text"
          required
          value={fullName}
          onChange={(e) => onFullNameChange(e.target.value)}
          disabled={loading}
          placeholder="e.g. Kaluba Musonda"
          className="field mb-1"
          style={{ height: 44 }}
        />
        <p className="text-xs text-muted-foreground mb-5">
          We use this to personalize your match alerts.
        </p>

        <label htmlFor="auth-phone" className="mb-2 block text-sm font-medium text-ink-2">
          Phone number
        </label>
        <PhoneField
          id="auth-phone"
          digits={phoneDigits}
          onDigitsChange={onPhoneChange}
          error={error}
          disabled={loading}
        />

        <label htmlFor="auth-email" className="mb-2 mt-5 block text-sm font-medium text-ink-2">
          Email address
        </label>
        <input
          id="auth-email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => onEmailChange(e.target.value)}
          disabled={loading}
          placeholder="you@example.com"
          className="field"
          style={{ height: 44 }}
        />

        {isFreeTier && (
          <fieldset className="mt-5">
            <legend className="mb-2 text-sm font-medium text-ink-2">Send code via</legend>
            <div className="flex flex-col gap-2 text-sm">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="otp-channel"
                  checked={otpChannel === "email"}
                  onChange={() => onOtpChannelChange("email")}
                  disabled={loading}
                />
                Email (default)
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="otp-channel"
                  checked={otpChannel === "whatsapp"}
                  onChange={() => onOtpChannelChange("whatsapp")}
                  disabled={loading}
                />
                WhatsApp
              </label>
            </div>
          </fieldset>
        )}

        <label
          className="mt-5 flex items-start gap-2.5 text-xs leading-relaxed cursor-pointer"
          style={{ color: "var(--muted)" }}
        >
          <input
            type="checkbox"
            checked={consentChecked}
            onChange={(e) => onConsentChange(e.target.checked)}
            className="cursor-pointer"
            style={{
              accentColor: "var(--green-700)",
              width: 16,
              height: 16,
              marginTop: 2,
              flexShrink: 0,
            }}
          />
          <span>
            I agree to the{" "}
            <Link
              href="/legal/terms"
              style={{ color: "var(--ink-2)", textDecoration: "underline" }}
            >
              Terms
            </Link>{" "}
            and acknowledge the{" "}
            <Link
              href="/legal/privacy"
              style={{ color: "var(--ink-2)", textDecoration: "underline" }}
            >
              Privacy Policy
            </Link>
            .
          </span>
        </label>

        <Button
          type="submit"
          variant="primary"
          size="lg"
          className="mt-6 w-full"
          loading={loading}
          disabled={!consentChecked || phoneDigits.length < 9 || !email.trim() || fullName.trim().length < 2}
        >
          Send code <Icon name="arrowRight" size={16} />
        </Button>
      </form>
    </div>
  );
}
