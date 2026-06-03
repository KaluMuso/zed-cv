/**
 * Browser print / Save-as-PDF for the tailored CV builder (live preview + Review).
 *
 * Export paths (Phase 0 — print layout only; no .docx here):
 * - Tailored CV builder + profile generator preview: `printTailoredCv()` or
 *   `window.print()` + `print.css` (this module / generator print.css).
 * - Scratch / manual CV wizard: server WeasyPrint via `POST /cv/build-from-scratch`
 *   (`apps/backend/app/services/cv_pdf_renderer.py`) — not browser print.
 */

export const TAILORED_CV_PRINT_ROOT_SELECTOR = ".tailored-cv-print-root";
export const TAILORED_CV_PRINT_HOST_CLASS = "tailored-cv-print-host";
export const CV_PRINT_ACTIVE_BODY_CLASS = "cv-print-active";

export function slugifyPrintFilename(filenameSlug: string): string {
  return (
    filenameSlug
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "tailored-cv"
  );
}

/**
 * Replace accordion `<details>` with flat `<section>` nodes so print engines
 * (especially Chromium/Edge) do not insert extra gap before section bodies.
 */
export function flattenDetailsForPrint(root: HTMLElement): void {
  root.querySelectorAll<HTMLDetailsElement>("details.cv-preview-section").forEach((details) => {
    const summary = details.querySelector("summary.cv-preview-section-title");
    const body = details.querySelector(".cv-preview-section-body");
    const section = document.createElement("section");
    section.className = "cv-preview-section cv-preview-section--print";

    if (summary) {
      const heading = document.createElement("h2");
      heading.className = summary.className;
      heading.textContent = summary.textContent?.trim() ?? "";
      section.appendChild(heading);
    }

    if (body) {
      while (body.firstChild) {
        section.appendChild(body.firstChild);
      }
    }

    details.replaceWith(section);
  });
}

/** Clone the live preview into a print-only host so hidden UI does not reserve blank pages. */
export function mountTailoredCvPrintHost(root: HTMLElement): HTMLElement {
  const host = document.createElement("div");
  host.className = TAILORED_CV_PRINT_HOST_CLASS;
  const clone = root.cloneNode(true) as HTMLElement;
  clone.querySelectorAll("details").forEach((details) => {
    details.open = true;
  });
  flattenDetailsForPrint(clone);
  host.appendChild(clone);
  document.body.appendChild(host);
  document.body.classList.add(CV_PRINT_ACTIVE_BODY_CLASS);
  return host;
}

export function unmountTailoredCvPrintHost(host: HTMLElement | null): void {
  host?.remove();
  document.body.classList.remove(CV_PRINT_ACTIVE_BODY_CLASS);
}

export function printTailoredCv(filenameSlug: string): void {
  const root = document.querySelector<HTMLElement>(TAILORED_CV_PRINT_ROOT_SELECTOR);
  const previousTitle = document.title;
  const slug = slugifyPrintFilename(filenameSlug);
  document.title = slug;

  const host = root ? mountTailoredCvPrintHost(root) : null;

  let cleaned = false;
  const cleanup = () => {
    if (cleaned) return;
    cleaned = true;
    unmountTailoredCvPrintHost(host);
    document.title = previousTitle;
  };

  window.addEventListener("afterprint", cleanup, { once: true });

  // Let the print host paint before opening the dialog (Chromium/Edge).
  const openPrintDialog = () => window.print();
  if (typeof window.requestAnimationFrame === "function") {
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(openPrintDialog);
    });
  } else {
    openPrintDialog();
  }

  // Fallback when afterprint is missing (older WebKit).
  window.setTimeout(cleanup, 30_000);
}
