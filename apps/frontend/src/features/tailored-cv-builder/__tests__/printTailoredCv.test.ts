import { describe, expect, it, beforeEach, afterEach } from "vitest";
import { PDF_SKILLS_SEPARATOR } from "../skillsDisplay";
import {
  CV_PRINT_ACTIVE_BODY_CLASS,
  flattenDetailsForPrint,
  mountTailoredCvPrintHost,
  slugifyPrintFilename,
  TAILORED_CV_PRINT_HOST_CLASS,
  unmountTailoredCvPrintHost,
} from "../printTailoredCv";

describe("printTailoredCv helpers", () => {
  beforeEach(() => {
    document.body.innerHTML = "";
    document.body.className = "";
  });

  afterEach(() => {
    document.body.innerHTML = "";
    document.body.className = "";
  });

  it("slugifyPrintFilename normalizes titles", () => {
    expect(slugifyPrintFilename("CV Jane Doe")).toBe("cv-jane-doe");
    expect(slugifyPrintFilename("!!!")).toBe("tailored-cv");
  });

  it("flattenDetailsForPrint replaces details with sections", () => {
    const root = document.createElement("article");
    root.innerHTML = `
      <details class="cv-preview-section">
        <summary class="cv-preview-section-title">Summary</summary>
        <div class="cv-preview-section-body"><p>Experienced analyst.</p></div>
      </details>
    `;
    flattenDetailsForPrint(root);

    expect(root.querySelector("details")).toBeNull();
    const section = root.querySelector("section.cv-preview-section--print");
    expect(section).not.toBeNull();
    expect(section?.querySelector("h2")?.textContent).toBe("Summary");
    expect(section?.querySelector("p")?.textContent).toBe("Experienced analyst.");
  });

  it("mountTailoredCvPrintHost clones root and flattens details for print", () => {
    document.body.innerHTML = `
      <article class="tailored-cv-print-root">
        <header class="cv-print-header"><h1>Jane</h1></header>
        <details class="cv-preview-section">
          <summary class="cv-preview-section-title">Skills</summary>
          <div class="cv-preview-section-body"><p>Excel</p></div>
        </details>
      </article>
    `;
    const root = document.querySelector<HTMLElement>(".tailored-cv-print-root")!;
    const host = mountTailoredCvPrintHost(root);

    expect(host.className).toBe(TAILORED_CV_PRINT_HOST_CLASS);
    expect(document.body.classList.contains(CV_PRINT_ACTIVE_BODY_CLASS)).toBe(true);
    expect(host.querySelector("details")).toBeNull();
    expect(host.querySelector("section.cv-preview-section--print h2")?.textContent).toBe(
      "Skills",
    );
    expect(host.querySelector(".cv-print-header h1")?.textContent).toBe("Jane");

    unmountTailoredCvPrintHost(host);
    expect(document.querySelector(`.${TAILORED_CV_PRINT_HOST_CLASS}`)).toBeNull();
    expect(document.body.classList.contains(CV_PRINT_ACTIVE_BODY_CLASS)).toBe(false);
  });

  it("print clone keeps uncapped dot-separated skills line for PDF export", () => {
    const skills = Array.from({ length: 20 }, (_, i) => `Skill ${i + 1}`);
    const fullLine = skills.join(PDF_SKILLS_SEPARATOR);

    document.body.innerHTML = `
      <article class="tailored-cv-print-root">
        <details class="cv-preview-section" open>
          <summary class="cv-preview-section-title">Skills</summary>
          <div class="cv-preview-section-body">
            <div class="cv-skills-block">
              <p class="cv-skills-line">${fullLine}</p>
              <div class="cv-skills-tags">
                ${skills
                  .slice(0, 18)
                  .map((s) => `<span class="cv-skill-tag">${s}</span>`)
                  .join("")}
                <span class="cv-skill-tag cv-skill-tag--more">+2 more</span>
              </div>
            </div>
          </div>
        </details>
      </article>
    `;

    const root = document.querySelector<HTMLElement>(".tailored-cv-print-root")!;
    const host = mountTailoredCvPrintHost(root);

    const printLine = host.querySelector(".cv-skills-line");
    expect(printLine?.textContent).toBe(fullLine);
    expect(printLine?.textContent).toContain("Skill 19");
    expect(printLine?.textContent).toContain("Skill 20");
    expect(printLine?.textContent).not.toContain("and 2 more");

    const skillsHeading = host.querySelector("section.cv-preview-section--print h2");
    expect(skillsHeading?.textContent).toBe("Skills");

    unmountTailoredCvPrintHost(host);
  });
});
