"use client";

import type { CVSections } from "@/lib/api";
import type { ParsedCV, ParsedSection } from "../parseCv";
import { splitBullets } from "../parseCv";

/**
 * Two-column layout: copper sidebar holds identity + scannable sections
 * (skills, education, certifications), main column carries the narrative
 * (summary, experience). Less ATS-friendly than the plain template — meant
 * for human reviewers, recruiter portfolios, and printed copies.
 *
 * Two render paths share the same DOM/CSS:
 *   - cvSections present (task #59): render structured shape with the
 *     sidebar/main split picked by section type (sidebar: scannable;
 *     main: narrative).
 *   - cvSections null: fall back to the legacy free-text ParsedCV path,
 *     routing sections by heading name. Used for legacy generations and
 *     post-edit state.
 */

const SIDEBAR_SECTIONS = new Set([
  "SKILLS",
  "TECHNICAL SKILLS",
  "CORE SKILLS",
  "EDUCATION",
  "CERTIFICATIONS",
  "CERTIFICATES",
  "LANGUAGES",
  "REFERENCES",
]);

export function DesignerTemplate({
  parsed,
  cvSections,
}: {
  parsed: ParsedCV;
  cvSections?: CVSections | null;
}) {
  const { header } = parsed;

  if (cvSections) {
    return (
      <div className="cv-print-root cv-designer">
        <aside className="cv-sidebar">
          <h1>{header.name || "Your Name"}</h1>
          <div className="cv-contact">
            {header.phone && <div>{header.phone}</div>}
            {header.email && <div style={{ wordBreak: "break-all" }}>{header.email}</div>}
            {header.location && <div>{header.location}</div>}
            {cvSections.header?.linkedin_url && (
              <div style={{ wordBreak: "break-all" }}>{cvSections.header.linkedin_url}</div>
            )}
            {cvSections.header?.portfolio_url && (
              <div style={{ wordBreak: "break-all" }}>{cvSections.header.portfolio_url}</div>
            )}
            {cvSections.header?.github_url && (
              <div style={{ wordBreak: "break-all" }}>{cvSections.header.github_url}</div>
            )}
          </div>
          <SidebarSections sections={cvSections} />
        </aside>
        <main className="cv-main">
          <MainSections sections={cvSections} />
        </main>
      </div>
    );
  }

  const sidebar = parsed.sections.filter((s) => SIDEBAR_SECTIONS.has(s.title));
  const main = parsed.sections.filter((s) => !SIDEBAR_SECTIONS.has(s.title));

  return (
    <div className="cv-print-root cv-designer">
      <aside className="cv-sidebar">
        <h1>{header.name || "Your Name"}</h1>
        <div className="cv-contact">
          {header.phone && <div>{header.phone}</div>}
          {header.email && <div style={{ wordBreak: "break-all" }}>{header.email}</div>}
          {header.location && <div>{header.location}</div>}
        </div>
        {sidebar.map((s) => (
          <LegacySection key={s.title} section={s} variant="sidebar" />
        ))}
      </aside>
      <main className="cv-main">
        {main.map((s) => (
          <LegacySection key={s.title} section={s} variant="main" />
        ))}
      </main>
    </div>
  );
}

function LegacySection({ section, variant }: { section: ParsedSection; variant: "sidebar" | "main" }) {
  const { bullets, paragraphs } = splitBullets(section.body);
  // SKILLS in the sidebar reads better as comma-separated tags than as a
  // bullet list — and SKILLS bodies often arrive as a single comma line
  // anyway. Detect this and flatten.
  const isSkillsTags =
    variant === "sidebar" &&
    section.title.includes("SKILLS") &&
    paragraphs.length === 1 &&
    bullets.length === 0 &&
    paragraphs[0].includes(",");

  return (
    <section>
      <h2>{section.title}</h2>
      {isSkillsTags ? (
        <p>{paragraphs[0]}</p>
      ) : (
        <>
          {paragraphs.map((p, i) => (
            <p key={`p-${i}`}>{p}</p>
          ))}
          {bullets.length > 0 && (
            <ul>
              {bullets.map((b, i) => (
                <li key={`b-${i}`}>{b}</li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}

/**
 * Sidebar holds the scannable structured sections: Education, Certifications,
 * Languages, Memberships, References. Skips Skills because the structured
 * shape doesn't include a top-level skills list (those are profile-level
 * and not reproduced in CVSections to keep the data model small).
 *
 * References fallback line: "Available on request" rendered when the
 * references array is empty, per Zambian convention.
 */
function SidebarSections({ sections }: { sections: CVSections }) {
  return (
    <>
      {sections.education.length > 0 && (
        <section>
          <h2>EDUCATION</h2>
          {sections.education.map((e, i) => (
            <p key={i} style={{ marginBottom: "0.4em" }}>
              <strong>{e.degree}</strong>
              {e.institution && <span><br />{e.institution}</span>}
              {(e.start_date || e.end_date) && (
                <span>
                  <br />
                  {[e.start_date, e.end_date].filter(Boolean).join(" – ")}
                </span>
              )}
              {e.gpa && <span><br />GPA: {e.gpa}</span>}
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

      <section>
        <h2>REFERENCES</h2>
        {sections.references.length === 0 ? (
          <p>Available on request.</p>
        ) : (
          sections.references.map((r, i) => (
            <p key={i} style={{ marginBottom: "0.4em" }}>
              <strong>{r.name}</strong>
              {r.title && <><br />{r.title}</>}
              {r.organisation && <><br />{r.organisation}</>}
              {(r.phone || r.email) && (
                <><br />{[r.phone, r.email].filter(Boolean).join(" · ")}</>
              )}
            </p>
          ))
        )}
      </section>
    </>
  );
}

function MainSections({ sections }: { sections: CVSections }) {
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
    </>
  );
}
