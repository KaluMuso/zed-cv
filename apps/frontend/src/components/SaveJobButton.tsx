"use client";

import { useCallback, useEffect, useState } from "react";
import { savedJobs, ApiError } from "@/lib/api";
import { Icon } from "@/components/ui/Icon";
import { notify } from "@/lib/toast";
import { cn } from "@/lib/utils";

export interface SaveJobButtonProps {
  jobId: string;
  saved: boolean;
  token: string | null;
  disabled?: boolean;
  /** Optional extra classes for the outer button */
  className?: string;
  /** Show text label beside the bookmark icon */
  showLabel?: boolean;
  /** Override visible label when unsaved (default: "Save job") */
  saveLabel?: string;
  /** Override visible label when saved (default: "Saved") */
  savedLabel?: string;
  onChange?: (jobId: string, nextSaved: boolean) => void;
}

export function SaveJobButton({
  jobId,
  saved,
  token,
  disabled,
  className,
  showLabel = false,
  saveLabel = "Save job",
  savedLabel = "Saved",
  onChange,
}: SaveJobButtonProps) {
  const [busy, setBusy] = useState(false);
  const [innerSaved, setInnerSaved] = useState(saved);

  useEffect(() => {
    setInnerSaved(saved);
  }, [saved]);

  const toggle = useCallback(async () => {
    if (!token) {
      notify.error("Sign in to save jobs.");
      return;
    }
    if (disabled || busy) return;
    setBusy(true);
    const wasSaved = innerSaved;
    try {
      if (wasSaved) {
        await savedJobs.unsave(token, jobId);
        setInnerSaved(false);
        onChange?.(jobId, false);
        notify.unsaved("Job unsaved");
      } else {
        await savedJobs.save(token, jobId);
        setInnerSaved(true);
        onChange?.(jobId, true);
        notify.saved("Job saved successfully");
      }
    } catch (e: unknown) {
      setInnerSaved(wasSaved);
      if (e instanceof ApiError) {
        notify.error(e.detail || "Could not update saved jobs.");
      } else {
        notify.error("Could not update saved jobs.");
      }
    } finally {
      setBusy(false);
    }
  }, [token, disabled, busy, innerSaved, jobId, onChange]);

  const label = innerSaved ? "Saved job" : "Save job";

  return (
    <button
      type="button"
      className={cn(
        innerSaved ? "btn btn-primary" : "btn btn-outline",
        showLabel ? "btn-sm gap-1.5" : "btn-sm",
        className,
      )}
      aria-label={label}
      title={innerSaved ? "Remove from saved" : "Save this job"}
      disabled={Boolean(disabled) || busy}
      onClick={toggle}
      style={{ opacity: busy ? 0.65 : 1 }}
    >
      <Icon name="bookmark" size={16} />
      {showLabel ? <span>{innerSaved ? savedLabel : saveLabel}</span> : null}
    </button>
  );
}
