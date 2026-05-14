"use client";

import { useCallback, useEffect, useState } from "react";
import { admin, type AdminUserRow } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "sonner";
import { formatDate, SkeletonTableRows } from "./shared";

import type { SubscriptionTier } from "@/lib/api";

type Tier = SubscriptionTier;

export function UsersTab({ token }: { token: string }) {
  const [data, setData] = useState<AdminUserRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    admin
      .users(token, { page, search: search || undefined })
      .then((r) => {
        setData(r.users);
        setPages(r.pages);
      })
      .catch((e) => toast.error(e instanceof Error ? e.message : "Failed to load users"))
      .finally(() => setLoading(false));
  }, [token, page, search]);

  useEffect(() => {
    load();
  }, [load]);

  const onTierChange = async (userId: string, tier: Tier) => {
    setBusyId(userId);
    try {
      await admin.updateSubscription(token, userId, tier);
      toast.success("Tier updated.");
      load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Update failed");
    } finally {
      setBusyId(null);
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
        </form>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Phone</TableHead>
                <TableHead>Tier</TableHead>
                <TableHead>Matches</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Joined</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading && (
                <SkeletonTableRows
                  rows={5}
                  widths={["w-32", "w-28", "w-20", "w-12", "w-12", "w-20"]}
                />
              )}
              {!loading && data.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="text-sm text-muted-foreground">No users found.</TableCell>
                </TableRow>
              )}
              {!loading &&
                data.map((u) => (
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
                      {u.role === "superadmin" ? (
                        <Badge variant="destructive">admin</Badge>
                      ) : (
                        <span className="text-muted-foreground text-xs">user</span>
                      )}
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
