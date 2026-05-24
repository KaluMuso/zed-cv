"use client";

import { useCallback, useEffect, useState } from "react";
import { auth } from "@/lib/api";
import { OTPInput } from "@/components/features/OTPInput";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Loader2 } from "lucide-react";

type Props = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  phone: string;
  title: string;
  description: string;
  onVerified: (otpCode: string) => Promise<void>;
};

export function SensitiveActionOtpDialog({
  open,
  onOpenChange,
  phone,
  title,
  description,
  onVerified,
}: Props) {
  const [otp, setOtp] = useState("");
  const [sending, setSending] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  useEffect(() => {
    if (!open) {
      setOtp("");
      setError(null);
      setSent(false);
    }
  }, [open]);

  const sendOtp = useCallback(async () => {
    setSending(true);
    setError(null);
    try {
      await auth.requestOTP(phone);
      setSent(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not send OTP");
    } finally {
      setSending(false);
    }
  }, [phone]);

  useEffect(() => {
    if (open && phone && !sent) {
      void sendOtp();
    }
  }, [open, phone, sent, sendOtp]);

  const submit = async () => {
    if (otp.length !== 6) return;
    setSubmitting(true);
    setError(null);
    try {
      await onVerified(otp);
      onOpenChange(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Verification failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{description}</DialogDescription>
        </DialogHeader>
        <p className="text-xs text-muted-foreground">
          We sent a 6-digit code to {phone}. Sensitive actions always require a fresh OTP, even on
          a remembered device.
        </p>
        <OTPInput value={otp} onChange={setOtp} disabled={submitting} aria-label="Sensitive action OTP" />
        {error && <p className="text-sm text-destructive">{error}</p>}
        <DialogFooter className="gap-2 sm:gap-0">
          <Button type="button" variant="outline" onClick={() => void sendOtp()} disabled={sending}>
            {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : "Resend code"}
          </Button>
          <Button type="button" onClick={() => void submit()} disabled={otp.length !== 6 || submitting}>
            {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Confirm"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
