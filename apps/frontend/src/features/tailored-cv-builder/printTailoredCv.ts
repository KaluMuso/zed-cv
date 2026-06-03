/** Trigger browser Save-as-PDF for the tailored CV print stylesheet. */

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

/** Clone the live preview into a print-only host so hidden UI does not reserve blank pages. */
export function mountTailoredCvPrintHost(root: HTMLElement): HTMLElement {
  const host = document.createElement("div");
  host.className = TAILORED_CV_PRINT_HOST_CLASS;
  const clone = root.cloneNode(true) as HTMLElement;
  clone.querySelectorAll("details").forEach((details) => {
    details.open = true;
  });
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
  window.print();
  // Fallback when afterprint is missing (older WebKit).
  window.setTimeout(cleanup, 30_000);
}
