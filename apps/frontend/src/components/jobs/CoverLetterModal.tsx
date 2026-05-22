"use client";

import { useCallback, useState } from "react";
import Link from "next/link";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { coverLetter, ApiError } from "@/lib/api";
import { Icon } from "@/components/ui/Icon";
import { notifyError, notifySuccess } from "@/components/Toast";

export function CoverLetterModal({
  jobId,
  jobTitle,
  company,
  token,
  open,
  onOpenChange,
}: {
  jobId: string;
  jobTitle: string;
  company: string | null;
  token: string | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [letter, setLetter] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const generate = useCallback(async () => {
    if (!token) {
      notifyError("Sign in to generate a cover letter.");
      return;
    }
    setLoading(true);
    setLetter(null);
    try {
      const res = await coverLetter.generate(token, jobId);
      setLetter(res.letter);
      notifySuccess("Cover letter ready");
    } catch (e: unknown) {
      if (e instanceof ApiError && e.status === 403) {
        notifyError("Cover letters require the Professional plan.");
      } else if (e instanceof ApiError) {
        notifyError(e.detail || "Could not generate cover letter.");
      } else {
        notifyError("Could not generate cover letter.");
      }
    } finally {
      setLoading(false);
    }
  }, [token, jobId]);

  const copy = useCallback(async () => {
    if (!letter) return;
    try {
      await navigator.clipboard.writeText(letter);
      notifySuccess("Copied to clipboard");
    } catch {
      notifyError("Could not copy — select the text manually");
    }
  }, [letter]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg" showCloseButton>
        <DialogHeader>
          <DialogTitle>Cover letter</DialogTitle>
          <DialogDescription>
            {jobTitle}
            {company ? ` at ${company}` : ""}
          </DialogDescription>
        </DialogHeader>

        {!letter && !loading && (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              AI drafts a tailored letter from your CV and this job description.
              Professional plan required.
            </p>
            <button
              type="button"
              className="btn btn-primary w-full"
              onClick={() => void generate()}
              disabled={!token}
            >
              <Icon name="sparkle" size={14} /> Generate cover letter
            </button>
            {!token && (
              <p className="text-xs text-center">
                <Link href="/auth" className="underline" style={{ color: "var(--copper-500)" }}>
                  Sign in
                </Link>{" "}
                to continue
              </p>
            )}
            <p className="text-xs text-center text-muted-foreground">
              <Link href="/pricing">View plans</Link>
            </p>
          </div>
        )}

        {loading && (
          <p className="text-sm text-muted-foreground py-8 text-center">
            Writing your cover letter…
          </p>
        )}

        {letter && (
          <div className="space-y-3">
            <div
              className="max-h-64 overflow-y-auto rounded-lg border p-4 text-sm leading-relaxed whitespace-pre-wrap"
              style={{ borderColor: "var(--line)", color: "var(--ink-2)" }}
            >
              {letter}
            </div>
            <div className="flex gap-2">
              <button type="button" className="btn btn-outline btn-sm flex-1" onClick={() => void copy()}>
                Copy
              </button>
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => {
                  setLetter(null);
                  void generate();
                }}
              >
                Regenerate
              </button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
