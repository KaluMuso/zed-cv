/** Trigger browser Save-as-PDF for the tailored CV print stylesheet. */
export function printTailoredCv(filenameSlug: string): void {
  const previousTitle = document.title;
  const slug =
    filenameSlug
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "tailored-cv";
  document.title = slug;
  window.print();
  window.setTimeout(() => {
    document.title = previousTitle;
  }, 100);
}
