const HTML_TAG_NAMES = (
  "h1|h2|h3|h4|h5|h6|p|div|span|a|br|li|ul|ol|" +
  "strong|em|b|i|u|s|strike|sup|sub|table|thead|tbody|tr|td|th|" +
  "blockquote|pre|code|hr|figure|figcaption|img|small"
).split("|");

const _HTML_TAG_RE = new RegExp(
  `</?\\s*(${HTML_TAG_NAMES.join("|")})(\\s[^>]*)?>`,
  "gi",
);
const _BR_RE = /<\s*br\s*\/?\s*>/gi;
const _LI_OPEN_RE = /<\s*li\b[^>]*>/gi;
const _BLOCK_CLOSE_RE = /<\/\s*(p|div|h[1-6]|ul|ol|tr|table)\s*>/gi;

/** Lines that expose scraper provenance — never show on candidate-facing detail. */
const SCRAPER_LINE_PATTERNS: RegExp[] = [
  /^\s*first\s+posted\b/i,
  /^\s*scraped\s+from\b/i,
  /^\s*source\s*:\s*/i,
  /^\s*posted\s+via\b/i,
  /^\s*view\s+(the\s+)?original\s+(posting|job)\b/i,
  /^\s*see\s+original\s+(posting|job)\b/i,
  /linkedin\.com/i,
  /bestjobs\.co/i,
  /gozambiajobs/i,
  /jobartis/i,
  /myjobmag/i,
  /reliefweb\.int/i,
];

function isScraperMetadataLine(line: string): boolean {
  const trimmed = line.trim();
  if (!trimmed) return false;
  return SCRAPER_LINE_PATTERNS.some((re) => re.test(trimmed));
}

/** Remove scraper/source footer lines from plain-text job descriptions. */
export function stripScraperMetadata(text: string): string {
  if (!text) return "";
  return text
    .split("\n")
    .filter((line) => !isScraperMetadataLine(line))
    .join("\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

/** Client-side defensive HTML strip for legacy job descriptions. */
export function stripDescriptionHtml(text: string | null | undefined): string {
  if (!text) return "";
  let out = text;
  if (out.includes("<")) {
    out = out
      .replace(_BR_RE, "\n")
      .replace(_LI_OPEN_RE, "\n• ")
      .replace(_BLOCK_CLOSE_RE, "\n")
      .replace(_HTML_TAG_RE, "")
      .replace(/&nbsp;/gi, " ")
      .replace(/&amp;/gi, "&")
      .replace(/&lt;/gi, "<")
      .replace(/&gt;/gi, ">")
      .replace(/&quot;/gi, '"')
      .replace(/&#39;/gi, "'")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }
  return stripScraperMetadata(out);
}
