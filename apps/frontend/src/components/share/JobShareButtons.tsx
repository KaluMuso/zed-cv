"use client";

import { useCallback, useState } from "react";
import { Icon } from "@/components/ui/Icon";
import {
  buildFacebookShareUrl,
  buildJobShareText,
  buildLinkedInShareUrl,
  buildTwitterShareUrl,
  buildWhatsAppShareUrl,
  jobPermalink,
  trackJobShare,
  type JobShareInput,
} from "@/lib/job-share";
import { notify } from "@/lib/toast";

interface JobShareButtonsProps {
  job: JobShareInput;
  className?: string;
  /** Match cards: Share + WhatsApp only (copy/X live in native Share). */
  variant?: "full" | "compact";
}

type ShareChannel =
  | "native"
  | "whatsapp"
  | "linkedin"
  | "facebook"
  | "twitter"
  | "copy";

export function JobShareButtons({
  job,
  className = "",
  variant = "full",
}: JobShareButtonsProps) {
  const [copying, setCopying] = useState(false);
  const url = jobPermalink(job.id);
  const text = buildJobShareText(job);
  const canNativeShare =
    typeof navigator !== "undefined" && typeof navigator.share === "function";

  const copyLink = useCallback(async () => {
    setCopying(true);
    try {
      await navigator.clipboard.writeText(url);
      notify.custom.success("Link copied");
      trackJobShare("copy");
    } catch {
      notify.error("Could not copy — try selecting the URL manually");
    } finally {
      setCopying(false);
    }
  }, [url]);

  const share = useCallback(
    async (channel: ShareChannel) => {
      trackJobShare(channel);
      switch (channel) {
        case "native":
          try {
            await navigator.share({ title: job.title, text, url });
          } catch (err) {
            if (err instanceof DOMException && err.name === "AbortError") return;
            await copyLink();
          }
          break;
        case "whatsapp":
          window.open(buildWhatsAppShareUrl(text), "_blank", "noopener,noreferrer");
          break;
        case "linkedin":
          window.open(buildLinkedInShareUrl(url), "_blank", "noopener,noreferrer");
          break;
        case "facebook":
          window.open(buildFacebookShareUrl(url), "_blank", "noopener,noreferrer");
          break;
        case "twitter":
          window.open(buildTwitterShareUrl(text, url), "_blank", "noopener,noreferrer");
          break;
        case "copy":
          await copyLink();
          break;
      }
    },
    [copyLink, job.title, text, url],
  );

  const plausibleAttrs = (channel: string) => ({
    "data-plausible-event-name": `job_share_${channel}`,
  });

  return (
    <div
      className={`share-buttons ${className}`.trim()}
      role="group"
      aria-label="Share this job"
    >
      {canNativeShare && (
        <button
          type="button"
          className="share-btn"
          onClick={() => void share("native")}
          {...plausibleAttrs("native")}
        >
          <Icon name="share" size={16} aria-hidden />
          Share
        </button>
      )}
      <a
        href={buildWhatsAppShareUrl(text)}
        target="_blank"
        rel="noopener noreferrer"
        className="share-btn"
        aria-label="Share on WhatsApp"
        onClick={() => trackJobShare("whatsapp")}
        {...plausibleAttrs("whatsapp")}
      >
        <Icon name="whatsapp" size={16} aria-hidden />
        WhatsApp
      </a>
      {variant === "full" ? (
        <>
          <a
            href={buildLinkedInShareUrl(url)}
            target="_blank"
            rel="noopener noreferrer"
            className="share-btn"
            aria-label="Share on LinkedIn"
            onClick={() => trackJobShare("linkedin")}
            {...plausibleAttrs("linkedin")}
          >
            <Icon name="linkedin" size={16} aria-hidden />
            LinkedIn
          </a>
          <a
            href={buildFacebookShareUrl(url)}
            target="_blank"
            rel="noopener noreferrer"
            className="share-btn"
            aria-label="Share on Facebook"
            onClick={() => trackJobShare("facebook")}
            {...plausibleAttrs("facebook")}
          >
            <Icon name="facebook" size={16} aria-hidden />
            Facebook
          </a>
          <a
            href={buildTwitterShareUrl(text, url)}
            target="_blank"
            rel="noopener noreferrer"
            className="share-btn"
            aria-label="Share on X"
            onClick={() => trackJobShare("twitter")}
            {...plausibleAttrs("twitter")}
          >
            <Icon name="x" size={16} aria-hidden />
            X
          </a>
          <button
            type="button"
            className="share-btn"
            onClick={() => void share("copy")}
            disabled={copying}
            aria-label="Copy job link"
            {...plausibleAttrs("copy")}
          >
            <Icon name="link" size={16} aria-hidden />
            {copying ? "Copied…" : "Copy link"}
          </button>
        </>
      ) : null}
    </div>
  );
}
