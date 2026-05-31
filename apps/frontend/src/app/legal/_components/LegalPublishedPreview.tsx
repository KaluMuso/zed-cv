"use client";

/**
 * Renders bleach-sanitized HTML from legal_docs.content_html (server-side).
 * Do not pass unsanitized user input — admin editor uses this only for DB rows.
 */
export function LegalPublishedPreview({ html }: { html: string }) {
  if (!html.trim()) {
    return (
      <p className="text-sm text-muted-foreground">
        No published HTML yet. Save the document to generate sanitized HTML from markdown.
      </p>
    );
  }

  return (
    <div
      className="legal-body legal-published-preview"
      // content_html is rendered + bleached in apps/backend/app/api/v1/legal.py
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
