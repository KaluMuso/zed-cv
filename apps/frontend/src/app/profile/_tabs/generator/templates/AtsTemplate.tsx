"use client";

import type { CVSections } from "@/lib/api";
import type { ParsedCV } from "../parseCv";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";

/**
 * Single-column, no-decoration layout optimised for ATS parsing.
 *
 * Why simple beats pretty here: most Zambian recruiters (and global ones
 * using Greenhouse / Workable / SmartRecruiters) ingest CVs through resume
 * parsers that get confused by columns, icons, and decorative graphics.
 * Black text on white, real headings, real bullets, no clever positioning.
 *
 * Two render paths share the same DOM/CSS:
 *   - cvSections present (task #59): render structured with field-level
 *     fidelity (separate title/company/dates lines, dedicated cert rows).
 *   - cvSections null: fall back to the legacy free-text ParsedCV path
 *     for old generations and post-edit state.
 */
export function AtsTemplate({
  parsed,
  cvSections,
}: {
  parsed: ParsedCV;
  cvSections?: CVSections | null;
}) {
  const { header } = parsed;
  const contactBits = [header.phone, header.email, header.location].filter(Boolean);

  if (cvSections) {
    return (
      <div className="cv-print-root cv-ats">
        <h1>{header.name || "Your Name"}</h1>
        {contactBits.length > 0 && (
          <div className="cv-contact">{contactBits.join("  ·  ")}</div>
        )}
        <StructuredLinksLine header={cvSections.header} />
        <StructuredSections sections={cvSections} />
      </div>
    );
  }

  return (
    <div className="cv-print-root cv-ats">
      <h1>{header.name || "Your Name"}</h1>
      {contactBits.length > 0 && <div className="cv-contact">{contactBits.join("  ·  ")}</div>}
      {parsed.sections.map((s) => (
        <LegacySection key={s.title} title={s.title} body={s.body} />
      ))}
    </div>
  );
}

function LegacySection({ title, body }: { title: string; body: string }) {
  return (
    <section>
      <h2>{title}</h2>
      <div className="prose prose-sm max-w-none text-inherit leading-snug prose-p:my-1 prose-ul:my-1 prose-li:my-0">
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
          {body}
        </ReactMarkdown>
      </div>
    </section>
  );
}

function StructuredLinksLine({ header }: { header: CVSections["header"] }) {
  if (!header) return null;
  const links: string[] = [];
  if (header.linkedin_url) links.push(header.linkedin_url);
  if (header.portfolio_url) links.push(header.portfolio_url);
  if (header.github_url) links.push(header.github_url);
  if (links.length === 0) return null;
  return <div className="cv-contact">{links.join("  ·  ")}</div>;
}

/**
 * Order chosen to match what Zambian recruiters typically expect at the
 * top of a CV: summary → experience → education → certs → languages →
 * projects → achievements → memberships → publications → volunteer →
 * references. Section is omitted when its array is empty.
 *
 * References: when sections.references is empty the template still emits
 * a "References available on request" line per Zambian convention. This
 * is a render-only decision; the stored data still says zero references.
 */
function StructuredSections({ sections }: { sections: CVSections }) {
  return (
    <>
      {sections.professional_summary?.text && (
        <section>
          <h2>SUMMARY</h2>
          <p>{sections.professional_summary.text}</p>
        </section>
      )}

      {sections.work_experience.length > 0 && (
        <section>
          <h2>EXPERIENCE</h2>
          {sections.work_experience.map((w, i) => (
            <div key={i} style={{ marginBottom: "0.6em" }}>
              <p style={{ marginBottom: 0 }}>
                <strong>{w.title}</strong>
                {w.company && <span>, {w.company}</span>}
                {w.location && <span> ({w.location})</span>}
                {(w.start_date || w.end_date !== undefined) && (
                  <span>
                    {"  ["}
                    {[w.start_date, w.end_date ?? "Present"].filter(Boolean).join(" – ")}
                    {"]"}
                  </span>
                )}
              </p>
              {w.achievements.length > 0 && (
                <ul>
                  {w.achievements.map((a, j) => (
                    <li key={j}>{a}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </section>
      )}

      {sections.education.length > 0 && (
        <section>
          <h2>EDUCATION</h2>
          {sections.education.map((e, i) => (
            <p key={i}>
              <strong>{e.degree}</strong>
              {e.institution && <span>, {e.institution}</span>}
              {e.location && <span> ({e.location})</span>}
              {(e.start_date || e.end_date) && (
                <span>
                  {"  ["}
                  {[e.start_date, e.end_date].filter(Boolean).join(" – ")}
                  {"]"}
                </span>
              )}
              {e.gpa && <span>  ·  GPA: {e.gpa}</span>}
              {e.thesis && <span>  ·  Thesis: {e.thesis}</span>}
            </p>
          ))}
        </section>
      )}

      {sections.certifications.length > 0 && (
        <section>
          <h2>CERTIFICATIONS</h2>
          <ul>
            {sections.certifications.map((c, i) => (
              <li key={i}>
                {c.name}
                {c.issuer && <> · {c.issuer}</>}
                {c.year && <> · {c.year}</>}
                {c.expiry && <> · expires {c.expiry}</>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {sections.languages.length > 0 && (
        <section>
          <h2>LANGUAGES</h2>
          <p>{sections.languages.map((l) => `${l.name} (${l.proficiency})`).join(", ")}</p>
        </section>
      )}

      {sections.projects.length > 0 && (
        <section>
          <h2>PROJECTS</h2>
          {sections.projects.map((p, i) => (
            <div key={i} style={{ marginBottom: "0.4em" }}>
              <p style={{ marginBottom: 0 }}>
                <strong>{p.name}</strong>
                {p.role && <span> — {p.role}</span>}
              </p>
              {p.outcome && <p style={{ marginTop: 0 }}>{p.outcome}</p>}
              {p.technologies.length > 0 && (
                <p style={{ marginTop: 0 }}>
                  <em>Stack: {p.technologies.join(", ")}</em>
                </p>
              )}
            </div>
          ))}
        </section>
      )}

      {sections.achievements.length > 0 && (
        <section>
          <h2>ACHIEVEMENTS</h2>
          <ul>
            {sections.achievements.map((a, i) => (
              <li key={i}>
                {a.title}
                {a.year && <> ({a.year})</>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {sections.memberships.length > 0 && (
        <section>
          <h2>MEMBERSHIPS</h2>
          <ul>
            {sections.memberships.map((m, i) => (
              <li key={i}>
                {m.organisation} · {m.role}
                {(m.year_started || m.year_ended) && (
                  <> ({m.year_started || ""} – {m.year_ended || "present"})</>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      {sections.publications.length > 0 && (
        <section>
          <h2>PUBLICATIONS</h2>
          <ul>
            {sections.publications.map((p, i) => (
              <li key={i}>
                {p.title}
                {p.venue && <> — {p.venue}</>}
                {p.year && <> ({p.year})</>}
              </li>
            ))}
          </ul>
        </section>
      )}

      {sections.volunteer_work.length > 0 && (
        <section>
          <h2>VOLUNTEER WORK</h2>
          {sections.volunteer_work.map((v, i) => (
            <div key={i} style={{ marginBottom: "0.4em" }}>
              <p style={{ marginBottom: 0 }}>
                <strong>{v.role || "Volunteer"}</strong>
                {v.organisation && <span>, {v.organisation}</span>}
                {(v.start_date || v.end_date) && (
                  <span>
                    {"  ["}
                    {[v.start_date, v.end_date ?? "Present"].filter(Boolean).join(" – ")}
                    {"]"}
                  </span>
                )}
              </p>
              {v.description && <p style={{ marginTop: 0 }}>{v.description}</p>}
            </div>
          ))}
        </section>
      )}

      <section>
        <h2>REFERENCES</h2>
        {sections.references.length === 0 ? (
          <p>Available on request.</p>
        ) : (
          sections.references.map((r, i) => (
            <p key={i} style={{ marginBottom: "0.3em" }}>
              <strong>{r.name}</strong>
              {r.title && <span>, {r.title}</span>}
              {r.organisation && <span> — {r.organisation}</span>}
              {(r.phone || r.email) && (
                <span> ({[r.phone, r.email].filter(Boolean).join(" · ")})</span>
              )}
            </p>
          ))
        )}
      </section>
    </>
  );
}
