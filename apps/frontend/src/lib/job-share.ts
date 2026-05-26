import { SITE_URL } from "@/lib/site-metadata";

export type JobShareInput = {
  id: string;
  title: string;
  company?: string | null;
  location?: string | null;
};

export function jobPermalink(jobId: string): string {
  return `${SITE_URL}/jobs/${jobId}`;
}

/** Plain-text blurb for WhatsApp / native share sheets. */
export function buildJobShareText(job: JobShareInput): string {
  const where = [job.company, job.location].filter(Boolean).join(" · ");
  const headline = where ? `${job.title} — ${where}` : job.title;
  return `${headline}\n\nView on ZedApply: ${jobPermalink(job.id)}`;
}

export function buildLinkedInShareUrl(url: string): string {
  return `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(url)}`;
}

export function buildFacebookShareUrl(url: string): string {
  return `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(url)}`;
}

export function buildWhatsAppShareUrl(text: string): string {
  return `https://wa.me/?text=${encodeURIComponent(text)}`;
}

export function buildTwitterShareUrl(text: string, url: string): string {
  return `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(url)}`;
}

/** Fire a Plausible custom event when the script is loaded (optional). */
export function trackJobShare(channel: string): void {
  if (typeof window === "undefined") return;
  const plausible = (
    window as Window & {
      plausible?: (name: string, options?: { props?: Record<string, string> }) => void;
    }
  ).plausible;
  plausible?.("job_share", { props: { channel } });
}
