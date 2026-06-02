"use client";

import { useCallback, useEffect, useState } from "react";
import { admin, type AdminUserRow } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { notify } from "@/lib/toast";
import { formatDate, SkeletonTableRows } from "./shared";
import { useClientTable, exportRowsToCsv, sortIsoDate } from "@/components/admin/useClientTable";
import { AdminSortableTableHead } from "@/components/admin/AdminTableTools";
import { EmptyState } from "@/components/shared/EmptyState";

import type { SubscriptionTier } from "@/lib/api";

type Tier = SubscriptionTier;

export function UsersTab({ token }: { token: string }) {
  const [data, setData] = useState<AdminUserRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [tierFilter, setTierFilter] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);

  const { sorted, sortProps } = useClientTable(data, {
    getSortValue: (row, key) => {
      if (key === "created_at") return sortIsoDate(row.created_at);
      const v = row[key as keyof AdminUserRow];
      if (typeof v === "number") return v;
      return String(v ?? "").toLowerCase();
    },
  });

  const load = useCallback(() => {
    setLoading(true);
    admin
      .users(token, {
        page,
        search: search || undefined,
        tier: tierFilter || undefined,
      })
      .then((r) => {
        setData(r.users);
        setPages(r.pages);
      })
      .catch((e) => notify.error(e instanceof Error ? e.message : "Failed to load users"))
      .finally(() => setLoading(false));
  }, [token, page, search, tierFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const onTierChange = async (userId: string, tier: Tier) => {
    setBusyId(userId);
    try {
      await admin.updateSubscription(token, userId, tier);
      notify.custom.success("Tier updated.");
      load();
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Update failed");
    } finally {
      setBusyId(null);
    }
  };

  const onRepairDelivery = async (userId: string, phone: string) => {
    const ok = window.confirm(
      `Repair delivery quota for ${phone}?\n\n` +
        "• Restores free-tier welcome window (7 matches / 1 month) if missing\n" +
        "• Clears this month's delivered credits and re-credits top matches up to tier limit\n\n" +
        "Use after a user saw too many matches. They should refresh /matches after.",
    );
    if (!ok) return;
    setBusyId(userId);
    try {
      const result = await admin.repairDeliveryQuota(token, userId);
      notify.custom.success(
        `Repaired: ${result.credited_before} → ${result.credited_after} delivered (limit ${result.matches_limit}).`,
      );
      load();
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Repair failed");
    } finally {
      setBusyId(null);
    }
  };

  const onWelcomeUntilChange = async (userId: string, value: string) => {
    if (!value) return;
    setBusyId(userId);
    try {
      const until = new Date(`${value}T23:59:59Z`).toISOString();
      await admin.updateWelcomeBonus(token, userId, { welcome_match_bonus_until: until });
      notify.custom.success("Welcome bonus extended.");
      load();
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Update failed");
    } finally {
      setBusyId(null);
    }
  };

  const welcomeDateInputValue = (iso: string | null | undefined): string => {
    if (!iso) return "";
    try {
      return new Date(iso).toISOString().slice(0, 10);
    } catch {
      return "";
    }
  };

  return (
    <Card>
      <CardContent className="p-0">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setPage(1);
            setSearch(searchInput);
          }}
          className="flex gap-2 p-3 border-b border-border"
        >
          <Input
            placeholder="Search phone, name, email"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="h-9 max-w-sm"
          />
          <Button type="submit" size="sm" className="min-h-9">Search</Button>
          <select
            value={tierFilter}
            onChange={(e) => {
              setTierFilter(e.target.value);
              setPage(1);
            }}
            className="h-9 rounded-md border border-input bg-background px-2 text-sm"
            aria-label="Filter by tier"
          >
            <option value="">All tiers</option>
            <option value="free">free</option>
            <option value="starter">starter</option>
            <option value="professional">professional</option>
            <option value="super_standard">super_standard</option>
          </select>
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="min-h-9 ml-auto"
            disabled={data.length === 0}
            onClick={() =>
              exportRowsToCsv(
                `zedapply-users-p${page}.csv`,
                ["name", "phone", "tier", "matches", "role", "joined"],
                sorted.map((u) => [
                  u.full_name ?? "",
                  u.phone,
                  u.subscription_tier,
                  `${u.matches_used}/${u.matches_limit}`,
                  u.role,
                  formatDate(u.created_at),
                ]),
              )
            }
          >
            Export CSV
          </Button>
        </form>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <AdminSortableTableHead label="Name" sortProps={sortProps("full_name")} />
                <AdminSortableTableHead label="Phone" sortProps={sortProps("phone")} />
                <AdminSortableTableHead label="Tier" sortProps={sortProps("subscription_tier")} />
                <AdminSortableTableHead label="Matches" sortProps={sortProps("matches_used")} />
                <TableHead>Welcome bonus until</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Actions</TableHead>
                <AdminSortableTableHead label="Joined" sortProps={sortProps("created_at")} />
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading && (
                <SkeletonTableRows
                  rows={5}
                  widths={["w-32", "w-28", "w-20", "w-12", "w-36", "w-12", "w-24", "w-20"]}
                />
              )}
              {!loading && sorted.length === 0 && (
                <TableRow>
                  <TableCell colSpan={8}>
                    <EmptyState title="No users found" description="Try a different search or tier filter." className="border-0 bg-transparent py-8" />
                  </TableCell>
                </TableRow>
              )}
              {!loading &&
                sorted.map((u) => (
                  <TableRow key={u.id}>
                    <TableCell>{u.full_name || <span className="text-muted-foreground">—</span>}</TableCell>
                    <TableCell className="font-mono text-xs">{u.phone}</TableCell>
                    <TableCell>
                      <select
                        value={u.subscription_tier}
                        disabled={busyId === u.id}
                        onChange={(e) => onTierChange(u.id, e.target.value as Tier)}
                        className="h-8 rounded-md border border-input bg-background px-2 text-xs"
                      >
                        <option value="free">free</option>
                        <option value="starter">starter</option>
                        <option value="professional">professional</option>
                        <option value="super_standard">super_standard</option>
                      </select>
                    </TableCell>
                    <TableCell className="tabular-nums">{u.matches_used}/{u.matches_limit}</TableCell>
                    <TableCell>
                      {u.subscription_tier === "free" ? (
                        <input
                          type="date"
                          className="h-8 rounded-md border border-input bg-background px-2 text-xs"
                          disabled={busyId === u.id}
                          value={welcomeDateInputValue(u.welcome_match_bonus_until)}
                          onChange={(e) => onWelcomeUntilChange(u.id, e.target.value)}
                          aria-label={`Welcome bonus until for ${u.phone}`}
                        />
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {u.role === "superadmin" ? (
                        <Badge variant="destructive">admin</Badge>
                      ) : (
                        <span className="text-muted-foreground text-xs">user</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="h-8 text-xs"
                        disabled={busyId === u.id}
                        onClick={() => void onRepairDelivery(u.id, u.phone)}
                      >
                        Repair quota
                      </Button>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">{formatDate(u.created_at)}</TableCell>
                  </TableRow>
                ))}
            </TableBody>
          </Table>
        </div>
        {pages > 1 && (
          <div className="p-3 flex items-center justify-end gap-2 border-t border-border">
            <Button variant="outline" size="sm" className="min-h-9" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Previous</Button>
            <span className="text-sm text-muted-foreground">Page {page} of {pages}</span>
            <Button variant="outline" size="sm" className="min-h-9" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>Next</Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
