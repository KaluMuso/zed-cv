"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { dataRights, type ConsentType } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { notify } from "@/lib/toast";
import { Loader2 } from "lucide-react";
import { SettingsCard, SettingsSectionHeader } from "../_components/SettingsShell";

const CONSENT_TOGGLES: { type: ConsentType; label: string; hint: string }[] = [
  {
    type: "terms_of_service",
    label: "Terms of Service",
    hint: "Required to use Zed Apply. Version recorded when you toggle.",
  },
  {
    type: "privacy_policy",
    label: "Privacy Policy",
    hint: "How we process your data under ZDPA 2021.",
  },
  {
    type: "marketing_email",
    label: "Marketing email",
    hint: "Product updates and tips by email.",
  },
  {
    type: "marketing_whatsapp",
    label: "Marketing WhatsApp",
    hint: "Promotional messages on WhatsApp (separate from match digests).",
  },
  {
    type: "analytics_cookies",
    label: "Analytics cookies",
    hint: "Helps us understand how the site is used.",
  },
  {
    type: "third_party_data_sharing",
    label: "Third-party data sharing",
    hint: "Optional sharing with integrated partners where applicable.",
  },
];

const DEFAULT_CONSENTS: Record<ConsentType, boolean> = {
  terms_of_service: true,
  privacy_policy: true,
  marketing_email: false,
  marketing_whatsapp: false,
  analytics_cookies: false,
  third_party_data_sharing: false,
};

export function ConsentPreferencesSection() {
  const { token } = useAuth();
  const [values, setValues] = useState<Record<ConsentType, boolean>>(DEFAULT_CONSENTS);
  const [lastUpdated, setLastUpdated] = useState<Partial<Record<ConsentType, string>>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<ConsentType | null>(null);

  const load = useCallback(() => {
    if (!token) return;
    dataRights
      .getConsentStatus(token)
      .then((res) => {
        setValues({ ...DEFAULT_CONSENTS, ...res.consents });
        setLastUpdated(res.last_updated as Partial<Record<ConsentType, string>>);
      })
      .catch((e) => notify.error(e instanceof Error ? e.message : "Failed to load consent"))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => {
    load();
  }, [load]);

  const onToggle = async (type: ConsentType, granted: boolean) => {
    if (!token) return;
    if ((type === "terms_of_service" || type === "privacy_policy") && !granted) {
      notify.error("Terms and Privacy must remain accepted to use Zed Apply.");
      return;
    }
    setSaving(type);
    try {
      const res = await dataRights.recordConsent(token, type, granted);
      setValues((v) => ({ ...v, [type]: granted }));
      setLastUpdated((u) => ({ ...u, [type]: res.consent.granted_at }));
      notify.custom.success("Saved");
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Could not save consent");
    } finally {
      setSaving(null);
    }
  };

  if (loading) {
    return <p className="text-sm text-muted-foreground">Loading consent preferences…</p>;
  }

  return (
    <div className="mb-6">
      <SettingsSectionHeader title="Consent preferences" />
      <SettingsCard>
        <p className="text-sm mb-4 leading-relaxed" style={{ color: "var(--muted)" }}>
          Each change is appended to your consent audit log with timestamp and legal document
          version. See also{" "}
          <Link href="/legal/privacy" className="underline" style={{ color: "var(--green-700)" }}>
            Privacy Policy
          </Link>{" "}
          and{" "}
          <Link href="/legal/cookies" className="underline" style={{ color: "var(--green-700)" }}>
            Cookie Policy
          </Link>
          .
        </p>
        <div className="space-y-0">
          {CONSENT_TOGGLES.map((item) => {
            const checked = values[item.type] ?? false;
            const busy = saving === item.type;
            return (
              <label
                key={item.type}
                className="flex items-start justify-between gap-4 py-4 border-b border-[var(--line)] last:border-0 cursor-pointer"
              >
                <span>
                  <span className="text-sm font-medium block">{item.label}</span>
                  <span className="text-xs mt-1 block" style={{ color: "var(--muted)" }}>
                    {item.hint}
                  </span>
                  {lastUpdated[item.type] ? (
                    <span className="text-xs mt-1 block" style={{ color: "var(--muted)" }}>
                      Last updated {new Date(lastUpdated[item.type]!).toLocaleString()}
                    </span>
                  ) : null}
                </span>
                <span className="flex items-center gap-2 shrink-0 mt-0.5">
                  {busy ? (
                    <Loader2 className="h-4 w-4 animate-spin" style={{ color: "var(--muted)" }} />
                  ) : null}
                  <input
                    type="checkbox"
                    className="h-5 w-5"
                    checked={checked}
                    disabled={busy}
                    onChange={(e) => void onToggle(item.type, e.target.checked)}
                  />
                </span>
              </label>
            );
          })}
        </div>
      </SettingsCard>
    </div>
  );
}
