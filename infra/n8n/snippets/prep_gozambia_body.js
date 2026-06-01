const SITE_BASE = 'https://www.gozambiajobs.com';
const NL = String.fromCharCode(10);
const raw = ($json.data || '');
const absUrl = (href) => {
  if (!href || href.startsWith('javascript:') || href.startsWith('#') || href.startsWith('mailto:')) return null;
  try {
    if (href.startsWith('http://') || href.startsWith('https://')) return href.split('#')[0];
    if (href.startsWith('/')) return SITE_BASE.replace(/\/$/, '') + href.split('#')[0];
  } catch (e) {}
  return null;
};
const listingLinks = [];
const hrefRe = /href\s*=\s*["']([^"']+)["']/gi;
let hm;
while ((hm = hrefRe.exec(raw)) !== null && listingLinks.length < 200) {
  const u = absUrl(hm[1]);
  if (!u) continue;
  const low = u.toLowerCase();
  if ((low.includes('gozambiajobs') && /\/job\//.test(low)) || low.includes('/job') || low.includes('/vacanc') || low.includes('/career') || low.includes('/position') || low.includes('/opportunit')) {
    if (!listingLinks.includes(u)) listingLinks.push(u);
  }
}
const linksBlock = listingLinks.length
  ? NL + NL + 'EXTRACTED_LISTING_LINKS (use the best match as source_url per job):' + NL + listingLinks.join(NL)
  : '';
const text = raw
  .replace(/<script[\s\S]*?<\/script>/gi, '')
  .replace(/<style[\s\S]*?<\/style>/gi, '')
  .replace(/<!--[\s\S]*?-->/g, '')
  .replace(/<[^>]+>/g, ' ')
  .replace(/\s+/g, ' ')
  .trim()
  .substring(0, 80000);
const prompt = 'Extract ALL real Zambian job listings from the cleaned-text below (not ads, sidebars, navigation, or category labels). Be CONCISE: cap each description at 600 chars; no repeated whitespace or boilerplate. Return ONLY valid JSON: {"jobs":[{"title":"","company":"","location":"","description":"","requirements":[],"skills_required":[],"apply_url":null,"source_url":null,"closing_date":null,"posted_at":null}]}. posted_at must be ISO YYYY-MM-DD or null (never relative like 9h ago). For each job, set source_url from EXTRACTED_LISTING_LINKS when it matches that job (full per-job URL only; never the site homepage). Normalize locations to Zambian cities (leave null if unclear). Skip expired or non-Zambia roles. Return {"jobs":[]} ONLY if there are literally zero job postings.';
const fullPrompt = prompt + linksBlock + NL + NL + 'TEXT:' + NL + text;
return [{
  json: {
    geminiBody: {
      contents: [{ parts: [{ text: fullPrompt }] }],
      generationConfig: {
        temperature: 0.1,
        maxOutputTokens: 32768,
        responseMimeType: 'application/json',
        thinkingConfig: { thinkingBudget: 0 }
      }
    },
    extractedLinks: listingLinks,
    siteHost: SITE_BASE.replace(/^https?:\/\//, '').replace(/\/$/, ''),
  }
}];
