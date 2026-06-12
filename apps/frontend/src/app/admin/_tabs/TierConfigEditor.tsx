"use client";

import { useEffect, useState } from "react";
import { adminTiers, profile, type TierConfigRow } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { notify } from "@/lib/toast";
import { UNLIMITED_MATCHES } from "@/lib/tier-config";

type EditableTier = TierConfigRow & {
  price_kwacha: string;
  matches_input: string;
  marketing_blurb_input: string;
  is_highlighted_input: boolean;
};

function toEditable(row: TierConfigRow): EditableTier {
  return {
    ...row,
    price_kwacha: String(row.price_ngwee / 100),
    matches_input: String(row.matches_limit),
    marketing_blurb_input: row.marketing_blurb || "",
    is_highlighted_input: row.is_highlighted || false,
  };
}

function toPatchBody(row: EditableTier): { price_ngwee: number; matches_limit: number; marketing_blurb?: string; is_highlighted?: boolean } {
  const priceKwacha = Math.max(0, parseInt(row.price_kwacha, 10) || 0);
  const matches = Math.max(0, parseInt(row.matches_input, 10) || 0);
  return {
    price_ngwee: row.tier === "free" ? 0 : priceKwacha * 100,
    matches_limit: matches,
    marketing_blurb: row.marketing_blurb_input,
    is_highlighted: row.is_highlighted_input,
  };
}

const TIER_LABELS: Record<string, string> = {
  free: "Free",
  starter: "Starter",
  professional: "Professional",
  super_standard: "Super Standard",
};

const CANONICAL_TIER_ORDER = [
  "free",
  "starter",
  "professional",
  "super_standard",
] as const;

export function TierConfigEditor({ token }: { token: string }) {
  const [isSuperadmin, setIsSuperadmin] = useState(false);
  const [rows, setRows] = useState<EditableTier[]>([]);
  const [loading, setLoading] = useState(true);
  const [savingTier, setSavingTier] = useState<string | null>(null);

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
    adminTiers
      .list(token)
      .then((r) => {
        const byTier = Object.fromEntries(r.tiers.map((t) => [t.tier, t]));
        const ordered = CANONICAL_TIER_ORDER.map(
          (tier) => byTier[tier] ?? {
            tier,
            display_name: TIER_LABELS[tier] ?? tier,
            price_ngwee: 0,
            matches_limit: 0,
            sort_order: 0,
          },
        );
        setRows(ordered.map(toEditable));
      })
      .catch((e) =>
        notify.error(e instanceof Error ? e.message : "Failed to load tier config"),
      )
      .finally(() => setLoading(false));
  }, [token, isSuperadmin]);

  if (!isSuperadmin) {
    return (
      <p className="text-sm text-muted-foreground">
        Tier configuration is available to superadmin accounts only.
      </p>
    );
  }

  const updateRow = (tier: string, patch: Partial<EditableTier>) => {
    setRows((prev) =>
      prev.map((r) => (r.tier === tier ? { ...r, ...patch } : r)),
    );
  };

  const handleSaveRow = async (row: EditableTier) => {
    setSavingTier(row.tier);
    try {
      const updated = await adminTiers.patch(token, row.tier, toPatchBody(row));
      setRows((prev) =>
        prev.map((r) => (r.tier === row.tier ? toEditable(updated) : r)),
      );
      notify.custom.success("Tier updated successfully");
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSavingTier(null);
    }
  };

  return (
    <Card>
      <CardContent className="p-4 space-y-4">
        <div>
          <h2 className="text-lg font-semibold">Tier Config</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Adjust match limits and monthly prices for each plan. Prices are in ZMW;
            stored as ngwee in the database. Use {UNLIMITED_MATCHES} for unlimited
            matches (Super Standard).
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
                  <th className="py-2 pr-3 font-medium">Matches Limit</th>
                  <th className="py-2 pr-3 font-medium">Price (ZMW)</th>
                  <th className="py-2 pr-3 font-medium">Marketing Blurb</th>
                  <th className="py-2 pr-3 font-medium">Highlight?</th>
                  <th className="py-2 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.tier} className="border-b border-border/60">
                    <td className="py-3 pr-3 text-muted-foreground">
                      {TIER_LABELS[row.tier] ?? row.tier}
                    </td>
                    <td className="py-3 pr-3">
                      <Input
                        type="number"
                        min={0}
                        value={row.matches_input}
                        onChange={(e) =>
                          updateRow(row.tier, { matches_input: e.target.value })
                        }
                        className="min-h-9 w-32"
                        aria-label={`Matches limit for ${row.tier}`}
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
                        className="min-h-9 w-32"
                        aria-label={`Price for ${row.tier}`}
                      />
                    </td>
                    <td className="py-3 pr-3">
                      <Input
                        type="text"
                        value={row.marketing_blurb_input}
                        onChange={(e) =>
                          updateRow(row.tier, { marketing_blurb_input: e.target.value })
                        }
                        className="min-h-9 w-48"
                        aria-label={`Marketing blurb for ${row.tier}`}
                        placeholder="e.g. Most Popular"
                      />
                    </td>
                    <td className="py-3 pr-3 text-center">
                      <input
                        type="checkbox"
                        checked={row.is_highlighted_input}
                        onChange={(e) =>
                          updateRow(row.tier, { is_highlighted_input: e.target.checked })
                        }
                        className="h-4 w-4"
                        aria-label={`Highlight ${row.tier}`}
                      />
                    </td>
                    <td className="py-3 text-right">
                      <Button
                        className="min-h-9"
                        size="sm"
                        disabled={savingTier === row.tier}
                        onClick={() => void handleSaveRow(row)}
                      >
                        {savingTier === row.tier ? "Saving…" : "Save"}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
