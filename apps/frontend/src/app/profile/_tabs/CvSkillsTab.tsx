"use client";

import { useCallback, useRef, useState } from "react";
import { cv as cvApi, ApiError, type CVSections, type UserProfile } from "@/lib/api";
import { SkillBadge } from "@/components/SkillBadge";
import { Icon } from "@/components/ui/Icon";

const VALID_TYPES = [
  "application/pdf",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "image/jpeg",
  "image/png",
];

export function CvSkillsTab({
  token,
  profileData,
  onUploaded,
}: {
  token: string;
  profileData: UserProfile;
  onUploaded: () => void;
}) {
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");
  const [uploadErrorCode, setUploadErrorCode] = useState<string | null>(null);
  const [showScanFix, setShowScanFix] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleUpload = useCallback(
    async (file: File) => {
      if (!VALID_TYPES.includes(file.type)) {
        setUploadMsg("Please upload a PDF, Word document, or image.");
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        setUploadMsg("File must be under 10MB.");
        return;
      }
      setUploading(true);
      setUploadMsg("");
      setUploadErrorCode(null);
      setShowScanFix(false);
      try {
        const result = await cvApi.upload(token, file);
        // parsed_skills is the canonical field per docs/openapi.yaml.
        // 202 (queued) responses won't include it; the ?? 0 covers that case.
        const skillsCount = result?.parsed_skills?.length ?? 0;
        if (result?.queued) {
          setUploadMsg(
            "CV queued — we'll process it as soon as AI capacity is back."
          );
        } else {
          setUploadMsg(`CV uploaded! ${skillsCount} skills extracted.`);
        }
        onUploaded();
      } catch (err) {
        let msg: string;
        let code: string | null = null;
        if (err instanceof TypeError && /fetch/i.test(err.message)) {
          msg = "Couldn't reach the server. Please check your connection and try again.";
        } else if (err instanceof ApiError) {
          msg = err.detail || "Upload failed";
          code = err.code ?? null;
        } else if (err instanceof Error) {
          msg = err.message;
        } else {
          msg = "Upload failed";
        }
        setUploadMsg(msg);
        setUploadErrorCode(code);
      } finally {
        setUploading(false);
      }
    },
    [token, onUploaded]
  );

  return (
    <>
      <div className="card p-6">
        <div className="eyebrow mb-4">
          {profileData.cv_uploaded ? "Your CV" : "Upload your CV"}
        </div>

        {profileData.cv_uploaded && (
          <div
            className="flex items-center gap-3 p-3 rounded-lg mb-4"
            style={{ background: "var(--bg-2)", border: "1px solid var(--line)" }}
          >
            <Icon name="file" size={20} />
            <div className="flex-1 min-w-0">
              <div className="text-sm font-medium truncate">CV uploaded</div>
              <div className="text-xs" style={{ color: "var(--muted)" }}>
                {(profileData.skills ?? []).length} skills extracted
              </div>
            </div>
            <button onClick={() => fileRef.current?.click()} className="btn btn-ghost btn-sm">
              Replace
            </button>
          </div>
        )}

        {/* Hidden file input — always rendered so the Replace button above
            can trigger it, even when the dropzone below isn't shown. */}
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleUpload(file);
          }}
          className="hidden"
        />

        {/* Dropzone is only shown when no CV is uploaded yet. With a CV in
            place, the "Replace" button above is the canonical affordance —
            showing both was confusing (users wondered if their upload
            actually succeeded). */}
        {!profileData.cv_uploaded && (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragActive(false);
            const file = e.dataTransfer.files[0];
            if (file) handleUpload(file);
          }}
          onClick={() => fileRef.current?.click()}
          className="cursor-pointer p-8 text-center rounded-xl transition"
          style={{
            border: dragActive ? "2px dashed var(--green-500)" : "2px dashed var(--line-2)",
            background: dragActive ? "var(--green-50)" : "transparent",
          }}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === "Enter") fileRef.current?.click();
          }}
        >
          {uploading ? (
            <div className="flex items-center justify-center gap-2">
              <span
                className="spinner"
                style={{ borderTopColor: "var(--green-500)", borderColor: "var(--line-2)" }}
              />
              <span className="text-sm font-medium" style={{ color: "var(--green-700)" }}>
                Uploading...
              </span>
            </div>
          ) : (
            <>
              <div
                className="w-12 h-12 mx-auto mb-3 rounded-xl flex items-center justify-center"
                style={{ background: "var(--bg-2)", color: "var(--muted)" }}
              >
                <Icon name="upload" size={22} />
              </div>
              <p className="text-sm" style={{ color: "var(--ink-2)" }}>
                Drag and drop your CV here, or{" "}
                <span className="font-medium" style={{ color: "var(--green-700)" }}>
                  browse
                </span>
              </p>
              <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>
                PDF, Word, or image (max 10MB)
              </p>
            </>
          )}
        </div>
        )}

        {uploading && profileData.cv_uploaded && (
          <div className="flex items-center justify-center gap-2 mt-4">
            <span
              className="spinner"
              style={{ borderTopColor: "var(--green-500)", borderColor: "var(--line-2)" }}
            />
            <span className="text-sm font-medium" style={{ color: "var(--green-700)" }}>
              Replacing your CV…
            </span>
          </div>
        )}

        {uploadMsg && (
          <div className="mt-3">
            <p
              className="text-sm"
              style={{
                color:
                  uploadMsg.includes("failed") ||
                  uploadMsg.includes("Please") ||
                  uploadMsg.includes("couldn't") ||
                  uploadMsg.includes("Couldn't") ||
                  uploadErrorCode === "image_scanned_pdf"
                    ? "var(--danger)"
                    : "var(--success)",
              }}
            >
              {uploadMsg}
            </p>
            {uploadErrorCode === "image_scanned_pdf" && (
              <div className="mt-2 text-sm" style={{ color: "var(--ink-2)" }}>
                <button
                  type="button"
                  className="font-medium underline"
                  style={{ color: "var(--green-700)" }}
                  onClick={() => setShowScanFix((v) => !v)}
                >
                  How to fix
                </button>
                {showScanFix && (
                  <ul className="mt-2 ml-4 list-disc space-y-1 text-xs" style={{ color: "var(--muted)" }}>
                    <li>Re-export your CV from Word or Google Docs as a PDF (not a photo scan).</li>
                    <li>
                      If you only have a paper copy, scan with OCR enabled (Adobe Scan, Microsoft Lens, or
                      Google Drive scan).
                    </li>
                    <li>Upload a DOCX or a searchable PDF — we need selectable text, not just an image.</li>
                  </ul>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="card p-6">
        <div className="eyebrow mb-4">Extracted skills</div>
        {(profileData.skills ?? []).length === 0 ? (
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Upload your CV to automatically extract skills.
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {(profileData.skills ?? []).map((skill) => (
              <SkillBadge key={skill} skill={skill} matched />
            ))}
          </div>
        )}
      </div>

      {/* Structured CV body (task #59). Rendered only when the backend
          supplied the new "sections" shape — legacy parsed_data rows
          without it simply show nothing here, which is the same
          behaviour as before this slice. Read-only on purpose; edit
          UI for these sections is a separate task. */}
      <CVSectionsReadView sections={profileData.cv_sections ?? null} />
    </>
  );
}


// ─── task #59: structured CV sections read view ────────────────────────

const SECTION_DEFS: ReadonlyArray<{
  key: keyof CVSections;
  label: string;
  count: (s: CVSections) => number;
}> = [
  { key: "professional_summary", label: "Professional summary", count: (s) => (s.professional_summary?.text ? 1 : 0) },
  { key: "work_experience", label: "Work experience", count: (s) => s.work_experience.length },
  { key: "education", label: "Education", count: (s) => s.education.length },
  { key: "certifications", label: "Certifications", count: (s) => s.certifications.length },
  { key: "languages", label: "Languages", count: (s) => s.languages.length },
  { key: "projects", label: "Projects", count: (s) => s.projects.length },
  { key: "achievements", label: "Achievements", count: (s) => s.achievements.length },
  { key: "publications", label: "Publications", count: (s) => s.publications.length },
  { key: "memberships", label: "Memberships", count: (s) => s.memberships.length },
  { key: "volunteer_work", label: "Volunteer work", count: (s) => s.volunteer_work.length },
  { key: "references", label: "References", count: (s) => s.references.length },
];

function CVSectionsReadView({ sections }: { sections: CVSections | null }) {
  // Open the most informative section by default so first-time viewers
  // see real content without clicking. Work experience is the most useful
  // default; if it's empty, fall back to whichever has the highest count.
  const defaultOpen = (() => {
    if (!sections) return null as string | null;
    if (sections.work_experience.length > 0) return "work_experience";
    for (const def of SECTION_DEFS) {
      if (def.count(sections) > 0) return String(def.key);
    }
    return null;
  })();
  const [openKey, setOpenKey] = useState<string | null>(defaultOpen);

  if (!sections) return null;

  const visible = SECTION_DEFS.filter((d) => d.count(sections) > 0);
  if (visible.length === 0) return null;

  return (
    <div className="card p-6">
      <div className="flex items-center justify-between mb-4 gap-3">
        <div>
          <div className="eyebrow">Your CV at a glance</div>
          <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>
            Parsed from your uploaded CV. Click a section to expand.
          </p>
        </div>
      </div>

      <div className="space-y-2">
        {visible.map((def) => {
          const key = String(def.key);
          const open = openKey === key;
          const n = def.count(sections);
          return (
            <div
              key={key}
              className="rounded-md"
              style={{ border: "1px solid var(--line)" }}
            >
              <button
                onClick={() => setOpenKey(open ? null : key)}
                className="w-full flex items-center justify-between px-3 py-2 text-left"
                style={{ background: open ? "var(--bg-2)" : "transparent" }}
                type="button"
              >
                <span className="text-sm font-medium">{def.label}</span>
                <span
                  className="text-xs flex items-center gap-2"
                  style={{ color: "var(--muted)" }}
                >
                  <span className="tabular-nums">{n}</span>
                  <Icon name={open ? "chevronDown" : "chevronRight"} size={14} />
                </span>
              </button>
              {open && (
                <div className="px-3 py-3" style={{ borderTop: "1px solid var(--line)" }}>
                  <SectionBody sections={sections} sectionKey={def.key} />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {sections.header && (sections.header.linkedin_url || sections.header.portfolio_url || sections.header.github_url) && (
        <div className="mt-4 pt-4 flex flex-wrap gap-3" style={{ borderTop: "1px solid var(--line)" }}>
          {sections.header.linkedin_url && (
            <a
              href={sections.header.linkedin_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs"
              style={{ color: "var(--green-700)" }}
            >
              LinkedIn ↗
            </a>
          )}
          {sections.header.portfolio_url && (
            <a
              href={sections.header.portfolio_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs"
              style={{ color: "var(--green-700)" }}
            >
              Portfolio ↗
            </a>
          )}
          {sections.header.github_url && (
            <a
              href={sections.header.github_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs"
              style={{ color: "var(--green-700)" }}
            >
              GitHub ↗
            </a>
          )}
        </div>
      )}
    </div>
  );
}

function SectionBody({
  sections,
  sectionKey,
}: {
  sections: CVSections;
  sectionKey: keyof CVSections;
}) {
  switch (sectionKey) {
    case "professional_summary":
      return (
        <p className="text-sm" style={{ color: "var(--ink-2)" }}>
          {sections.professional_summary?.text}
        </p>
      );
    case "work_experience":
      return (
        <ul className="space-y-3">
          {sections.work_experience.map((w, i) => (
            <li key={i}>
              <div className="text-sm font-medium">
                {w.title}
                {w.company && (
                  <span style={{ color: "var(--muted)", fontWeight: 400 }}>
                    {" · "}
                    {w.company}
                  </span>
                )}
              </div>
              <div className="text-xs" style={{ color: "var(--muted)" }}>
                {[w.start_date, w.end_date ?? "Present"].filter(Boolean).join(" – ")}
                {w.location ? ` · ${w.location}` : ""}
              </div>
              {w.achievements.length > 0 && (
                <ul className="mt-1.5 ml-4 text-sm list-disc" style={{ color: "var(--ink-2)" }}>
                  {w.achievements.slice(0, 6).map((a, j) => (
                    <li key={j}>{a}</li>
                  ))}
                </ul>
              )}
            </li>
          ))}
        </ul>
      );
    case "education":
      return (
        <ul className="space-y-2">
          {sections.education.map((e, i) => (
            <li key={i} className="text-sm">
              <span className="font-medium">{e.degree}</span>
              {e.institution && (
                <span style={{ color: "var(--muted)" }}>{" · "}{e.institution}</span>
              )}
              {(e.start_date || e.end_date) && (
                <div className="text-xs" style={{ color: "var(--muted)" }}>
                  {[e.start_date, e.end_date].filter(Boolean).join(" – ")}
                  {e.location ? ` · ${e.location}` : ""}
                </div>
              )}
            </li>
          ))}
        </ul>
      );
    case "certifications":
      return (
        <ul className="space-y-1">
          {sections.certifications.map((c, i) => (
            <li key={i} className="text-sm">
              <span className="font-medium">{c.name}</span>
              {c.issuer && <span style={{ color: "var(--muted)" }}>{" · "}{c.issuer}</span>}
              {c.year && <span style={{ color: "var(--muted)" }}>{" · "}{c.year}</span>}
            </li>
          ))}
        </ul>
      );
    case "languages":
      return (
        <div className="flex flex-wrap gap-1.5">
          {sections.languages.map((l, i) => (
            <span
              key={i}
              className="tag tag-mono text-xs"
              title={l.proficiency}
            >
              {l.name} <span style={{ color: "var(--muted)" }}>({l.proficiency})</span>
            </span>
          ))}
        </div>
      );
    case "projects":
      return (
        <ul className="space-y-2">
          {sections.projects.map((p, i) => (
            <li key={i} className="text-sm">
              <span className="font-medium">{p.name}</span>
              {p.role && <span style={{ color: "var(--muted)" }}>{" — "}{p.role}</span>}
              {p.outcome && (
                <div className="text-xs mt-0.5" style={{ color: "var(--ink-2)" }}>
                  {p.outcome}
                </div>
              )}
              {p.technologies.length > 0 && (
                <div className="text-xs mt-0.5" style={{ color: "var(--muted)" }}>
                  Stack: {p.technologies.join(", ")}
                </div>
              )}
            </li>
          ))}
        </ul>
      );
    case "achievements":
      return (
        <ul className="space-y-1">
          {sections.achievements.map((a, i) => (
            <li key={i} className="text-sm">
              {a.title}
              {a.year && <span style={{ color: "var(--muted)" }}>{" · "}{a.year}</span>}
            </li>
          ))}
        </ul>
      );
    case "publications":
      return (
        <ul className="space-y-1.5">
          {sections.publications.map((p, i) => (
            <li key={i} className="text-sm">
              {p.url ? (
                <a
                  href={p.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: "var(--green-700)" }}
                >
                  {p.title} ↗
                </a>
              ) : (
                <span className="font-medium">{p.title}</span>
              )}
              {p.venue && <span style={{ color: "var(--muted)" }}>{" · "}{p.venue}</span>}
              {p.year && <span style={{ color: "var(--muted)" }}>{" · "}{p.year}</span>}
            </li>
          ))}
        </ul>
      );
    case "memberships":
      return (
        <ul className="space-y-1">
          {sections.memberships.map((m, i) => (
            <li key={i} className="text-sm">
              <span className="font-medium">{m.organisation}</span>
              {m.role && <span style={{ color: "var(--muted)" }}>{" · "}{m.role}</span>}
              {(m.year_started || m.year_ended) && (
                <span style={{ color: "var(--muted)" }}>
                  {" · "}
                  {[m.year_started, m.year_ended].filter(Boolean).join(" – ")}
                </span>
              )}
            </li>
          ))}
        </ul>
      );
    case "volunteer_work":
      return (
        <ul className="space-y-2">
          {sections.volunteer_work.map((v, i) => (
            <li key={i} className="text-sm">
              <span className="font-medium">{v.organisation}</span>
              {v.role && <span style={{ color: "var(--muted)" }}>{" · "}{v.role}</span>}
              {v.description && (
                <div className="text-xs mt-0.5" style={{ color: "var(--ink-2)" }}>
                  {v.description}
                </div>
              )}
            </li>
          ))}
        </ul>
      );
    case "references":
      return (
        <ul className="space-y-2">
          {sections.references.map((r, i) => (
            <li key={i} className="text-sm">
              <span className="font-medium">{r.name}</span>
              {r.title && <span style={{ color: "var(--muted)" }}>{", "}{r.title}</span>}
              {r.organisation && (
                <div className="text-xs" style={{ color: "var(--muted)" }}>
                  {r.organisation}
                </div>
              )}
              {(r.phone || r.email) && (
                <div className="text-xs" style={{ color: "var(--muted)" }}>
                  {[r.phone, r.email].filter(Boolean).join(" · ")}
                </div>
              )}
            </li>
          ))}
        </ul>
      );
    default:
      return null;
  }
}
