"use client";

const MAIN_ID = "main-content";

/** Skip link target id — use on the primary `<main>` landmark. */
export const MAIN_CONTENT_ID = MAIN_ID;

/**
 * Visually hidden until focused; jumps keyboard users past chrome
 * (navbar, tab bar) to the page main landmark.
 */
export function SkipToContent() {
  return (
    <a href={`#${MAIN_ID}`} className="skip-to-content">
      Skip to main content
    </a>
  );
}
