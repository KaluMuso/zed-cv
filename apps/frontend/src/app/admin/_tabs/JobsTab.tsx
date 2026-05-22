"use client";

import { useCallback, useEffect, useState } from "react";
import {
  admin,
  jobs as jobsApi,
  type AdminJobRow,
  type AdminJobCreate,
} from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { notify } from "@/lib/toast";
import { Loader2 } from "lucide-react";
import { formatDate, SkeletonTableRows } from "./shared";

const EMPTY_FORM: AdminJobCreate = {
  title: "",
  company: "",
  location: "",
  description: "",
  source: "manual",
  apply_url: "",
  apply_email: "",
  closing_date: "",
};

export function JobsTab({ token }: { token: string }) {
  const [data, setData] = useState<AdminJobRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [filter, setFilter] = useState<"all" | "active" | "expired">("all");
  const [bulkLoading, setBulkLoading] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<AdminJobCreate>(EMPTY_FORM);
  const [creating, setCreating] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  // Edit-mode state. `editingId` non-null means the form is editing
  // that job; the create button hides while editing to avoid confusion.
  // editForm reuses AdminJobCreate's shape since the PATCH endpoint
  // accepts the same set of fields (plus id).
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<AdminJobCreate>(EMPTY_FORM);
  const [editLoading, setEditLoading] = useState(false);
  const [editSaving, setEditSaving] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    const params: { page: number; expired?: boolean; is_active?: boolean } = { page };
    if (filter === "expired") params.expired = true;
    if (filter === "active") params.is_active = true;
    admin
      .jobs(token, params)
      .then((r) => {
        setData(r.jobs);
        setPages(r.pages);
      })
      .catch((e) => notify.error(e instanceof Error ? e.message : "Failed to load jobs"))
      .finally(() => setLoading(false));
  }, [token, page, filter]);

  useEffect(() => {
    load();
  }, [load]);

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

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title || form.title.length < 5) {
      notify.error("Title must be at least 5 characters");
      return;
    }
    if (!form.description || form.description.length < 20) {
      notify.error("Description must be at least 20 characters");
      return;
    }
    setCreating(true);
    try {
      // Strip empty optional strings so backend doesn't reject ""
      const payload: AdminJobCreate = { ...form };
      (Object.keys(payload) as (keyof AdminJobCreate)[]).forEach((k) => {
        if (payload[k] === "") delete payload[k as keyof AdminJobCreate];
      });
      await admin.createJob(token, payload);
      notify.custom.success("Job posted.");
      setForm(EMPTY_FORM);
      setShowForm(false);
      load();
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Failed to create job");
    } finally {
      setCreating(false);
    }
  };

  // Pull the full job (admin row doesn't include description / apply_url /
  // apply_email) and prefill the edit form. Closes the create form if open
  // so there's only ever one form visible.
  const onStartEdit = async (job: AdminJobRow) => {
    setEditingId(job.id);
    setShowForm(false);
    setEditLoading(true);
    try {
      const full = await jobsApi.get(job.id);
      setEditForm({
        title: full.title ?? "",
        company: full.company ?? "",
        location: full.location ?? "",
        description: full.description ?? "",
        source: (full.source as AdminJobCreate["source"]) ?? "manual",
        apply_url: full.apply_url ?? "",
        apply_email: full.apply_email ?? "",
        closing_date: full.closing_date ? full.closing_date.slice(0, 10) : "",
      });
    } catch (e) {
      notify.error(
        e instanceof Error ? e.message : "Failed to load job for editing"
      );
      setEditingId(null);
    } finally {
      setEditLoading(false);
    }
  };

  const onSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingId) return;
    if (!editForm.title || editForm.title.length < 5) {
      notify.error("Title must be at least 5 characters");
      return;
    }
    if (!editForm.description || editForm.description.length < 20) {
      notify.error("Description must be at least 20 characters");
      return;
    }
    setEditSaving(true);
    try {
      // Strip empty-string optionals so the PATCH doesn't nullify fields
      // we don't intend to change. The backend treats missing keys as
      // "leave alone" and explicit nulls as "clear".
      const payload: Partial<AdminJobCreate> = { ...editForm };
      (Object.keys(payload) as (keyof AdminJobCreate)[]).forEach((k) => {
        if (payload[k] === "") delete payload[k];
      });
      await admin.updateJob(token, editingId, payload);
      notify.custom.success("Job updated.");
      setEditingId(null);
      setEditForm(EMPTY_FORM);
      load();
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Update failed");
    } finally {
      setEditSaving(false);
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

  return (
    <Card>
      <CardContent className="p-0">
        <div className="flex flex-wrap gap-2 p-3 border-b border-border items-center">
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
          <Button
            type="button"
            size="sm"
            className="min-h-9 ml-auto"
            disabled={editingId !== null}
            onClick={() => {
              // Close edit mode if it was open, so we never show both
              // forms simultaneously.
              setEditingId(null);
              setShowForm((v) => !v);
            }}
          >
            {showForm ? "Cancel" : "Post a job"}
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
        </div>

        {showForm && (
          <form onSubmit={onCreate} className="p-4 grid sm:grid-cols-2 gap-3 border-b border-border">
            <Input
              placeholder="Title (min 5 chars)"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              required
            />
            <Input
              placeholder="Company"
              value={form.company}
              onChange={(e) => setForm({ ...form, company: e.target.value })}
            />
            <Input
              placeholder="Location (e.g. Lusaka)"
              value={form.location}
              onChange={(e) => setForm({ ...form, location: e.target.value })}
            />
            <select
              className="h-9 rounded-md border border-input bg-background px-2 text-sm"
              value={form.source}
              onChange={(e) =>
                setForm({ ...form, source: e.target.value as AdminJobCreate["source"] })
              }
            >
              <option value="manual">manual</option>
              <option value="partner">partner</option>
              <option value="scraper">scraper</option>
              <option value="ocr">ocr</option>
            </select>
            <Input
              placeholder="Apply URL"
              value={form.apply_url}
              onChange={(e) => setForm({ ...form, apply_url: e.target.value })}
            />
            <Input
              placeholder="Apply email"
              type="email"
              value={form.apply_email}
              onChange={(e) => setForm({ ...form, apply_email: e.target.value })}
            />
            <Input
              placeholder="Closing date (YYYY-MM-DD)"
              type="date"
              value={form.closing_date}
              onChange={(e) => setForm({ ...form, closing_date: e.target.value })}
            />
            <textarea
              className="sm:col-span-2 min-h-[110px] rounded-md border border-input bg-background p-2 text-sm"
              placeholder="Description (min 20 chars)"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              required
            />
            <div className="sm:col-span-2 flex gap-2 justify-end">
              <Button type="submit" size="sm" disabled={creating}>
                {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : "Post job"}
              </Button>
            </div>
          </form>
        )}

        {/* Edit form — same fields as create, but PATCHes the row id and
            closes on save instead of resetting. Hidden until user clicks
            "Edit" on a row. */}
        {editingId && (
          <form
            onSubmit={onSaveEdit}
            className="p-4 grid sm:grid-cols-2 gap-3 border-b border-border bg-muted/30"
          >
            <div className="sm:col-span-2 flex items-baseline justify-between">
              <h4 className="text-sm font-medium">
                {editLoading ? "Loading job…" : `Editing job ${editingId.slice(0, 8)}…`}
              </h4>
              <button
                type="button"
                className="text-xs text-muted-foreground hover:underline"
                onClick={() => {
                  setEditingId(null);
                  setEditForm(EMPTY_FORM);
                }}
              >
                Cancel
              </button>
            </div>
            <Input
              placeholder="Title (min 5 chars)"
              value={editForm.title}
              onChange={(e) => setEditForm({ ...editForm, title: e.target.value })}
              disabled={editLoading}
              required
            />
            <Input
              placeholder="Company"
              value={editForm.company}
              onChange={(e) => setEditForm({ ...editForm, company: e.target.value })}
              disabled={editLoading}
            />
            <Input
              placeholder="Location (e.g. Lusaka)"
              value={editForm.location}
              onChange={(e) => setEditForm({ ...editForm, location: e.target.value })}
              disabled={editLoading}
            />
            <select
              className="h-9 rounded-md border border-input bg-background px-2 text-sm"
              value={editForm.source}
              onChange={(e) =>
                setEditForm({ ...editForm, source: e.target.value as AdminJobCreate["source"] })
              }
              disabled={editLoading}
            >
              <option value="manual">manual</option>
              <option value="partner">partner</option>
              <option value="scraper">scraper</option>
              <option value="ocr">ocr</option>
            </select>
            <Input
              placeholder="Apply URL"
              value={editForm.apply_url}
              onChange={(e) => setEditForm({ ...editForm, apply_url: e.target.value })}
              disabled={editLoading}
            />
            <Input
              placeholder="Apply email"
              type="email"
              value={editForm.apply_email}
              onChange={(e) => setEditForm({ ...editForm, apply_email: e.target.value })}
              disabled={editLoading}
            />
            <Input
              placeholder="Closing date (YYYY-MM-DD)"
              type="date"
              value={editForm.closing_date}
              onChange={(e) => setEditForm({ ...editForm, closing_date: e.target.value })}
              disabled={editLoading}
            />
            <textarea
              className="sm:col-span-2 min-h-[110px] rounded-md border border-input bg-background p-2 text-sm"
              placeholder="Description (min 20 chars)"
              value={editForm.description}
              onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
              disabled={editLoading}
              required
            />
            <div className="sm:col-span-2 flex gap-2 justify-end">
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => {
                  setEditingId(null);
                  setEditForm(EMPTY_FORM);
                }}
                disabled={editSaving}
              >
                Cancel
              </Button>
              <Button type="submit" size="sm" disabled={editSaving || editLoading}>
                {editSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : "Save changes"}
              </Button>
            </div>
          </form>
        )}

        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Title</TableHead>
                <TableHead>Company</TableHead>
                <TableHead>Source</TableHead>
                <TableHead>Quality</TableHead>
                <TableHead>Active</TableHead>
                <TableHead>Closes</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {loading && (
                <SkeletonTableRows
                  rows={5}
                  widths={["w-40", "w-32", "w-12", "w-8", "w-16", "w-20", "w-24"]}
                />
              )}
              {!loading && data.length === 0 && (
                <TableRow>
                  <TableCell colSpan={7} className="text-sm text-muted-foreground">
                    No jobs match this filter.
                  </TableCell>
                </TableRow>
              )}
              {!loading &&
                data.map((j) => (
                  <TableRow key={j.id}>
                    <TableCell className="max-w-xs truncate" title={j.title}>{j.title}</TableCell>
                    <TableCell>{j.company || <span className="text-muted-foreground">—</span>}</TableCell>
                    <TableCell className="text-xs">{j.source}</TableCell>
                    <TableCell className="tabular-nums">{j.quality_score}</TableCell>
                    <TableCell>
                      {j.is_active ? (
                        <Badge variant="default">active</Badge>
                      ) : (
                        <Badge variant="secondary">inactive</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">{formatDate(j.closing_date)}</TableCell>
                    <TableCell className="text-right">
                      <div className="inline-flex gap-1">
                        <Button
                          size="sm"
                          variant="outline"
                          className="min-h-8 h-8 px-2 text-xs"
                          disabled={editLoading || editingId === j.id}
                          onClick={() => onStartEdit(j)}
                        >
                          {editingId === j.id && editLoading ? "…" : "Edit"}
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
                      </div>
                    </TableCell>
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
