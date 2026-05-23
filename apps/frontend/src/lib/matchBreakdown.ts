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
};

export function matchBreakdownRows(match: {
  vector_score?: number;
  semantic_score?: number;
  skill_score?: number;
  skills_score?: number;
  experience_score?: number | null;
  location_score?: number | null;
  recency_score?: number | null;
  bonus_score?: number;
}): MatchBreakdownRow[] {
  const semantic = match.semantic_score ?? match.vector_score ?? 0;
  const skills = match.skills_score ?? match.skill_score ?? 0;
  const experience = match.experience_score ?? 0;
  let location = match.location_score ?? 0;
  let recency = match.recency_score ?? 0;
  if (location === 0 && recency === 0 && (match.bonus_score ?? 0) > 0) {
    location = match.bonus_score ?? 0;
  }
  return [
    { key: "semantic", label: "Semantic", value: semantic, max: MATCH_SCORE_CAPS.semantic, tone: "green" },
    { key: "skills", label: "Skills overlap", value: skills, max: MATCH_SCORE_CAPS.skills, tone: "copper" },
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
  return `${Math.round(value)}/${max}`;
}
