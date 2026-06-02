/** v2 weighted match score component caps (sum to 100). */
export const MATCH_SCORE_CAPS = {
  semantic: 50,
  skills: 20,
  experience: 15,
  location: 10,
  recency: 5,
} as const;

export type MatchBreakdownRow = {
  key: string;
  label: string;
  value: number;
  max: number;
  tone: "green" | "copper";
  /** Extra context shown under the fraction (e.g. required-skill counts). */
  detail?: string;
};

export type RequiredSkillsCount = {
  matched: number;
  total: number;
};

/** Required job skills = matched names + missing names from the RPC. */
export function countRequiredJobSkills(match: {
  matched_skills?: string[];
  missing_skills?: string[];
}): RequiredSkillsCount {
  const matched = match.matched_skills?.length ?? 0;
  const missing = match.missing_skills?.length ?? 0;
  return { matched, total: matched + missing };
}

export function formatRequiredSkillsDetail(count: RequiredSkillsCount): string | null {
  if (count.total <= 0) return null;
  const noun = count.total === 1 ? "skill" : "skills";
  return `${count.matched}/${count.total} required ${noun}`;
}

export function matchBreakdownRows(match: {
  vector_score?: number;
  semantic_score?: number;
  skill_score?: number;
  skills_score?: number;
  experience_score?: number | null;
  location_score?: number | null;
  recency_score?: number | null;
  bonus_score?: number;
  matched_skills?: string[];
  missing_skills?: string[];
}): MatchBreakdownRow[] {
  const semantic = match.semantic_score ?? match.vector_score ?? 0;
  const skills = match.skills_score ?? match.skill_score ?? 0;
  const experience = match.experience_score ?? 0;
  let location = match.location_score ?? 0;
  let recency = match.recency_score ?? 0;
  if (location === 0 && recency === 0 && (match.bonus_score ?? 0) > 0) {
    location = match.bonus_score ?? 0;
  }
  const skillsDetail = formatRequiredSkillsDetail(countRequiredJobSkills(match));
  return [
    { key: "semantic", label: "Semantic", value: semantic, max: MATCH_SCORE_CAPS.semantic, tone: "green" },
    {
      key: "skills",
      label: "Required skills",
      value: skills,
      max: MATCH_SCORE_CAPS.skills,
      tone: "copper",
      detail: skillsDetail ?? undefined,
    },
    {
      key: "experience",
      label: "Experience fit",
      value: experience,
      max: MATCH_SCORE_CAPS.experience,
      tone: "green",
    },
    { key: "location", label: "Location fit", value: location, max: MATCH_SCORE_CAPS.location, tone: "green" },
    { key: "recency", label: "Recency", value: recency, max: MATCH_SCORE_CAPS.recency, tone: "copper" },
  ];
}

export function formatBreakdownFraction(value: number, max: number): string {
  return `${Math.round(value)}/${max} pts`;
}
