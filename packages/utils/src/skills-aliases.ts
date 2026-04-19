/**
 * Skills normalization map — shared between frontend and backend.
 * Maps common aliases/abbreviations to canonical skill names.
 *
 * Backend equivalent lives in the skill_aliases DB table,
 * but this is used for client-side display and validation.
 */

export const SKILL_ALIASES: Record<string, string> = {
  // Programming languages
  js: "javascript",
  ts: "typescript",
  "c#": "csharp",
  "c sharp": "csharp",
  py: "python",
  rb: "ruby",

  // Frameworks
  node: "nodejs",
  "node.js": "nodejs",
  "next.js": "nextjs",
  "react.js": "react",
  "vue.js": "vue",
  "express.js": "expressjs",

  // Office tools
  "ms word": "microsoft office",
  word: "microsoft office",
  "ms excel": "excel",
  "ms powerpoint": "powerpoint",
  ppt: "powerpoint",
  "google docs": "google workspace",
  "google sheets": "google workspace",

  // Domain
  hr: "human resources",
  pm: "project management",
  "data entry": "data analysis",
  bookkeeping: "accounting",
};

/**
 * Normalize a skill name to its canonical form.
 */
export function normalizeSkill(raw: string): string {
  const lower = raw.trim().toLowerCase();
  return SKILL_ALIASES[lower] ?? lower;
}

/**
 * Normalize an array of skills, removing duplicates.
 */
export function normalizeSkills(skills: string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];

  for (const skill of skills) {
    const normalized = normalizeSkill(skill);
    if (!seen.has(normalized)) {
      seen.add(normalized);
      result.push(normalized);
    }
  }

  return result;
}

/**
 * Skill categories for UI grouping.
 */
export const SKILL_CATEGORIES = {
  programming: "Programming & Development",
  tools: "Software & Tools",
  soft_skill: "Soft Skills",
  domain: "Industry & Domain",
} as const;

export type SkillCategory = keyof typeof SKILL_CATEGORIES;
