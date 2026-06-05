/** Light tap feedback on supported mobile browsers (ignored elsewhere). */
export function hapticTap(durationMs = 8): void {
  if (typeof navigator === "undefined" || !navigator.vibrate) return;
  try {
    navigator.vibrate(durationMs);
  } catch {
    /* Safari / permission edge cases */
  }
}
