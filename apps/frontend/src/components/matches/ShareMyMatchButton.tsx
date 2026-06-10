"use client";

import { useCallback, useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { notify } from "@/lib/toast";

// Strip any trailing slash AND any trailing /api/v1 so we can safely
// concatenate "/api/v1/..." paths below. On Vercel,
// NEXT_PUBLIC_API_URL is set to "https://api.zedapply.com/api/v1"
// (with the prefix included), which double-prefixed every request
// from this component until 2026-06-10 and 404'd the viral loop.
const API_BASE = (
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ??
  "https://api.zedapply.com"
).replace(/\/api\/v1$/, "");

interface ShareMatchResponse {
  token: string;
  share_url: string;
  is_new: boolean;
}

type ShareMyMatchButtonProps = {
  matchId: string;
  authToken: string;
  /** Optional context for the WhatsApp message body. */
  matchScore?: number;
  jobTitle?: string | null;
  /** Extra classes on the button. */
  className?: string;
};

function buildShareMessage(
  url: string,
  matchScore: number | undefined,
  jobTitle: string | null | undefined,
): string {
  const intro =
    typeof matchScore === "number" && jobTitle
      ? `I'm a ${matchScore}% match for ${jobTitle} on ZedApply.`
      : jobTitle
        ? `Check out this job match I found on ZedApply: ${jobTitle}.`
        : `Check out this job match I found on ZedApply.`;
  return `${intro}\n\nGet your own AI-powered job matches free — ${url}`;
}

function openWhatsAppShare(text: string): void {
  const url = `https://wa.me/?text=${encodeURIComponent(text)}`;
  window.open(url, "_blank", "noopener,noreferrer");
}

export function ShareMyMatchButton({
  matchId,
  authToken,
  matchScore,
  jobTitle,
  className = "",
}: ShareMyMatchButtonProps) {
  const [busy, setBusy] = useState(false);
  // Cache the URL across clicks so the second share doesn't re-hit the API.
  const [cachedUrl, setCachedUrl] = useState<string | null>(null);

  const onClick = useCallback(
    async () => {
      if (busy) return;

      // Already have a token from a previous click in this session?
      if (cachedUrl) {
        const text = buildShareMessage(cachedUrl, matchScore, jobTitle);
        if (
          typeof navigator !== "undefined" &&
          typeof navigator.share === "function"
        ) {
          try {
            await navigator.share({
              title: "My ZedApply match",
              text,
              url: cachedUrl,
            });
            return;
          } catch (err) {
            if (err instanceof DOMException && err.name === "AbortError")
              return;
            // Fall through to WhatsApp
          }
        }
        openWhatsAppShare(text);
        return;
      }

      setBusy(true);
      try {
        const res = await fetch(
          `${API_BASE}/api/v1/matches/${encodeURIComponent(matchId)}/share`,
          {
            method: "POST",
            headers: {
              Authorization: `Bearer ${authToken}`,
              "Content-Type": "application/json",
            },
            body: "{}",
          },
        );
        if (!res.ok) {
          let detail = "Could not create share link.";
          try {
            const body = (await res.json()) as { detail?: string };
            if (body?.detail) detail = body.detail;
          } catch {
            /* ignore */
          }
          notify.error(detail);
          return;
        }
        const data = (await res.json()) as ShareMatchResponse;
        setCachedUrl(data.share_url);

        const text = buildShareMessage(data.share_url, matchScore, jobTitle);

        // Prefer the native share sheet on mobile (Android/iOS) so the user
        // can pick WhatsApp, Telegram, SMS, etc. Fall back to a WhatsApp
        // deep link on desktop or when the API isn't available.
        if (
          typeof navigator !== "undefined" &&
          typeof navigator.share === "function"
        ) {
          try {
            await navigator.share({
              title: "My ZedApply match",
              text,
              url: data.share_url,
            });
            return;
          } catch (err) {
            if (err instanceof DOMException && err.name === "AbortError")
              return;
            // Fall through to WhatsApp
          }
        }
        openWhatsAppShare(text);
      } catch (err) {
        notify.error(
          err instanceof Error
            ? err.message
            : "Could not create share link. Please try again.",
        );
      } finally {
        setBusy(false);
      }
    },
    [busy, cachedUrl, matchId, authToken, matchScore, jobTitle],
  );

  return (
    <button
      type="button"
      className={`share-btn ${className}`.trim()}
      onClick={() => void onClick()}
      disabled={busy}
      aria-label="Share my match on WhatsApp"
      data-plausible-event-name="match_share_my_match"
    >
      <Icon name="whatsapp" size={16} aria-hidden />
      {busy ? "Sharing…" : "Share my match"}
    </button>
  );
}
