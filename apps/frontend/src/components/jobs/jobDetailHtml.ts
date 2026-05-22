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

/** Client-side defensive HTML strip for legacy job descriptions. */
export function stripDescriptionHtml(text: string | null | undefined): string {
  if (!text) return "";
  if (!text.includes("<")) return text;
  return text
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
