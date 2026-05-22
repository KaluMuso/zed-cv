/** Shared display helpers for job detail surfaces (page + drawer). */

export const EMPLOYMENT_TYPE_LABEL: Record<string, string> = {
  full_time: "Full time",
  part_time: "Part time",
  contract: "Contract",
  freelance: "Freelance",
  internship: "Internship",
  temporary: "Temporary",
};

export const WORK_ARRANGEMENT_LABEL: Record<string, string> = {
  remote: "Remote",
  hybrid: "Hybrid",
  on_site: "On-site",
};

export const PAY_FREQUENCY_LABEL: Record<string, string> = {
  monthly: "/mo",
  annual: "/yr",
  hourly: "/hr",
  daily: "/day",
};

export function formatSalary(min?: number | null, max?: number | null): string | null {
  if (!min && !max) return null;
  const fmt = (ngwee: number) => {
    const kwacha = ngwee / 100;
    if (kwacha >= 1000)
      return `K${(kwacha / 1000).toFixed(kwacha % 1000 === 0 ? 0 : 1)}k`;
    return `K${kwacha.toFixed(0)}`;
  };
  if (min && max && min !== max) return `${fmt(min)}–${fmt(max)}`;
  return fmt(min ?? max ?? 0);
}

export function matchStrengthCopy(score: number): string {
  if (score >= 85) return "Strong match. Based on your CV.";
  if (score >= 70) return "Good match. Based on your CV.";
  if (score >= 50) return "Moderate match. Based on your CV.";
  return "Stretch match. Based on your CV.";
}
