"use client";

import { Icon } from "@/components/ui/Icon";
import { Button } from "@/components/ui/button";
import { OtpField } from "@/components/shared/OtpField";
import { StepProgress } from "@/components/shared/StepProgress";
import type { OtpChannel } from "@/lib/api";

export interface OtpPageProps {
  phoneDigits: string;
  email: string;
  otpCode: string;
  otpChannel: OtpChannel;
  loading: boolean;
  error: string;
  resendIn: number;
  rememberDevice: boolean;
  onOtpChange: (code: string) => void;
  onRememberChange: (checked: boolean) => void;
  onBack: () => void;
  onResend: () => void;
}

export function OtpPage({
  phoneDigits,
  email,
  otpCode,
  otpChannel,
  loading,
  error,
  resendIn,
  rememberDevice,
  onOtpChange,
  onRememberChange,
  onBack,
  onResend,
}: OtpPageProps) {
  return (
    <div className="fade-up">
      <Button
        type="button"
        variant="ghost"
        size="sm"
        className="mb-4 h-auto min-h-0 px-0 text-muted-foreground"
        onClick={onBack}
      >
        <Icon name="arrowLeft" size={13} /> Change number
      </Button>
      <StepProgress current={2} total={2} labels={["Phone", "Verify code"]} className="mb-4" />
      <h2
        className="font-display mt-2 mb-2"
        style={{ fontSize: 44, letterSpacing: "-0.02em" }}
      >
        Enter the code
      </h2>
      <p className="text-sm mb-8" style={{ color: "var(--muted)" }}>
        {otpChannel === "email" ? (
          <>
            Sent to <span style={{ color: "var(--ink)" }}>{email.trim()}</span> by email.
          </>
        ) : (
          <>
            Sent to{" "}
            <span className="font-mono" style={{ color: "var(--ink)" }}>
              +260 {phoneDigits}
            </span>{" "}
            on WhatsApp.
          </>
        )}
      </p>

      <label
        className="mb-6 flex items-start gap-2.5 text-xs leading-relaxed cursor-pointer"
        style={{ color: "var(--muted)" }}
      >
        <input
          type="checkbox"
          checked={rememberDevice}
          onChange={(e) => onRememberChange(e.target.checked)}
          disabled={loading}
          className="cursor-pointer"
          style={{
            accentColor: "var(--green-700)",
            width: 16,
            height: 16,
            marginTop: 2,
            flexShrink: 0,
          }}
        />
        <span>Remember this device (skip verification code next time)</span>
      </label>

      <OtpField value={otpCode} onChange={onOtpChange} disabled={loading} error={error} />

      <div className="mt-6 flex justify-between items-center">
        <span className="text-sm" style={{ color: "var(--muted)" }}>
          {loading ? "Verifying..." : "Didn't receive it?"}
        </span>
        {!loading && (
          <button
            type="button"
            onClick={() => resendIn === 0 && onResend()}
            disabled={resendIn > 0}
            className="text-sm font-mono font-medium"
            style={{
              background: "none",
              border: "none",
              cursor: resendIn > 0 ? "default" : "pointer",
              color: resendIn > 0 ? "var(--muted)" : "var(--green-700)",
            }}
          >
            {resendIn > 0 ? `Resend in ${resendIn}s` : "Resend code"}
          </button>
        )}
      </div>
    </div>
  );
}
