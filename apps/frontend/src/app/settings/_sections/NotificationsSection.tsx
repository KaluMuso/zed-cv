"use client";

import { useEffect, useState } from "react";
import {
  autoMatchPreferences,
  userPreferences,
  type AutoMatchPreferences,
  type PreferredNotificationChannel,
  type UserPreferences,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { notify } from "@/lib/toast";
import { Loader2 } from "lucide-react";
import { SettingsCard, SettingsSectionHeader } from "../_components/SettingsShell";

const CHANNEL_OPTIONS: {
  value: PreferredNotificationChannel;
  label: string;
  hint: string;
}[] = [
  { value: "email", label: "Email only", hint: "Daily digests to your inbox (default)." },
  {
    value: "whatsapp",
    label: "WhatsApp only",
    hint: "Starter plan or higher. Requires a verified WhatsApp number.",
  },
  { value: "both", label: "Email and WhatsApp", hint: "Starter plan or higher." },
];

export function NotificationsSection() {
  const { token } = useAuth();
  const [dashPrefs, setDashPrefs] = useState<UserPreferences | null>(null);
  const [autoPrefs, setAutoPrefs] = useState<AutoMatchPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [savingChannel, setSavingChannel] = useState(false);
  const [savingAutoMatch, setSavingAutoMatch] = useState(false);

  useEffect(() => {
    if (!token) return;
    Promise.allSettled([userPreferences.get(token), autoMatchPreferences.get(token)])
      .then(([dashRes, autoRes]) => {
        if (dashRes.status === "fulfilled") setDashPrefs(dashRes.value);
        if (autoRes.status === "fulfilled") setAutoPrefs(autoRes.value);
        if (dashRes.status === "rejected") throw dashRes.reason;
      })
      .catch((e) => notify.error(e instanceof Error ? e.message : "Failed to load preferences"))
      .finally(() => setLoading(false));
  }, [token]);

  const updateChannel = async (next: PreferredNotificationChannel) => {
    if (!token || !dashPrefs) return;
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
    if (!token) return;
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
  const alertFrequency = dashPrefs?.alert_frequency ?? "daily";
  const alertsMuted = alertFrequency === "muted";
  const alertsWeekly = alertFrequency === "weekly";

  const patchDashPrefs = async (data: Parameters<typeof userPreferences.patch>[1]) => {
    if (!token) return;
    setSavingChannel(true);
    try {
      const next = await userPreferences.patch(token, data);
      setDashPrefs(next);
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Could not save");
    } finally {
      setSavingChannel(false);
    }
  };

  return (
    <div>
      <SettingsSectionHeader title="Notifications" />

      <SettingsCard className="mb-4">
        <div className="eyebrow mb-2">WhatsApp</div>
        <h3 className="font-medium text-sm mb-1">Send matches via WhatsApp</h3>
        <p className="text-xs mb-4" style={{ color: "var(--muted)" }}>
          Up to your plan limit. Email digests remain available on all tiers.
        </p>
        <div className="space-y-3">
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          ) : (
            CHANNEL_OPTIONS.map((opt) => {
              const disabled = savingChannel || (!paidWhatsApp && opt.value !== "email");
              const checked = channel === opt.value;
              return (
                <label
                  key={opt.value}
                  className={`flex items-center justify-between gap-3 rounded-lg border p-3 cursor-pointer ${
                    disabled ? "opacity-50 cursor-not-allowed" : ""
                  }`}
                  style={{ borderColor: "var(--line)" }}
                >
                  <span>
                    <span className="text-sm font-medium block">{opt.label}</span>
                    <span className="text-xs" style={{ color: "var(--muted)" }}>
                      {opt.hint}
                    </span>
                  </span>
                  <input
                    type="radio"
                    name="digest-channel"
                    className="h-4 w-4"
                    checked={checked}
                    disabled={disabled}
                    onChange={() => void updateChannel(opt.value)}
                  />
                </label>
              );
            })
          )}
        </div>
        {!loading && !paidWhatsApp && (
          <p className="text-xs mt-3" style={{ color: "var(--muted)" }}>
            <a href="/pricing" className="underline" style={{ color: "var(--green-700)" }}>
              Upgrade to Starter
            </a>{" "}
            to enable WhatsApp or both channels.
          </p>
        )}
      </SettingsCard>

      <SettingsCard className="mb-4">
        <div className="eyebrow mb-2">Email</div>
        <label className="flex items-center justify-between gap-4 py-3 border-b border-[var(--line)]">
          <span>
            <span className="text-sm font-medium block">New match notifications</span>
            <span className="text-xs" style={{ color: "var(--muted)" }}>
              Included in your daily digest when alerts are on.
            </span>
          </span>
          <input
            type="checkbox"
            className="h-5 w-5"
            checked={!alertsMuted}
            disabled={loading || savingChannel}
            onChange={(e) => {
              void patchDashPrefs({
                alert_frequency: e.target.checked
                  ? alertsWeekly
                    ? "weekly"
                    : "daily"
                  : "muted",
              });
            }}
          />
        </label>
        <label className="flex items-center justify-between gap-4 py-3 border-b border-[var(--line)]">
          <span>
            <span className="text-sm font-medium block">Weekly job alerts</span>
            <span className="text-xs" style={{ color: "var(--muted)" }}>
              A summary of activity in your area once per week.
            </span>
          </span>
          <input
            type="checkbox"
            className="h-5 w-5"
            checked={alertsWeekly}
            disabled={loading || savingChannel || alertsMuted}
            onChange={(e) => {
              void patchDashPrefs({
                alert_frequency: e.target.checked ? "weekly" : "daily",
              });
            }}
          />
        </label>
        <label className="flex items-center justify-between gap-4 py-3">
          <span>
            <span className="text-sm font-medium block">Product updates and offers</span>
          </span>
          <input
            type="checkbox"
            className="h-5 w-5"
            checked={dashPrefs?.notify_product_updates ?? false}
            disabled={loading || savingChannel}
            onChange={(e) => {
              void patchDashPrefs({ notify_product_updates: e.target.checked });
            }}
          />
        </label>
      </SettingsCard>

      <SettingsCard className="mb-4">
        <div className="eyebrow mb-2">Quiet hours</div>
        <p className="text-xs mb-4" style={{ color: "var(--muted)" }}>
          We won&apos;t send WhatsApp messages during these hours ({dashPrefs?.display_timezone ?? "Africa/Lusaka"}).
        </p>
        <div className="grid grid-cols-2 gap-4">
          <label className="block">
            <span className="text-xs font-medium uppercase tracking-wider" style={{ color: "var(--muted)" }}>
              From
            </span>
            <input
              type="time"
              className="field mt-1"
              value={dashPrefs?.quiet_hours_start?.slice(0, 5) ?? "20:00"}
              disabled={loading || savingChannel}
              onChange={(e) => {
                void patchDashPrefs({ quiet_hours_start: e.target.value });
              }}
            />
          </label>
          <label className="block">
            <span className="text-xs font-medium uppercase tracking-wider" style={{ color: "var(--muted)" }}>
              To
            </span>
            <input
              type="time"
              className="field mt-1"
              value={dashPrefs?.quiet_hours_end?.slice(0, 5) ?? "07:00"}
              disabled={loading || savingChannel}
              onChange={(e) => {
                void patchDashPrefs({ quiet_hours_end: e.target.value });
              }}
            />
          </label>
        </div>
      </SettingsCard>

      <SettingsCard>
        <div className="eyebrow mb-2">Matching</div>
        <h3 className="font-medium text-sm mb-1">Scheduled auto-match</h3>
        <p className="text-xs mb-4" style={{ color: "var(--muted)" }}>
          Let Zed Apply run scheduled matching. Manual refresh on Matches still works when off.
        </p>
        <div className="flex items-center justify-between gap-4">
          <span className="text-sm">Enable auto-match</span>
          {loading ? (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          ) : (
            <input
              type="checkbox"
              className="h-5 w-5 rounded border-input"
              checked={autoPrefs?.auto_match_enabled ?? true}
              disabled={savingAutoMatch}
              onChange={(e) => void updateAutoMatch(e.target.checked)}
            />
          )}
        </div>
      </SettingsCard>
    </div>
  );
}
