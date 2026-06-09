"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { admin, type AdminJobRow } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { notify } from "@/lib/toast";
import { Loader2 } from "lucide-react";
import { formatDate, SkeletonTableRows } from "./shared";
import { useClientTable } from "@/components/admin/useClientTable";
import {
  AdminExportButton,
  AdminSortableTableHead,
  AdminTableEmptyRow,
  AdminTablePagination,
} from "@/components/admin/AdminTableTools";
import { AdminJobFormDialog } from "@/features/admin/jobs/AdminJobFormDialog";

// Returns row.posted_at (or row.created_at as a fallback) as an epoch ms
// number, or 0 if neither field is present. Defensive read because
// AdminJobRow's exact shape varies depending on how it's serialized.
function rowTimestamp(row: AdminJobRow): number {
  const maybe = row as unknown as { posted_at?: string | null; created_at?: string | null };
  if (maybe.posted_at) {
    const t = new Date(maybe.posted_at).getTime();
    if (!Number.isNaN(t)) return t;
  }
  if (maybe.created_at) {
    const t = new Date(maybe.created_at).getTime();
    if (!Number.isNaN(t)) return t;
  }
  return 0;
}

export function JobsTab({ token }: { token: string }) {
  const [data, setData] = useState<AdminJobRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [filter, setFilter] = useState<"all" | "active" | "expired">("all");
  const [bulkLoading, setBulkLoading] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [dialogMode, setDialogMode] = useState<"create" | "edit" | null>(null);
  const [editingJobId, setEditingJobId] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    const params: { page: number; expired?: boolean; is_active?: boolean } = { page };
    if (filter === "expired") params.expired = true;
    if (filter === "active") params.is_active = true;
    admin
      .jobs(token, params)
      .then((r) => {
        // Pre-sort by posted_at desc so freshly ingested jobs surface
        // at the top of the current page. Column-header sorts via
        // useClientTable still override this initial order.
        // NOTE: this only orders WITHIN the loaded page; cross-page
        // reverse chronology needs a backend ORDER BY change.
        const sortedJobs = [...r.jobs].sort((a, b) => rowTimestamp(b) - rowTimestamp(a));
        setData(sortedJobs);
        setPages(r.pages);
      })
      .catch((e) => notify.error(e instanceof Error ? e.message : "Failed to load jobs"))
      .finally(() => setLoading(false));
  }, [token, page, filter]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const timer = window.setTimeout(() => setSearchQuery(searchInput.trim().toLowerCase()), 300);
    return () => window.clearTimeout(timer);
  }, [searchInput]);

  const filteredData = useMemo(() => {
    if (!searchQuery) return data;
    return data.filter((row) => {
      const haystack = [row.title, row.company ?? "", row.source]
        .join(" ")
        .toLowerCase();
      return haystack.includes(searchQuery);
    });
  }, [data, searchQuery]);

  const { sorted, sortProps } = useClientTable(filteredData, {
    getSortValue: (row, key) => {
      if (key === "closing_date") {
        return row.closing_date ? new Date(row.closing_date).getTime() : 0;
      }
      const v = row[key as keyof AdminJobRow];
      if (typeof v === "boolean") return v ? 1 : 0;
      return String(v ?? "").toLowerCase();
    },
  });

  const onBulkDeactivate = async () => {
    setBulkLoading(true);
    try {
      const r = await admin.bulkDeactivate(token, { expired_only: true });
      notify.custom.success(`Deactivated ${r.deactivated} expired job(s).`);
      load();
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Bulk action failed");
    } finally {
      setBulkLoading(false);
    }
  };

  const onToggle = async (job: AdminJobRow) => {
    setBusyId(job.id);
    try {
      await admin.updateJob(token, job.id, { is_active: !job.is_active });
      notify.custom.success(job.is_active ? "Deactivated" : "Activated");
      load();
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Toggle failed");
    } finally {
      setBusyId(null);
    }
  };

  const onDelete = async (job: AdminJobRow) => {
    const confirmed = window.confirm(
      `Delete "${job.title}"? This permanently deletes the job from the database.`,
    );
    if (!confirmed) return;
    setBusyId(job.id);
    try {
      await admin.deleteJob(token, job.id);
      notify.custom.success("Job deleted.");
      if (editingJobId === job.id) {
        setDialogMode(null);
        setEditingJobId(null);
      }
      load();
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setBusyId(null);
    }
  };

  const openCreate = () => {
    setEditingJobId(null);
    setDialogMode("create");
  };

  const openEdit = (job: AdminJobRow) => {
    setEditingJobId(job.id);
    setDialogMode("edit");
  };

  return (
    <>
      <Card>
        <CardContent className="p-0">
          <div className="flex flex-wrap gap-2 p-3 border-b border-border items-center">
            <Input
              placeholder="Search title, company, source…"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="h-9 min-h-9 w-full sm:max-w-xs"
              aria-label="Search jobs"
            />
            <select
              className="h-9 min-h-9 rounded-md border border-input bg-background px-2 text-sm"
              value={filter}
              onChange={(e) => {
                setFilter(e.target.value as typeof filter);
                setPage(1);
              }}
            >
              <option value="all">All</option>
              <option value="active">Active only</option>
              <option value="expired">Expired & still active</option>
            </select>
            <Link
              href="/admin/jobs/new"
              className="inline-flex min-h-9 items-center rounded-md border border-input bg-background px-3 text-sm font-medium hover:bg-muted"
            >
              Full wizard
            </Link>
            <Button type="button" size="sm" className="min-h-9" onClick={openCreate}>
              Post a job
            </Button>
            <Button
              type="button"
              size="sm"
              variant="destructive"
              className="min-h-9"
              disabled={bulkLoading}
              onClick={onBulkDeactivate}
            >
              {bulkLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Deactivate expired"}
            </Button>
            <AdminExportButton
              filename={`zedapply-jobs-p${page}-${filter}.csv`}
              headers={["title", "company", "source_url", "apply_url", "quality", "active", "closes"]}
              rows={sorted.map((j) => [
                j.title,
                j.company ?? "",
                j.source_url ?? "",
                j.apply_url ?? "",
                String(j.quality_score ?? ""),
                j.is_active ? "yes" : "no",
                formatDate(j.closing_date),
              ])}
              disabled={loading}
            />
          </div>

          <div className="w-full min-w-0">
            <Table className="table-fixed w-full">
              <TableHeader>
                <TableRow>
                  <AdminSortableTableHead
                    label="Title"
                    sortProps={sortProps("title")}
                    className="w-[22%]"
                  />
                  <AdminSortableTableHead
                    label="Company"
                    sortProps={sortProps("company")}
                    className="w-[14%]"
                  />
                  <AdminSortableTableHead
                    label="Source URL"
                    sortProps={sortProps("source_url")}
                    className="w-[15%]"
                  />
                  <AdminSortableTableHead
                    label="Apply URL"
                    sortProps={sortProps("apply_url")}
                    className="w-[15%]"
                  />
                  <TableHead className="w-[8%]">Quality</TableHead>
                  <AdminSortableTableHead
                    label="Active"
                    sortProps={sortProps("is_active")}
                    className="w-[8%]"
                  />
                  <AdminSortableTableHead
                    label="Closes"
                    sortProps={sortProps("closing_date")}
                    className="w-[10%]"
                  />
                  <TableHead className="w-[12%] text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {loading && (
                  <SkeletonTableRows
                    rows={5}
                    widths={["w-full", "w-full", "w-full", "w-full", "w-8", "w-16", "w-20", "w-24"]}
                  />
                )}
                {!loading && sorted.length === 0 && (
                  <AdminTableEmptyRow
                    colSpan={8}
                    title={searchQuery ? "No jobs match your search" : "No jobs match this filter"}
                    description={
                      searchQuery
                        ? "Try a different search term or clear the filter."
                        : "Try a different filter or post a new job."
                    }
                  />
                )}
                {!loading &&
                  sorted.map((j) => (
                    <TableRow key={j.id}>
                      <TableCell className="truncate max-w-0" title={j.title}>
                        {j.title}
                      </TableCell>
                      <TableCell className="truncate max-w-0" title={j.company ?? undefined}>
                        {j.company || <span className="text-muted-foreground">—</span>}
                      </TableCell>
                      <TableCell className="truncate max-w-0 text-xs" title={j.source_url ?? undefined}>
                        {j.source_url ? (
                          <a
                            href={j.source_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:underline"
                          >
                            {j.source_url}
                          </a>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell className="truncate max-w-0 text-xs" title={j.apply_url ?? undefined}>
                        {j.apply_url ? (
                          <a
                            href={j.apply_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-primary hover:underline"
                          >
                            {j.apply_url}
                          </a>
                        ) : (
                          <span className="text-muted-foreground">—</span>
                        )}
                      </TableCell>
                      <TableCell className="tabular-nums">{j.quality_score}</TableCell>
                      <TableCell>
                        {j.is_active ? (
                          <Badge variant="default">active</Badge>
                        ) : (
                          <Badge variant="secondary">inactive</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                        {formatDate(j.closing_date)}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="inline-flex flex-wrap justify-end gap-1">
                          <Button
                            size="sm"
                            variant="outline"
                            className="min-h-8 h-8 px-2 text-xs"
                            onClick={() => openEdit(j)}
                          >
                            Edit
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="min-h-8 h-8 px-2 text-xs"
                            disabled={busyId === j.id}
                            onClick={() => onToggle(j)}
                          >
                            {busyId === j.id ? "…" : j.is_active ? "Deactivate" : "Activate"}
                          </Button>
                          <Button
                            size="sm"
                            variant="destructive"
                            className="min-h-8 h-8 px-2 text-xs"
                            disabled={busyId === j.id}
                            onClick={() => void onDelete(j)}
                          >
                            Delete
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
              </TableBody>
            </Table>
          </div>
          <AdminTablePagination page={page} pages={pages} onPageChange={setPage} />
        </CardContent>
      </Card>

      <AdminJobFormDialog
        token={token}
        open={dialogMode !== null}
        onOpenChange={(open) => {
          if (!open) {
            setDialogMode(null);
            setEditingJobId(null);
          }
        }}
        mode={dialogMode === "edit" ? "edit" : "create"}
        jobId={editingJobId}
        onSaved={load}
      />
    </>
  );
}
