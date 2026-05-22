"use client";

import { useEffect, useState } from "react";
import { adminTierConfig, profile, type TierConfigRow } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { notify } from "@/lib/toast";
import { UNLIMITED_MATCHES } from "@/lib/tier-config";

type EditableTier = TierConfigRow & {
  price_kwacha: string;
  unlimited_matches: boolean;
};

function toEditable(row: TierConfigRow): EditableTier {
  return {
    ...row,
    price_kwacha: String(row.price_ngwee / 100),
    unlimited_matches: row.matches_limit >= UNLIMITED_MATCHES,
  };
}

function fromEditable(row: EditableTier): TierConfigRow {
  const priceKwacha = Math.max(0, parseInt(row.price_kwacha, 10) || 0);
  const matches = row.unlimited_matches
    ? UNLIMITED_MATCHES
    : Math.max(0, parseInt(String(row.matches_limit), 10) || 0);
  return {
    tier: row.tier,
    display_name: row.display_name.trim(),
    price_ngwee: row.tier === "free" ? 0 : priceKwacha * 100,
    matches_limit: matches,
    sort_order: row.sort_order,
    updated_at: row.updated_at,
  };
}

const TIER_LABELS: Record<string, string> = {
  free: "Free",
  starter: "Starter",
  professional: "Professional",
  super_standard: "Super Standard",
};

export function TierConfigEditor({ token }: { token: string }) {
  const [isSuperadmin, setIsSuperadmin] = useState(false);
  const [rows, setRows] = useState<EditableTier[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    profile
      .get(token)
      .then((p) => setIsSuperadmin(p.role === "superadmin"))
      .catch(() => setIsSuperadmin(false));
  }, [token]);

  useEffect(() => {
    if (!isSuperadmin) {
      setLoading(false);
      return;
    }
    setLoading(true);
    adminTierConfig
      .get(token)
      .then((r) => setRows(r.tiers.map(toEditable)))
      .catch((e) =>
        notify.error(e instanceof Error ? e.message : "Failed to load tier config"),
      )
      .finally(() => setLoading(false));
  }, [token, isSuperadmin]);

  if (!isSuperadmin) {
    return null;
  }

  const updateRow = (tier: string, patch: Partial<EditableTier>) => {
    setRows((prev) =>
      prev.map((r) => (r.tier === tier ? { ...r, ...patch } : r)),
    );
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const payload = rows.map(fromEditable);
      const res = await adminTierConfig.update(token, payload);
      setRows(res.tiers.map(toEditable));
      notify.custom.success("Tier pricing and match limits saved.");
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Card>
      <CardContent className="p-4 space-y-4">
        <div>
          <h2 className="text-lg font-semibold">Tier pricing &amp; match limits</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Superadmin only. Changes apply to new payments, subscription quotas, and
            the public pricing page. Prices are in ZMW (kwacha); stored as ngwee in the
            database. Use unlimited for Super Standard (99999).
          </p>
        </div>

        {loading ? (
          <p className="text-sm text-muted-foreground">Loading tier config…</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-border text-left">
                  <th className="py-2 pr-3 font-medium">Tier</th>
                  <th className="py-2 pr-3 font-medium">Display name</th>
                  <th className="py-2 pr-3 font-medium">Price (ZMW/mo)</th>
                  <th className="py-2 pr-3 font-medium">Matches / month</th>
                  <th className="py-2 font-medium">Unlimited</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.tier} className="border-b border-border/60">
                    <td className="py-3 pr-3 capitalize text-muted-foreground">
                      {TIER_LABELS[row.tier] ?? row.tier}
                    </td>
                    <td className="py-3 pr-3">
                      <Input
                        value={row.display_name}
                        onChange={(e) =>
                          updateRow(row.tier, { display_name: e.target.value })
                        }
                        className="min-h-9"
                      />
                    </td>
                    <td className="py-3 pr-3">
                      <Input
                        type="number"
                        min={0}
                        disabled={row.tier === "free"}
                        value={row.tier === "free" ? "0" : row.price_kwacha}
                        onChange={(e) =>
                          updateRow(row.tier, { price_kwacha: e.target.value })
                        }
                        className="min-h-9 w-28"
                      />
                    </td>
                    <td className="py-3 pr-3">
                      <Input
                        type="number"
                        min={0}
                        disabled={row.unlimited_matches}
                        value={row.unlimited_matches ? "—" : String(row.matches_limit)}
                        onChange={(e) =>
                          updateRow(row.tier, {
                            matches_limit: parseInt(e.target.value, 10) || 0,
                          })
                        }
                        className="min-h-9 w-28"
                      />
                    </td>
                    <td className="py-3">
                      <input
                        type="checkbox"
                        checked={row.unlimited_matches}
                        onChange={(e) =>
                          updateRow(row.tier, {
                            unlimited_matches: e.target.checked,
                            matches_limit: e.target.checked
                              ? UNLIMITED_MATCHES
                              : row.matches_limit >= UNLIMITED_MATCHES
                                ? 125
                                : row.matches_limit,
                          })
                        }
                        aria-label={`Unlimited matches for ${row.tier}`}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div className="flex justify-end">
          <Button
            className="min-h-9"
            disabled={loading || saving}
            onClick={() => void handleSave()}
          >
            {saving ? "Saving…" : "Save tier config"}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
