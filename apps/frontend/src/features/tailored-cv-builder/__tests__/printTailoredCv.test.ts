import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
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
});
