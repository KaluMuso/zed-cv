import { describe, expect, it, beforeEach, afterEach, vi } from "vitest";
import {
  CV_PRINT_ACTIVE_BODY_CLASS,
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

  it("mountTailoredCvPrintHost clones root and opens closed details", () => {
    document.body.innerHTML = `
      <article class="tailored-cv-print-root">
        <details><summary>Skills</summary><p>Excel</p></details>
      </article>
    `;
    const root = document.querySelector<HTMLElement>(".tailored-cv-print-root")!;
    const host = mountTailoredCvPrintHost(root);

    expect(host.className).toBe(TAILORED_CV_PRINT_HOST_CLASS);
    expect(document.body.classList.contains(CV_PRINT_ACTIVE_BODY_CLASS)).toBe(true);
    const cloneDetails = host.querySelector("details");
    expect(cloneDetails?.open).toBe(true);

    unmountTailoredCvPrintHost(host);
    expect(document.querySelector(`.${TAILORED_CV_PRINT_HOST_CLASS}`)).toBeNull();
    expect(document.body.classList.contains(CV_PRINT_ACTIVE_BODY_CLASS)).toBe(false);
  });
});
