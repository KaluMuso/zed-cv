"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { dataRights, type ConsentType } from "@/lib/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2 } from "lucide-react";
import { notify } from "@/lib/toast";

const CONSENT_TOGGLES: { type: ConsentType; label: string; hint: string }[] = [
  {
    type: "terms_of_service",
    label: "Terms of Service",
    hint: "Required to use ZedApply. Version recorded when you toggle.",
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

export default function PrivacySettingsPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading, token } = useAuth();
  const [values, setValues] = useState<Partial<Record<ConsentType, boolean>>>({
    terms_of_service: true,
    privacy_policy: true,
    marketing_email: false,
    marketing_whatsapp: false,
    analytics_cookies: false,
    third_party_data_sharing: false,
  });
  const [lastUpdated, setLastUpdated] = useState<Partial<Record<ConsentType, string>>>({});
  const [saving, setSaving] = useState<ConsentType | null>(null);

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated || !token) {
      router.push("/auth");
    }
  }, [isAuthenticated, isLoading, router, token]);

  const onToggle = async (type: ConsentType, granted: boolean) => {
    if (!token) return;
    if ((type === "terms_of_service" || type === "privacy_policy") && !granted) {
      notify.error("Terms and Privacy must remain accepted to use ZedApply.");
      return;
    }
    setSaving(type);
    try {
      const res = await dataRights.recordConsent(token, type, granted);
      setValues((v) => ({ ...v, [type]: granted }));
      setLastUpdated((u) => ({ ...u, [type]: res.consent.granted_at }));
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Could not save consent");
    } finally {
      setSaving(null);
    }
  };

  if (isLoading || !isAuthenticated) {
    return <p className="text-sm text-muted-foreground">…</p>;
  }

  return (
    <div>
      <p className="text-sm text-muted-foreground mb-4">
        <Link href="/settings" className="underline">
          Settings
        </Link>{" "}
        / Privacy &amp; consent
      </p>
      <h1 className="text-2xl sm:text-3xl font-bold mb-2">Privacy &amp; consent</h1>
      <p className="text-muted-foreground text-sm mb-6">
        Each change is appended to your consent audit log with timestamp and legal document version.
      </p>

      <Card>
        <CardHeader>
          <CardTitle>Consent preferences</CardTitle>
          <CardDescription>
            See also{" "}
            <Link href="/legal/privacy" className="underline">
              Privacy Policy
            </Link>{" "}
            and{" "}
            <Link href="/legal/cookies" className="underline">
              Cookie Policy
            </Link>
            .
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {CONSENT_TOGGLES.map((item) => {
            const checked = values[item.type] ?? false;
            const busy = saving === item.type;
            return (
              <div
                key={item.type}
                className="flex items-start justify-between gap-4 border-b border-border pb-4 last:border-0"
              >
                <div>
                  <p className="text-sm font-medium">{item.label}</p>
                  <p className="text-xs text-muted-foreground mt-1">{item.hint}</p>
                  {lastUpdated[item.type] && (
                    <p className="text-xs text-muted-foreground mt-1">
                      Last updated {new Date(lastUpdated[item.type]!).toLocaleString()}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {busy && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
                  <input
                    type="checkbox"
                    className="h-5 w-5"
                    checked={checked}
                    disabled={busy}
                    onChange={(e) => void onToggle(item.type, e.target.checked)}
                  />
                </div>
              </div>
            );
          })}
        </CardContent>
      </Card>
    </div>
  );
}
