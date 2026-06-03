"use client";

import { useCallback, useEffect, useState } from "react";
import { Loader2 } from "lucide-react";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TagInput } from "@/components/TagInput";
import {
  admin,
  cv as cvApi,
  jobs as jobsApi,
  type AdminJobCreate,
  type EmploymentType,
  type ScrapingSourceEntry,
  type WorkArrangement,
} from "@/lib/api";
import { notify } from "@/lib/toast";
import { MarkdownDescriptionField } from "./MarkdownDescriptionField";
import { EMPLOYMENT_TYPES, WORK_ARRANGEMENTS } from "./job-enums";
import {
  finalizeAdminJobPayload,
  validateAdminJobApplyContact,
} from "./adminJobValidation";

/** Local form state; admin_published is edit-only and must not be sent on POST. */
type AdminJobFormState = AdminJobCreate & { admin_published?: boolean };

const EMPTY_FORM: AdminJobFormState = {
  title: "",
  company: "",
  location: "",
  description: "",
  source: "manual",
  apply_url: "",
  apply_email: "",
  contact_phone: "",
  closing_date: "",
  admin_published: false,
};

function SourcesList({ sources }: { sources: ScrapingSourceEntry[] }) {
  if (!sources.length) return null;
  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <span className="text-muted-foreground">Sources:</span>
      {sources.map((s) => (
        <a
          key={s.url}
          href={s.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-0.5 rounded-md border border-border px-2 py-0.5 hover:bg-muted"
        >
          {s.source_type} ↗
        </a>
      ))}
    </div>
  );
}

type AdminJobFormDialogProps = {
  token: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  mode: "create" | "edit";
  jobId?: string | null;
  onSaved: () => void;
};

export function AdminJobFormDialog({
  token,
  open,
  onOpenChange,
  mode,
  jobId,
  onSaved,
}: AdminJobFormDialogProps) {
  const [form, setForm] = useState<AdminJobFormState>(EMPTY_FORM);
  const [employmentType, setEmploymentType] = useState<EmploymentType>("full_time");
  const [workArrangement, setWorkArrangement] = useState<WorkArrangement>("on_site");
  const [sourceUrl, setSourceUrl] = useState("");
  const [requirements, setRequirements] = useState<string[]>([]);
  const [skillsRequired, setSkillsRequired] = useState<string[]>([]);
  const [skillSuggestions, setSkillSuggestions] = useState<string[]>([]);
  const [editSources, setEditSources] = useState<ScrapingSourceEntry[]>([]);
  const [forcePublish, setForcePublish] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const resetForm = useCallback(() => {
    setForm(EMPTY_FORM);
    setEmploymentType("full_time");
    setWorkArrangement("on_site");
    setSourceUrl("");
    setRequirements([]);
    setSkillsRequired([]);
    setEditSources([]);
    setForcePublish(false);
  }, []);

  useEffect(() => {
    if (!open) return;
    if (mode === "create") {
      resetForm();
      return;
    }
    if (!jobId) return;

    let cancelled = false;
    setLoading(true);
    jobsApi
      .get(jobId)
      .then((full) => {
        if (cancelled) return;
        setForm({
          title: full.title ?? "",
          company: full.company ?? "",
          location: full.location ?? "",
          description: full.description ?? "",
          source: (full.source as AdminJobCreate["source"]) ?? "manual",
          apply_url: full.apply_url ?? "",
          apply_email: full.apply_email ?? "",
          contact_phone: full.contact_phone ?? "",
          closing_date: full.closing_date ? full.closing_date.slice(0, 10) : "",
          admin_published: full.admin_published ?? false,
        });
        setEmploymentType((full.employment_type as EmploymentType | undefined) ?? "full_time");
        setWorkArrangement((full.work_arrangement as WorkArrangement | undefined) ?? "on_site");
        setSourceUrl(full.source_url ?? "");
        setRequirements(full.requirements ?? []);
        setSkillsRequired(full.skills_required ?? []);
        setEditSources(full.scraping_sources ?? []);
        setForcePublish(full.admin_published === true);
      })
      .catch((e) => {
        notify.error(e instanceof Error ? e.message : "Failed to load job");
        onOpenChange(false);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [open, mode, jobId, onOpenChange, resetForm]);

  const loadSkillSuggestions = async (query: string) => {
    if (!query.trim()) return;
    try {
      const res = await cvApi.suggestSkills(token, query);
      setSkillSuggestions(res.skills.map((s) => s.name));
    } catch {
      setSkillSuggestions([]);
    }
  };

  const buildPayload = (): Partial<AdminJobCreate> & { admin_published?: boolean } => {
    const { admin_published: _omit, ...formFields } = form;
    const payload: Partial<AdminJobCreate> = {
      ...formFields,
      employment_type: employmentType,
      work_arrangement: workArrangement,
      source_url: sourceUrl.trim() || undefined,
      requirements: requirements.length ? requirements : undefined,
      skills_required: skillsRequired.length ? skillsRequired : undefined,
    };
    (Object.keys(payload) as (keyof typeof payload)[]).forEach((k) => {
      if (payload[k] === "") delete payload[k];
    });
    return finalizeAdminJobPayload(mode, payload, forcePublish);
  };

  const validate = (): boolean => {
    if (!form.title || form.title.length < 5) {
      notify.error("Title must be at least 5 characters");
      return false;
    }
    if (!form.description || form.description.length < 20) {
      notify.error("Description must be at least 20 characters");
      return false;
    }
    const contactError = validateAdminJobApplyContact(
      form.apply_url,
      form.apply_email,
      form.contact_phone,
    );
    if (contactError) {
      notify.error(contactError);
      return false;
    }
    return true;
  };

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    setSaving(true);
    try {
      const payload = buildPayload();
      if (mode === "create") {
        await admin.createJob(token, payload as AdminJobCreate);
        notify.custom.success("Job posted.");
      } else if (jobId) {
        await admin.updateJob(token, jobId, payload);
        notify.custom.success("Job updated.");
      }
      onOpenChange(false);
      resetForm();
      onSaved();
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{mode === "create" ? "Post a job" : "Edit job"}</DialogTitle>
          <DialogDescription>
            Fields match the jobs table. Description supports Markdown with live preview.
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="flex items-center justify-center py-12 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin mr-2" />
            Loading job…
          </div>
        ) : (
          <form id="admin-job-form" onSubmit={onSubmit} className="grid sm:grid-cols-2 gap-3">
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
            <select
              className="h-9 rounded-md border border-input bg-background px-2 text-sm"
              value={employmentType}
              onChange={(e) => setEmploymentType(e.target.value as EmploymentType)}
            >
              {EMPLOYMENT_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
            <select
              className="h-9 rounded-md border border-input bg-background px-2 text-sm"
              value={workArrangement}
              onChange={(e) => setWorkArrangement(e.target.value as WorkArrangement)}
            >
              {WORK_ARRANGEMENTS.map((w) => (
                <option key={w.value} value={w.value}>
                  {w.label}
                </option>
              ))}
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
              placeholder="Contact phone (+260…)"
              value={form.contact_phone ?? ""}
              onChange={(e) => setForm({ ...form, contact_phone: e.target.value })}
            />
            <Input
              placeholder="Source URL"
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
            />
            <Input
              placeholder="Closing date (YYYY-MM-DD)"
              type="date"
              value={form.closing_date}
              onChange={(e) => setForm({ ...form, closing_date: e.target.value })}
            />
            {mode === "edit" && <SourcesList sources={editSources} />}
            {mode === "edit" && (
              <label className="sm:col-span-2 flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={forcePublish}
                  onChange={(e) => setForcePublish(e.target.checked)}
                />
                Force publish (show on public site without extracted contacts)
              </label>
            )}
            <div className="sm:col-span-2">
              <MarkdownDescriptionField
                value={form.description}
                onChange={(description) => setForm({ ...form, description })}
              />
            </div>
            <div className="sm:col-span-2">
              <label className="text-sm font-medium block mb-2">Requirements</label>
              <TagInput
                value={requirements}
                onChange={setRequirements}
                placeholder="Add requirement"
                max={30}
                inputId="admin-job-modal-requirements"
              />
            </div>
            <div className="sm:col-span-2">
              <label className="text-sm font-medium block mb-2">Skills required</label>
              <TagInput
                value={skillsRequired}
                onChange={setSkillsRequired}
                suggestions={skillSuggestions}
                placeholder="Type a skill"
                max={50}
                inputId="admin-job-modal-skills"
                ariaLabel="Skills required"
              />
              <Input
                className="mt-2"
                placeholder="Search canonical skills…"
                onChange={(e) => void loadSkillSuggestions(e.target.value)}
              />
            </div>
          </form>
        )}

        <DialogFooter>
          <Button type="button" variant="outline" onClick={() => onOpenChange(false)} disabled={saving}>
            Cancel
          </Button>
          <Button type="submit" form="admin-job-form" disabled={saving || loading}>
            {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : mode === "create" ? "Post job" : "Save changes"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
