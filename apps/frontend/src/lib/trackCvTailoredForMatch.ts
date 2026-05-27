/** Plausible custom event when a user generates a match-tailored CV. */
export function trackCvTailoredForMatch(matchId: string): void {
  if (typeof window === "undefined") return;
  const plausible = (
    window as Window & {
      plausible?: (name: string, options?: { props?: Record<string, string> }) => void;
    }
  ).plausible;
  plausible?.("cv_tailored_for_match", { props: { match_id: matchId } });
}
