"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { coverLetter, ApiError } from "@/lib/api";
import { canUseCoverLetterEditor } from "@/lib/tier-gating";
import { Icon } from "@/components/ui/Icon";
import { ModalPortal } from "@/components/shared/ModalPortal";
import { notify } from "@/lib/toast";

const CoverLetterEditor = dynamic(
  () =>
    import("@/features/tailored-cv-builder/CoverLetterEditor").then((mod) => ({
      default: mod.CoverLetterEditor,
    })),
  {
    ssr: false,
    loading: () => (
      <p className="text-sm py-6 text-center text-muted-foreground">Loading editor…</p>
    ),
  }
);

export function CoverLetterMatchModal({
  open,
  onClose,
  token,
  matchId,
  jobTitle,
  company,
  subscriptionTier,
}: {
  open: boolean;
  onClose: () => void;
  token: string;
  matchId: string;
  jobTitle: string;
  company: string | null;
  subscriptionTier: string | null | undefined;
}) {
  const [letter, setLetter] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const editorEnabled = canUseCoverLetterEditor(subscriptionTier);

  useEffect(() => {
    if (!open) {
      setLetter(null);
      return;
    }
    if (!editorEnabled) return;
    setLoading(true);
    coverLetter
      .listVersions(token, matchId)
      .then((res) => {
        if (res.latest?.content_md) {
          setLetter(res.latest.content_md);
        }
      })
      .catch(() => {
        /* no versions yet */
      })
      .finally(() => setLoading(false));
  }, [open, token, matchId, editorEnabled]);

  const generate = useCallback(async () => {
    setLoading(true);
    setLetter(null);
    try {
      const res = await coverLetter.generateForMatch(token, matchId);
      setLetter(res.content);
      notify.custom.success("Cover letter ready");
    } catch (e: unknown) {
      if (e instanceof ApiError && e.status === 403) {
        notify.error("Cover letters require the Professional plan.");
      } else if (e instanceof ApiError) {
        notify.error(e.detail || "Could not generate cover letter.");
      } else {
        notify.error("Could not generate cover letter.");
      }
    } finally {
      setLoading(false);
    }
  }, [token, matchId]);

  if (!open) return null;

  return (
    <ModalPortal>
      <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4">
        <div className="modal-backdrop" onClick={onClose} aria-hidden />
        <div
          role="dialog"
          aria-labelledby="cover-letter-match-title"
          className="relative z-10 w-full max-w-3xl max-h-[min(92vh,900px)] overflow-y-auto rounded-xl border bg-background shadow-xl p-5 sm:p-6"
          style={{ borderColor: "var(--line)" }}
        >
          <div className="flex items-start justify-between gap-3 mb-4">
            <div>
              <h2 id="cover-letter-match-title" className="text-lg font-semibold">
                Cover letter
              </h2>
              <p className="text-sm text-muted-foreground">
                {jobTitle}
                {company ? ` at ${company}` : ""}
              </p>
            </div>
            <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
              Close
            </button>
          </div>

          {!editorEnabled && (
            <p className="text-sm rounded-lg border px-4 py-3 mb-4 text-muted-foreground">
              AI drafts require Professional or Super Standard.{" "}
              <Link href="/pricing" className="underline">
                View plans
              </Link>
            </p>
          )}

          {!letter && !loading && (
            <button
              type="button"
              className="btn btn-primary w-full sm:w-auto mb-4"
              onClick={() => void generate()}
              disabled={!editorEnabled && !token}
            >
              <Icon name="sparkle" size={14} /> Generate cover letter
            </button>
          )}

          {loading && (
            <p className="text-sm py-8 text-center text-muted-foreground">Writing your cover letter…</p>
          )}

          {(letter || editorEnabled) && (
            <CoverLetterEditor
              matchId={matchId}
              jobTitle={jobTitle}
              company={company ?? ""}
              token={token}
              editorEnabled={editorEnabled}
              initialContent={letter ?? ""}
              onContentChange={setLetter}
            />
          )}

          {letter && editorEnabled ? (
            <button
              type="button"
              className="btn btn-ghost btn-sm mt-3"
              onClick={() => void generate()}
            >
              Regenerate
            </button>
          ) : null}
        </div>
      </div>
    </ModalPortal>
  );
}
