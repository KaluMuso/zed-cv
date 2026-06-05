/** Main bottom-tab routes in left-to-right order (for slide direction). */
export const MOBILE_TAB_ORDER = [
  "/jobs",
  "/matches",
  "/applications",
  "/profile",
] as const;

export type RouteTransitionVariant = "fade" | "tab-left" | "tab-right";

function tabIndex(pathname: string): number {
  const idx = MOBILE_TAB_ORDER.findIndex((route) => pathname.startsWith(route));
  return idx;
}

/** Slide direction when switching between primary tabs; fade elsewhere. */
export function getRouteTransitionVariant(
  fromPath: string,
  toPath: string,
): RouteTransitionVariant {
  const from = tabIndex(fromPath);
  const to = tabIndex(toPath);
  if (from < 0 || to < 0 || from === to) return "fade";
  return to > from ? "tab-right" : "tab-left";
}
