/** Visual drag handle for bottom sheets (native app affordance). */
export function SheetHandle() {
  return (
    <div
      className="mx-auto mb-2 mt-1 h-1 w-10 shrink-0 rounded-full"
      style={{ background: "var(--line-2)" }}
      aria-hidden
    />
  );
}
