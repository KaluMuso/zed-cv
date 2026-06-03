"use client";

import { useCallback, useState } from "react";
import { useRouter } from "next/navigation";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { TagInput } from "@/components/TagInput";
import { admin, cv as cvApi } from "@/lib/api";
import type { AdminJobCreatePayload } from "./types";
import { notify } from "@/lib/toast";
import { MarkdownDescriptionField } from "./MarkdownDescriptionField";
import {
  EMPLOYMENT_TYPES,
  WORK_ARRANGEMENTS,
} from "./job-enums";

const ZAMBIAN_PHONE_RE = /^\+260[0-9]{9}$/;

const JOB_CATEGORIES = [
  "Accounting",
  "Sales",
  "Marketing",
  "Engineering",
  "Human Resources",
  "Administration",
  "Healthcare",
  "Education",
  "Logistics",
  "Other",
] as const;

const SOURCE_PLATFORMS = [
  "Manual",
  "GoZambia",
  "JobWebZambia",
  "JobSearchZambia",
  "WhatsApp",
  "Other",
] as const;

const formSchema = z
  .object({
    title: z.string().trim().min(1, "Title is required"),
    company: z.string().trim().min(1, "Company is required"),
    location: z.string().trim().min(1, "Location is required"),
    employment_type: z.enum([
      "full_time",
      "part_time",
      "contract",
      "internship",
      "freelance",
      "temporary",
    ]),
    work_arrangement: z.enum(["on_site", "hybrid", "remote"]),
    apply_url: z.string().optional(),
    apply_email: z.string().optional(),
    contact_phone: z.string().optional(),
    source_url: z.string().trim().min(1, "Source URL is required"),
    description_md: z.string().trim().min(20, "Description must be at least 20 characters"),
    category: z.string().optional(),
    source_platform: z.string().optional(),
  })
  .superRefine((data, ctx) => {
    const url = data.apply_url?.trim();
    const email = data.apply_email?.trim();
    const phone = data.contact_phone?.trim();
    if (!url && !email && !phone) {
      ctx.addIssue({
        code: "custom",
        message: "Provide apply URL, apply email, or contact phone",
        path: ["apply_url"],
      });
    }
    if (url && email) {
      ctx.addIssue({
        code: "custom",
        message: "Provide apply URL or apply email, not both",
        path: ["apply_email"],
      });
    }
    if (phone && !ZAMBIAN_PHONE_RE.test(phone)) {
      ctx.addIssue({
        code: "custom",
        message: "Phone must be E.164 +260XXXXXXXXX",
        path: ["contact_phone"],
      });
    }
  });

type AdminJobManualFormProps = {
  token: string;
};

export function AdminJobManualForm({ token }: AdminJobManualFormProps) {
  const router = useRouter();
  const [submitting, setSubmitting] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [location, setLocation] = useState("");
  const [employmentType, setEmploymentType] =
    useState<AdminJobCreatePayload["employment_type"]>("full_time");
  const [workArrangement, setWorkArrangement] =
    useState<AdminJobCreatePayload["work_arrangement"]>("on_site");
  const [applyUrl, setApplyUrl] = useState("");
  const [applyEmail, setApplyEmail] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [sourceUrl, setSourceUrl] = useState("");
  const [closingDate, setClosingDate] = useState("");
  const [postedAt, setPostedAt] = useState(() => new Date().toISOString().slice(0, 10));
  const [salaryMin, setSalaryMin] = useState("");
  const [salaryMax, setSalaryMax] = useState("");
  const [descriptionMd, setDescriptionMd] = useState("");
  const [requirements, setRequirements] = useState<string[]>([]);
  const [skillsRequired, setSkillsRequired] = useState<string[]>([]);
  const [category, setCategory] = useState<string>(JOB_CATEGORIES[0]);
  const [sourcePlatform, setSourcePlatform] = useState<string>("Manual");

  const [skillSuggestions, setSkillSuggestions] = useState<string[]>([]);

  const loadSkillSuggestions = useCallback(
    async (query: string) => {
      if (!query.trim()) return;
      try {
        const res = await cvApi.suggestSkills(token, query);
        setSkillSuggestions(res.skills.map((s) => s.name));
      } catch {
        setSkillSuggestions([]);
      }
    },
    [token],
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = formSchema.safeParse({
      title,
      company,
      location,
      employment_type: employmentType,
      work_arrangement: workArrangement,
      apply_url: applyUrl,
      apply_email: applyEmail,
      contact_phone: contactPhone,
      source_url: sourceUrl,
      description_md: descriptionMd,
      category,
      source_platform: sourcePlatform,
    });
    if (!parsed.success) {
      const next: Record<string, string> = {};
      for (const issue of parsed.error.issues) {
        const key = String(issue.path[0] ?? "_form");
        if (!next[key]) next[key] = issue.message;
      }
      setErrors(next);
      return;
    }
    setErrors({});
    setSubmitting(true);
    try {
      const salaryMinNgwee = salaryMin.trim()
        ? Math.round(parseFloat(salaryMin) * 100)
        : undefined;
      const salaryMaxNgwee = salaryMax.trim()
        ? Math.round(parseFloat(salaryMax) * 100)
        : undefined;
      const payload: AdminJobCreatePayload = {
        title: title.trim(),
        company: company.trim(),
        location: location.trim(),
        description: descriptionMd.trim(),
        employment_type: employmentType,
        work_arrangement: workArrangement,
        apply_url: applyUrl.trim() || null,
        apply_email: applyEmail.trim() || null,
        contact_phone: contactPhone.trim() || null,
        source_url: sourceUrl.trim(),
        source: "manual",
        source_platform: sourcePlatform,
        closing_date: closingDate || null,
        posted_at: postedAt || null,
        salary_min: salaryMinNgwee,
        salary_max: salaryMaxNgwee,
        requirements: requirements.length ? requirements : undefined,
        skills_required: skillsRequired.length ? skillsRequired : undefined,
        application_instructions: category
          ? `Category: ${category}`
          : undefined,
      };
      const job = await admin.createJob(
        token,
        payload as Parameters<typeof admin.createJob>[1],
      );
      notify.success("Job created");
      router.push(`/admin/jobs/${job.id}`);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Could not create job";
      notify.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-8 max-w-5xl">
      <section className="grid sm:grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-medium">Title *</label>
          <Input value={title} onChange={(e) => setTitle(e.target.value)} />
          {errors.title && <p className="text-xs text-destructive mt-1">{errors.title}</p>}
        </div>
        <div>
          <label className="text-sm font-medium">Company *</label>
          <Input value={company} onChange={(e) => setCompany(e.target.value)} />
          {errors.company && (
            <p className="text-xs text-destructive mt-1">{errors.company}</p>
          )}
        </div>
        <div>
          <label className="text-sm font-medium">Location *</label>
          <Input value={location} onChange={(e) => setLocation(e.target.value)} list="admin-job-locations" />
          <datalist id="admin-job-locations">
            {["Lusaka", "Ndola", "Kitwe", "Livingstone", "Remote"].map((loc) => (
              <option key={loc} value={loc} />
            ))}
          </datalist>
        </div>
        <div>
          <label className="text-sm font-medium">Category</label>
          <select
            className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
          >
            {JOB_CATEGORIES.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-sm font-medium">Employment type *</label>
          <select
            className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
            value={employmentType ?? "full_time"}
            onChange={(e) =>
              setEmploymentType(e.target.value as AdminJobCreatePayload["employment_type"])
            }
          >
            {EMPLOYMENT_TYPES.map((t) => (
              <option key={t.value} value={t.value}>
                {t.label}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-sm font-medium">Setup *</label>
          <select
            className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
            value={workArrangement ?? "on_site"}
            onChange={(e) =>
              setWorkArrangement(e.target.value as AdminJobCreatePayload["work_arrangement"])
            }
          >
            {WORK_ARRANGEMENTS.map((w) => (
              <option key={w.value} value={w.value}>
                {w.label}
              </option>
            ))}
          </select>
        </div>
      </section>

      <section className="grid sm:grid-cols-2 gap-4">
        <div>
          <label className="text-sm font-medium">Apply URL</label>
          <Input value={applyUrl} onChange={(e) => setApplyUrl(e.target.value)} type="url" />
        </div>
        <div>
          <label className="text-sm font-medium">Apply email</label>
          <Input value={applyEmail} onChange={(e) => setApplyEmail(e.target.value)} type="email" />
        </div>
        <div>
          <label className="text-sm font-medium">Contact phone (+260)</label>
          <Input
            value={contactPhone}
            onChange={(e) => setContactPhone(e.target.value)}
            placeholder="+260971234567"
          />
          {errors.contact_phone && (
            <p className="text-xs text-destructive mt-1">{errors.contact_phone}</p>
          )}
        </div>
        <div>
          <label className="text-sm font-medium">Source URL *</label>
          <Input value={sourceUrl} onChange={(e) => setSourceUrl(e.target.value)} type="url" />
          {errors.source_url && (
            <p className="text-xs text-destructive mt-1">{errors.source_url}</p>
          )}
        </div>
        <div>
          <label className="text-sm font-medium">Source platform</label>
          <select
            className="w-full h-10 rounded-md border border-input bg-background px-3 text-sm"
            value={sourcePlatform}
            onChange={(e) => setSourcePlatform(e.target.value)}
          >
            {SOURCE_PLATFORMS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-sm font-medium">Closing date</label>
          <Input type="date" value={closingDate} onChange={(e) => setClosingDate(e.target.value)} />
        </div>
        <div>
          <label className="text-sm font-medium">Posted at</label>
          <Input type="date" value={postedAt} onChange={(e) => setPostedAt(e.target.value)} />
        </div>
        <div>
          <label className="text-sm font-medium">Salary min (ZMW)</label>
          <Input value={salaryMin} onChange={(e) => setSalaryMin(e.target.value)} inputMode="decimal" />
        </div>
        <div>
          <label className="text-sm font-medium">Salary max (ZMW)</label>
          <Input value={salaryMax} onChange={(e) => setSalaryMax(e.target.value)} inputMode="decimal" />
        </div>
      </section>

      {errors.apply_url && (
        <p className="text-sm text-destructive">{errors.apply_url}</p>
      )}

      <MarkdownDescriptionField value={descriptionMd} onChange={setDescriptionMd} />
      {errors.description_md && (
        <p className="text-sm text-destructive">{errors.description_md}</p>
      )}

      <div>
        <label className="text-sm font-medium block mb-2">Requirements</label>
        <TagInput
          value={requirements}
          onChange={setRequirements}
          placeholder="Add requirement"
          max={30}
          inputId="admin-job-requirements"
        />
      </div>

      <div>
        <label className="text-sm font-medium block mb-2">Skills required</label>
        <TagInput
          value={skillsRequired}
          onChange={setSkillsRequired}
          suggestions={skillSuggestions}
          placeholder="Type a skill"
          max={50}
          inputId="admin-job-skills"
          ariaLabel="Skills required"
        />
        <Input
          className="mt-2"
          placeholder="Search canonical skills…"
          onChange={(e) => void loadSkillSuggestions(e.target.value)}
        />
      </div>

      <div className="flex gap-3">
        <Button type="submit" disabled={submitting}>
          {submitting ? "Creating…" : "Create job"}
        </Button>
        <Button type="button" variant="outline" onClick={() => router.push("/admin/jobs")}>
          Cancel
        </Button>
      </div>
    </form>
  );
}
