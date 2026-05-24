"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import {
  autoMatchPreferences,
  userPreferences,
  type AutoMatchPreferences,
  type PreferredNotificationChannel,
  type UserPreferences,
} from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { notify } from "@/lib/toast";
import { Loader2 } from "lucide-react";

const CHANNEL_OPTIONS: { value: PreferredNotificationChannel; label: string; hint: string }[] = [
  { value: "email", label: "Email only", hint: "Daily digests to your inbox (default)." },
  {
    value: "whatsapp",
    label: "WhatsApp only",
    hint: "Starter plan or higher. Requires a verified WhatsApp number.",
  },
  { value: "both", label: "Email and WhatsApp", hint: "Starter plan or higher." },
];

export default function SettingsPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading, token } = useAuth();
  const [dashPrefs, setDashPrefs] = useState<UserPreferences | null>(null);
  const [autoPrefs, setAutoPrefs] = useState<AutoMatchPreferences | null>(null);
  const [prefsLoading, setPrefsLoading] = useState(true);
  const [savingChannel, setSavingChannel] = useState(false);
  const [savingAutoMatch, setSavingAutoMatch] = useState(false);
  useEffect(() => {
    if (isLoading) {
      return;
    }
    if (!isAuthenticated || !token) {
      router.push("/auth");
      return;
    }
    Promise.allSettled([userPreferences.get(token), autoMatchPreferences.get(token)])
      .then(([dashRes, autoRes]) => {
        if (dashRes.status === "fulfilled") setDashPrefs(dashRes.value);
        if (autoRes.status === "fulfilled") setAutoPrefs(autoRes.value);
        if (dashRes.status === "rejected") throw dashRes.reason;
      })
      .catch((e) => notify.error(e instanceof Error ? e.message : "Failed to load preferences"))
      .finally(() => setPrefsLoading(false));
  }, [isAuthenticated, isLoading, router, token]);

  if (isLoading || !isAuthenticated) {
    return <p className="text-sm text-muted-foreground">…</p>;
  }

  const updateChannel = async (next: PreferredNotificationChannel) => {
    if (!token || !dashPrefs) {
      return;
    }
    if (!dashPrefs.whatsapp_digest_available && next !== "email") {
      notify.error("Upgrade to Starter or higher for WhatsApp digests.");
      return;
    }
    setSavingChannel(true);
    try {
      const r = await userPreferences.patch(token, { preferred_notification_channel: next });
      setDashPrefs(r);
      notify.custom.success("Notification preference saved.");
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Could not save");
    } finally {
      setSavingChannel(false);
    }
  };

  const updateAutoMatch = async (next: boolean) => {
    if (!token) {
      return;
    }
    setSavingAutoMatch(true);
    try {
      const r = await autoMatchPreferences.patch(token, { auto_match_enabled: next });
      setAutoPrefs(r);
      notify.custom.success(next ? "Auto-match enabled." : "Auto-match disabled.");
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Could not save");
    } finally {
      setSavingAutoMatch(false);
    }
  };

  const channel = dashPrefs?.preferred_notification_channel ?? "email";
  const paidWhatsApp = dashPrefs?.whatsapp_digest_available ?? false;

  return (
    <div>
      <h1 className="text-2xl sm:text-3xl font-bold mb-2">Settings</h1>
      <p className="text-muted-foreground text-sm mb-6">How ZedApply reaches you and account safety.</p>

      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Account &amp; privacy</CardTitle>
          <CardDescription>Data export, scheduled deletion, and consent preferences (ZDPA).</CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-2 sm:flex-row">
          <Link
            href="/settings/account"
            className={cn(buttonVariants({ variant: "outline" }))}
          >
            Account &amp; data
          </Link>
          <Link
            href="/settings/privacy"
            className={cn(buttonVariants({ variant: "outline" }))}
          >
            Privacy &amp; consent
          </Link>
        </CardContent>
      </Card>

      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Daily match digests</CardTitle>
          <CardDescription>
            Email is the default for all plans. WhatsApp digests are available on Starter and above.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {prefsLoading ? (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          ) : (
            CHANNEL_OPTIONS.map((opt) => {
              const disabled =
                savingChannel || (!paidWhatsApp && opt.value !== "email");
              return (
                <label
                  key={opt.value}
                  className={`flex gap-3 rounded-lg border p-3 cursor-pointer ${
                    disabled ? "opacity-50 cursor-not-allowed" : ""
                  }`}
                >
                  <input
                    type="radio"
                    name="digest-channel"
                    className="mt-1"
                    checked={channel === opt.value}
                    disabled={disabled}
                    onChange={() => updateChannel(opt.value)}
                  />
                  <span>
                    <span className="text-sm font-medium block">{opt.label}</span>
                    <span className="text-xs text-muted-foreground">{opt.hint}</span>
                  </span>
                </label>
              );
            })
          )}
          {!prefsLoading && !paidWhatsApp && (
            <p className="text-xs text-muted-foreground">
              Upgrade to Starter to enable WhatsApp or both channels.
            </p>
          )}
        </CardContent>
      </Card>

      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Auto-match</CardTitle>
          <CardDescription>Let ZedApply run scheduled matching. Manual refresh still works when off.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between gap-4 min-h-11">
            <span className="text-sm">Scheduled auto-match</span>
            {prefsLoading ? (
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            ) : (
              <input
                type="checkbox"
                className="h-5 w-5 rounded border-input"
                checked={autoPrefs?.auto_match_enabled ?? true}
                disabled={savingAutoMatch}
                onChange={(e) => updateAutoMatch(e.target.checked)}
              />
            )}
          </div>
        </CardContent>
      </Card>

    </div>
  );
}
