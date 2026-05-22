"use client";

import type { TailoredCvDraft } from "./types";

export function AtsLivePreview({ draft }: { draft: TailoredCvDraft }) {
  const { basics, experience, education, skills } = draft;
  const contactBits = [basics.phone, basics.email, basics.location].filter(Boolean);

  return (
    <article className="tailored-cv-paper" aria-label="CV preview">
      <h1>{basics.fullName.trim() || "Your Name"}</h1>
      {basics.headline.trim() ? <p className="cv-headline">{basics.headline}</p> : null}
      {contactBits.length > 0 && (
        <div className="cv-contact">{contactBits.join("  ·  ")}</div>
      )}

      {basics.summary.trim() ? (
        <section>
          <h2>Summary</h2>
          <p>{basics.summary}</p>
        </section>
      ) : null}

      {experience.length > 0 && (
        <section>
          <h2>Experience</h2>
          {experience.map((role, i) => (
            <div key={`${role.company}-${i}`} style={{ marginBottom: "0.5em" }}>
              <p className="cv-entry-title">
                <strong>{role.title || "Role title"}</strong>
                {role.company ? <span>, {role.company}</span> : null}
                {role.location ? <span> ({role.location})</span> : null}
                {(role.startDate || role.endDate) && (
                  <span>
                    {"  ["}
                    {[role.startDate, role.endDate].filter(Boolean).join(" – ")}
                    {"]"}
                  </span>
                )}
              </p>
              {role.achievements.length > 0 && (
                <ul>
                  {role.achievements.map((item, j) => (
                    <li key={j}>{item}</li>
                  ))}
                </ul>
              )}
            </div>
          ))}
        </section>
      )}

      {education.length > 0 && (
        <section>
          <h2>Education</h2>
          {education.map((edu, i) => (
            <p key={`${edu.institution}-${i}`} className="cv-entry-title">
              <strong>{edu.degree}</strong>
              {edu.institution ? <span>, {edu.institution}</span> : null}
              {edu.location ? <span> ({edu.location})</span> : null}
              {(edu.startDate || edu.endDate) && (
                <span>
                  {"  ["}
                  {[edu.startDate, edu.endDate].filter(Boolean).join(" – ")}
                  {"]"}
                </span>
              )}
            </p>
          ))}
        </section>
      )}

      {skills.length > 0 && (
        <section>
          <h2>Skills</h2>
          <p className="cv-skills">{skills.join(" · ")}</p>
        </section>
      )}
    </article>
  );
}
