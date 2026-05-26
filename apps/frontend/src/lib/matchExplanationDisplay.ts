const PREFERENCES_PREFIX = "Preferences match:";

/** Split stored explanation into narrative text and preferences bonus line. */
export function splitMatchExplanation(explanation: string | null | undefined): {
  main: string | null;
  preferencesNote: string | null;
} {
  if (!explanation?.trim()) {
    return { main: null, preferencesNote: null };
  }

  const idx = explanation.indexOf(PREFERENCES_PREFIX);
  if (idx === -1) {
    return { main: explanation.trim(), preferencesNote: null };
  }

  const main = explanation.slice(0, idx).trim().replace(/\s+$/, "") || null;
  const preferencesNote = explanation.slice(idx).trim() || null;
  return { main, preferencesNote };
}
