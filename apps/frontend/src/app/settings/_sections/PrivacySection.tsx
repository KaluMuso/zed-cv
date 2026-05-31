"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { profile as profileApi, userPreferences, type UserPreferences } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { notify } from "@/lib/toast";
import { DataPrivacyCard } from "@/app/profile/_tabs/DataPrivacyCard";
import { ConsentPreferencesSection } from "./ConsentPreferencesSection";
import { SettingsCard, SettingsSectionHeader } from "../_components/SettingsShell";

export function PrivacySection() {
  const { token } = useAuth();
  const [phone, setPhone] = useState<string | null>(null);
  const [prefs, setPrefs] = useState<UserPreferences | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const load = useCallback(() => {
    if (!token) return;
    Promise.all([profileApi.get(token), userPreferences.get(token)])
      .then(([profile, dash]) => {
        setPhone(profile.phone);
        setPrefs(dash);
      })
      .catch((e) => notify.error(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const patchPrefs = async (data: Parameters<typeof userPreferences.patch>[1]) => {
    if (!token || !prefs) return;
    setSaving(true);
    try {
      const next = await userPreferences.patch(token, data);
      setPrefs(next);
      notify.custom.success("Saved");
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Could not save");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-muted-foreground">Loading privacy settings…</p>;
  }

  return (
    <div>
      <SettingsSectionHeader title="Privacy & data" />

      <ConsentPreferencesSection />

      <SettingsCard className="mb-4">
        <div className="eyebrow mb-2">Visibility</div>
        <label className="flex items-start justify-between gap-4 py-3 border-b border-[var(--line)]">
          <span>
            <span className="text-sm font-medium block">Show profile to employers</span>
            <span className="text-xs" style={{ color: "var(--muted)" }}>
              On by default. Verified employers can discover your profile in search; they
              must get your WhatsApp YES before seeing your phone or email.
            </span>
          </span>
          <input
            type="checkbox"
            className="h-5 w-5 mt-0.5"
            checked={prefs?.profile_visible_to_employers ?? true}
            disabled={saving}
            onChange={(e) => void patchPrefs({ profile_visible_to_employers: e.target.checked })}
          />
        </label>
        <div className="pt-4">
          <label className="text-xs font-medium uppercase tracking-wider block mb-2" style={{ color: "var(--muted)" }}>
            Hide from current employer
          </label>
          <input
            type="text"
            className="field"
            placeholder="Company name (optional)"
            value={prefs?.hidden_employer_name ?? ""}
            disabled={saving}
            onChange={(e) =>
              setPrefs((p) => (p ? { ...p, hidden_employer_name: e.target.value } : p))
            }
            onBlur={() =>
              void patchPrefs({ hidden_employer_name: prefs?.hidden_employer_name?.trim() || null })
            }
          />
          <p className="text-xs mt-2" style={{ color: "var(--muted)" }}>
            We&apos;ll try to exclude this employer from your match suggestions.
          </p>
        </div>
      </SettingsCard>

      <SettingsCard className="mb-4">
        <div className="eyebrow mb-2">Your data</div>
        <p className="text-sm mb-4 leading-relaxed" style={{ color: "var(--muted)" }}>
          We don&apos;t sell your data. Download a copy under the Zambia Data Protection Act 2021.
        </p>
        {token && phone ? (
          <DataPrivacyCard token={token} phone={phone} onDeleted={() => {}} exportOnly />
        ) : null}
      </SettingsCard>

      <SettingsCard>
        <div className="eyebrow mb-2">Policies</div>
        <ul className="space-y-2 text-sm">
          <li>
            <Link href="/legal/privacy" className="underline" style={{ color: "var(--green-700)" }}>
              Privacy policy
            </Link>
          </li>
          <li>
            <Link href="/legal/terms" className="underline" style={{ color: "var(--green-700)" }}>
              Terms of service
            </Link>
          </li>
          <li>
            <Link href="/legal/cookies" className="underline" style={{ color: "var(--green-700)" }}>
              Cookie policy
            </Link>
          </li>
        </ul>
      </SettingsCard>
    </div>
  );
}
