/**
 * Client-side description normalization when description_markdown is absent.
 * Mirrors backend description_markdown.py heuristics.
 */

const CAPS_HEADING = /^[A-Z][A-Z0-9\s/&-]{7,}:?\s*$/;
const BULLET = /^[\s]*[•·\-*]\s+/;

export function plainTextToMarkdown(description: string): string {
  if (!description.trim()) return "";
  const lines = description.replace(/\r\n/g, "\n").split("\n");
  const out: string[] = [];

  for (const raw of lines) {
    const line = raw.replace(/\s+$/, "");
    if (!line.trim()) {
      if (out.length && out[out.length - 1] !== "") out.push("");
      continue;
    }
    if (BULLET.test(line)) {
      out.push(`- ${line.replace(BULLET, "").trim()}`);
      continue;
    }
    if (CAPS_HEADING.test(line.trim()) || (line.trim().endsWith(":") && line === line.toUpperCase() && line.length < 80)) {
      out.push(`## ${line.trim().replace(/:$/, "")}`);
      continue;
    }
    out.push(line);
  }

  return out.join("\n").trim();
}
