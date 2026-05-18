/**
 * Split a plain-text job description into typed chunks so the UI can
 * render section headings ("Job Purpose", "Key Responsibilities", …)
 * distinctly from body paragraphs without pulling in a markdown parser.
 *
 * The detector is intentionally structural rather than whitelist-based:
 * a line is treated as a heading if it is short, capitalised in title
 * or upper case, and ends without sentence punctuation. That covers the
 * known headings in our scraper feed plus future variants nobody has
 * thought to whitelist, while keeping false positives low (a normal
 * sentence ends in a period, blowing the heading test).
 */

export type DescriptionChunk =
  | { type: "heading"; text: string }
  | { type: "paragraph"; text: string };

const STOP_WORDS = new Set([
  "a",
  "an",
  "and",
  "as",
  "at",
  "by",
  "for",
  "in",
  "of",
  "on",
  "or",
  "the",
  "to",
  "vs",
  "with",
]);

export function isHeadingLine(rawLine: string): boolean {
  // Allow an optional trailing colon ("Job Purpose:"); strip before
  // testing punctuation/case rules.
  const trimmed = rawLine.trim().replace(/:$/, "").trim();
  if (!trimmed) return false;
  if (trimmed.length > 80) return false;
  if (/[.!?,;]$/.test(trimmed)) return false;
  const words = trimmed.split(/\s+/);
  if (words.length === 0 || words.length > 8) return false;

  // ALL CAPS (with at least one A–Z) is a strong heading signal — many
  // employers shout their section headers, especially in OCR'd flyers.
  const hasLetter = /[A-Za-z]/.test(trimmed);
  if (!hasLetter) return false;
  const allCaps = trimmed === trimmed.toUpperCase();
  if (allCaps) return true;

  // Title case: every significant word starts with an uppercase letter.
  // Short stop-words ("of", "and", "the") may be lowercase mid-phrase,
  // mirroring how humans actually title things.
  return words.every((word, i) => {
    if (i > 0 && STOP_WORDS.has(word.toLowerCase())) return true;
    return /^[A-Z0-9]/.test(word);
  });
}

export function splitDescriptionChunks(text: string): DescriptionChunk[] {
  if (!text) return [];
  const lines = text.split(/\r?\n/);
  const chunks: DescriptionChunk[] = [];
  let buffer: string[] = [];

  const flushBuffer = () => {
    if (buffer.length === 0) return;
    const joined = buffer.join("\n").trim();
    if (joined) chunks.push({ type: "paragraph", text: joined });
    buffer = [];
  };

  for (const rawLine of lines) {
    const line = rawLine.replace(/\s+$/, "");
    if (line.trim() === "") {
      // Blank line closes the running paragraph.
      flushBuffer();
      continue;
    }
    if (isHeadingLine(line)) {
      flushBuffer();
      chunks.push({
        type: "heading",
        text: line.trim().replace(/:$/, "").trim(),
      });
      continue;
    }
    buffer.push(line);
  }
  flushBuffer();
  return chunks;
}
