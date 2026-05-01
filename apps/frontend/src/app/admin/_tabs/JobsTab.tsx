"use client";

import { useCallback, useEffect, useState } from "react";
import { admin, type AdminJobRow, type AdminJobCreate } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { formatDate } from "./shared";

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
      .catch((e) => toast.error(e instanceof Error ? e.message : "Failed to load jobs"))
      .finally(() => setLoading(false));
  }, [token, page, filter]);

  useEffect(() => {
    load();
  }, [load]);

  const onBulkDeactivate = async () => {
    setBulkLoading(true);
    try {
      const r = await admin.bulkDeactivate(token, { expired_only: true });
      toast.success(`Deactivated ${r.deactivated} expired job(s).`);
      load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Bulk action failed");
    } finally {
      setBulkLoading(false);
    }
  };

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title || form.title.length < 5) {
      toast.error("Title must be at least 5 characters");
      return;
    }
    if (!form.description || form.description.length < 20) {
      toast.error("Description must be at least 20 characters");
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
      toast.success("Job posted.");
      setForm(EMPTY_FORM);
      setShowForm(false);
      load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to create job");
    } finally {
      setCreating(false);
    }
  };

  const onToggle = async (job: AdminJobRow) => {
    setBusyId(job.id);
    try {
      await admin.updateJob(token, job.id, { is_active: !job.is_active });
      toast.success(job.is_active ? "Deactivated" : "Activated");
      load();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Toggle failed");
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
            onClick={() => setShowForm((v) => !v)}
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
                <TableRow>
                  <TableCell colSpan={7} className="text-sm text-muted-foreground">Loading…</TableCell>
                </TableRow>
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
                      <Button
                        size="sm"
                        variant="outline"
                        className="min-h-8 h-8 px-2 text-xs"
                        disabled={busyId === j.id}
                        onClick={() => onToggle(j)}
                      >
                        {busyId === j.id ? "…" : j.is_active ? "Deactivate" : "Activate"}
                      </Button>
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
