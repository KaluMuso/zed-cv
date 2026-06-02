// Paste entire file into n8n "Normalize and Deduplicate" Code node.
// Keeps per-job aggregator URLs (e.g. gozambiajobs.com/jobs/123-slug); drops homepages only.

const AGGREGATOR_HOSTS = new Set([
  'jobwebzambia.com',
  'gozambiajobs.com',
  'jobsearchzambia.com',
  'jobsearchzm.com',
]);

const AGG_INDEX_SEGMENTS = new Set([
  'jobs',
  'job',
  'vacancies',
  'careers',
  'index.php',
  'index.html',
]);

function decodeUrl(raw) {
  return String(raw || '')
    .trim()
    .replace(/&amp;/gi, '&')
    .replace(/&#38;/gi, '&');
}

function sanitizeListingSourceUrl(raw) {
  if (raw == null || raw === '') return null;
  const cleaned = decodeUrl(raw);
  if (!/^https?:\/\//i.test(cleaned)) return null;
  let u;
  try {
    u = new URL(cleaned);
  } catch {
    return null;
  }
  const host = (u.hostname || '').toLowerCase().replace(/^www\./, '');
  const isAgg =
    AGGREGATOR_HOSTS.has(host) ||
    [...AGGREGATOR_HOSTS].some((d) => host === d || host.endsWith('.' + d));
  if (!isAgg) return cleaned.substring(0, 2000);
  const segs = (u.pathname || '').replace(/^\/+|\/+$/g, '').split('/').filter(Boolean);
  if (segs.length === 0) return null;
  if (segs.length === 1 && AGG_INDEX_SEGMENTS.has(segs[0].toLowerCase())) return null;
  return cleaned.substring(0, 2000);
}

function normPostedAt(raw) {
  if (!raw) return null;
  const s = String(raw).trim();
  if (/^\d{4}-\d{2}-\d{2}/.test(s)) return s.substring(0, 10);
  const parsed = Date.parse(s);
  if (!Number.isNaN(parsed)) return new Date(parsed).toISOString().substring(0, 10);
  // "9h ago", "Posted 19 hours ago", "Posted 4 minutes ago"
  const rel = s.match(
    /(?:posted\s+)?(\d+)\s*(minute|min|hour|hr|h|day|d|week|w|month|m)s?\s+ago/i
  );
  if (rel) {
    const n = parseInt(rel[1], 10);
    const unit = rel[2].toLowerCase();
    const d = new Date();
    if (unit.startsWith('min')) d.setMinutes(d.getMinutes() - n);
    else if (unit.startsWith('h') || unit === 'hr') d.setHours(d.getHours() - n);
    else if (unit.startsWith('d')) d.setDate(d.getDate() - n);
    else if (unit.startsWith('w')) d.setDate(d.getDate() - n * 7);
    else if (unit.startsWith('m')) d.setMonth(d.getMonth() - n);
    return d.toISOString().substring(0, 10);
  }
  return null;
}

function slugify(t) {
  return String(t || '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
}

function matchLinkForJob(job, links) {
  if (!links || !links.length) return null;
  const titleSlug = slugify(job.title);
  const words = titleSlug.split('-').filter((w) => w.length > 3);
  let best = null;
  let bestScore = 0;
  for (const url of links) {
    const path = url.toLowerCase();
    let score = 0;
    if (titleSlug.length > 8 && path.includes(titleSlug.slice(0, 48))) score += 12;
    for (const w of words) {
      if (path.includes(w)) score += 2;
    }
    if (score > bestScore) {
      bestScore = score;
      best = url;
    }
  }
  return bestScore >= 3 ? best : null;
}

function parseJobsPayload(item) {
  const j = item.json || {};
  if (j.error) return null;
  if (j.jobs && Array.isArray(j.jobs)) return j;

  let text = null;
  if (j.choices?.[0]?.message?.content) {
    text = j.choices[0].message.content;
  } else if (j.data?.choices?.[0]?.message?.content) {
    text = j.data.choices[0].message.content;
  } else if (j.candidates?.[0]?.content?.parts?.[0]?.text) {
    text = j.candidates[0].content.parts[0].text;
  } else if (j.text) {
    text = typeof j.text === 'string' ? j.text : JSON.stringify(j.text);
  }

  if (text) {
    const trimmed = text.trim();
    try {
      const direct = JSON.parse(trimmed);
      if (direct && Array.isArray(direct.jobs)) return direct;
    } catch {
      /* fall through */
    }
    const m = trimmed.match(/\{[\s\S]*"jobs"[\s\S]*\}/);
    if (m) return JSON.parse(m[0]);
  }

  const blob = JSON.stringify(j);
  const m = blob.match(/\{[\s\S]*"jobs"[\s\S]*\}/);
  if (m) return JSON.parse(m[0]);
  return null;
}

function resolveSourceUrl(job, linkPool) {
  const candidates = [job.source_url, job.apply_url].filter(Boolean);
  for (const raw of candidates) {
    const kept = sanitizeListingSourceUrl(raw);
    if (kept) return kept;
  }
  const guessed = matchLinkForJob(job, linkPool);
  return guessed ? sanitizeListingSourceUrl(guessed) : null;
}

const prepNames = [
  'Prep GoZambia Body',
  'Prep JobWebZambia Body',
  'Prep LinkedIn Body',
  'Prep JobSearchZM Body',
];

function linksForBranch(index) {
  try {
    const prep = $(prepNames[index]).first();
    const links = prep?.json?.extractedLinks;
    return Array.isArray(links) ? links : [];
  } catch {
    return [];
  }
}

const allJobs = [];
const seen = new Set();
const inputs = $input.all();

for (let branch = 0; branch < inputs.length; branch++) {
  const item = inputs[branch];
  const linkPool = linksForBranch(branch);
  let data;
  try {
    data = parseJobsPayload(item);
  } catch {
    continue;
  }
  if (!data?.jobs) continue;

  for (const j of data.jobs) {
    if (!j.title) continue;

    const sourceUrl = resolveSourceUrl(j, linkPool);
    const hasContact = !!(j.apply_url || j.apply_email || sourceUrl);
    const descRaw = (j.description || '')
      .replace(/<[^>]+>/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();

    if (descRaw.length < 10 && !hasContact) continue;

    const description =
      descRaw.length >= 10
        ? descRaw.substring(0, 5000)
        : [
            (j.title || '').trim(),
            j.company ? 'at ' + j.company : '',
            j.location ? 'in ' + j.location : '',
            sourceUrl ? 'Details: ' + sourceUrl : '',
          ]
            .filter(Boolean)
            .join(' ')
            .substring(0, 5000);

    const k = (j.title + '|' + (j.company || '')).toLowerCase().trim();
    if (seen.has(k)) continue;
    seen.add(k);

    allJobs.push({
      title: (j.title || '').trim().substring(0, 200),
      company: (j.company || '').trim().substring(0, 200) || null,
      location: (j.location || '').trim() || null,
      description,
      requirements: Array.isArray(j.requirements) ? j.requirements : [],
      skills_required: Array.isArray(j.skills_required) ? j.skills_required : [],
      salary_min: j.salary_min || null,
      salary_max: j.salary_max || null,
      apply_url: j.apply_url || null,
      apply_email: j.apply_email || null,
      source: 'scraper',
      source_url: sourceUrl,
      closing_date: j.closing_date || null,
      posted_at: normPostedAt(j.posted_at),
    });
  }
}

return [{ json: { jobs: allJobs, count: allJobs.length } }];
