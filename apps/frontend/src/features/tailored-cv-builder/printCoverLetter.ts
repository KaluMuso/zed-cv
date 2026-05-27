/** Trigger browser Save-as-PDF for the cover letter print stylesheet. */
export function printCoverLetter(filenameSlug: string): void {
  const previousTitle = document.title;
  const slug =
    filenameSlug
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "cover-letter";
  document.title = slug;
  window.print();
  window.setTimeout(() => {
    document.title = previousTitle;
  }, 100);
}
