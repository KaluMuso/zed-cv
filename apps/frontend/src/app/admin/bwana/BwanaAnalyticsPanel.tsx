"use client";

import { useCallback, useEffect, useState } from "react";
import { adminBwana, type BwanaAnalyticsSummary } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";

export function BwanaAnalyticsPanel({ token }: { token: string }) {
  const [days, setDays] = useState(7);
  const [data, setData] = useState<BwanaAnalyticsSummary | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const summary = await adminBwana.analytics(token, days);
      setData(summary);
    } catch {
      setData(null);
    } finally {
      setLoading(false);
    }
  }, [token, days]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <Card>
      <CardContent className="p-4 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <h2 className="text-lg font-semibold">Analytics</h2>
          <label className="text-sm flex items-center gap-2">
            Period
            <select
              className="rounded-md border border-input bg-background px-2 py-1 text-sm"
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
            >
              <option value={7}>7 days</option>
              <option value={14}>14 days</option>
              <option value={30}>30 days</option>
            </select>
          </label>
        </div>
        {loading && (
          <p className="text-sm text-muted-foreground">Loading analytics…</p>
        )}
        {!loading && data && (
          <div className="space-y-4 text-sm">
            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-lg border p-3">
                <p className="text-muted-foreground">Messages</p>
                <p className="text-2xl font-semibold">{data.total_messages}</p>
              </div>
              <div className="rounded-lg border p-3">
                <p className="text-muted-foreground">Escalations</p>
                <p className="text-2xl font-semibold">{data.total_escalations}</p>
              </div>
              <div className="rounded-lg border p-3">
                <p className="text-muted-foreground">Escalation rate</p>
                <p className="text-2xl font-semibold">
                  {data.escalation_rate_percent}%
                </p>
              </div>
            </div>
            <div>
              <p className="font-medium mb-1">By source</p>
              <ul className="text-muted-foreground space-y-0.5">
                {Object.entries(data.messages_by_source).map(([k, v]) => (
                  <li key={k}>
                    {k}: {v}
                  </li>
                ))}
              </ul>
            </div>
            <div>
              <p className="font-medium mb-1">Escalations by reason</p>
              <ul className="text-muted-foreground space-y-0.5">
                {Object.entries(data.escalations_by_reason).map(([k, v]) => (
                  <li key={k}>
                    {k}: {v}
                  </li>
                ))}
              </ul>
            </div>
            {data.top_faq_intents.length > 0 && (
              <div>
                <p className="font-medium mb-1">Top FAQ intents</p>
                <ul className="text-muted-foreground space-y-0.5">
                  {data.top_faq_intents.map((row) => (
                    <li key={row.intent_id}>
                      {row.intent_id}: {row.count}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
