"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import {
  isEligibleForPushPrompt,
  markMatchesPageVisited,
  recordPushDeclined,
  requestPushPermissionAndSubscribe,
} from "@/lib/pushNotifications";
import { notify } from "@/lib/toast";

type PushPermissionPromptProps = {
  creditedMatchCount: number;
};

/**
 * Soft prompt for Web Push — only after ≥1 credited match and first matches-page visit.
 * Never calls Notification.requestPermission on first site visit (parent gates mount).
 */
export function PushPermissionPrompt({ creditedMatchCount }: PushPermissionPromptProps) {
  const { token } = useAuth();
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    markMatchesPageVisited();
  }, []);

  useEffect(() => {
    setVisible(isEligibleForPushPrompt(creditedMatchCount));
  }, [creditedMatchCount]);

  const handleEnable = useCallback(async () => {
    if (!token || busy) return;
    setBusy(true);
    try {
      const result = await requestPushPermissionAndSubscribe(token);
      if (result === "granted") {
        notify.custom.success("Alerts on — we'll notify you about strong matches (85%+).");
        setVisible(false);
      } else if (result === "denied") {
        recordPushDeclined();
        setVisible(false);
      } else {
        notify.error("Push notifications aren't supported in this browser.");
      }
    } catch (e: unknown) {
      const message = e instanceof Error ? e.message : "Couldn't enable alerts.";
      notify.error(message);
    } finally {
      setBusy(false);
    }
  }, [token, busy]);

  const handleDecline = useCallback(() => {
    recordPushDeclined();
    setVisible(false);
  }, []);

  if (!visible) return null;

  return (
    <div
      className="mb-4 rounded-lg border border-[var(--border)] bg-[var(--surface-elevated)] p-4 shadow-sm"
      role="region"
      aria-label="Enable match alerts"
    >
      <p className="text-sm font-medium text-[var(--foreground)]">
        Get instant alerts for strong matches
      </p>
      <p className="mt-1 text-sm text-[var(--muted-foreground)]">
        We&apos;ll notify you on this device when a new job scores 85% or higher — no spam,
        only high-confidence matches.
      </p>
      <div className="mt-3 flex flex-wrap gap-2">
        <button
          type="button"
          className="rounded-md bg-[var(--primary)] px-3 py-1.5 text-sm font-medium text-[var(--primary-foreground)] disabled:opacity-60"
          onClick={() => void handleEnable()}
          disabled={busy}
        >
          {busy ? "Enabling…" : "Enable alerts"}
        </button>
        <button
          type="button"
          className="rounded-md border border-[var(--border)] px-3 py-1.5 text-sm text-[var(--foreground)]"
          onClick={handleDecline}
          disabled={busy}
        >
          Not now
        </button>
      </div>
    </div>
  );
}
