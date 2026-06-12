"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";
import { coverLetter, ApiError, type CoverLetterVersionDetail } from "@/lib/api";
import { Icon } from "@/components/ui/Icon";
import { notify } from "@/lib/toast";
import {
  COVER_LETTER_WORD_SOFT_LIMIT,
  countWords,
} from "./countWords";
import { printCoverLetter } from "./printCoverLetter";
import { MarkdownTextarea } from "@/components/ui/MarkdownTextarea";
import "./coverLetterPrint.css";

export type CoverLetterEditorProps = {
  matchId: string;
  jobTitle: string;
  company: string;
  token: string | null;
  editorEnabled: boolean;
  initialContent?: string;
  onContentChange?: (content: string) => void;
};

export function CoverLetterEditor({
  matchId,
  jobTitle,
  company,
  token,
  editorEnabled,
  initialContent = "",
  onContentChange,
}: CoverLetterEditorProps) {
  const [draft, setDraft] = useState(initialContent);
  const [versions, setVersions] = useState<CoverLetterVersionDetail[]>([]);
  const [selectedVersionId, setSelectedVersionId] = useState<string | null>(null);
  const [currentVersionId, setCurrentVersionId] = useState<string | null>(null);
  const [loadingVersions, setLoadingVersions] = useState(false);
  const [saving, setSaving] = useState(false);

  const wordCount = useMemo(() => countWords(draft), [draft]);
  const overLimit = wordCount > COVER_LETTER_WORD_SOFT_LIMIT;

  const loadVersions = useCallback(async () => {
    if (!token || !editorEnabled) return;
    setLoadingVersions(true);
    try {
      const res = await coverLetter.listVersions(token, matchId);
      setVersions(res.versions);
      if (res.latest) {
        setDraft(res.latest.content_md);
        setSelectedVersionId(res.latest.id);
        setCurrentVersionId(res.latest.id);
        onContentChange?.(res.latest.content_md);
      }
    } catch (e: unknown) {
      if (e instanceof ApiError && e.status === 403) {
        return;
      }
      notify.error("Could not load saved versions.");
    } finally {
      setLoadingVersions(false);
    }
  }, [token, matchId, editorEnabled, onContentChange]);

  useEffect(() => {
    if (initialContent && !currentVersionId) {
      setDraft(initialContent);
    }
  }, [initialContent, currentVersionId]);

  useEffect(() => {
    void loadVersions();
  }, [loadVersions]);

  const handleDraftChange = (value: string) => {
    setDraft(value);
    onContentChange?.(value);
  };

  const handleVersionSelect = (versionId: string) => {
    const row = versions.find((v) => v.id === versionId);
    if (!row) return;
    setSelectedVersionId(versionId);
    setCurrentVersionId(versionId);
    handleDraftChange(row.content_md);
  };

  const save = async () => {
    if (!token || !editorEnabled) return;
    if (!draft.trim()) {
      notify.error("Write something before saving.");
      return;
    }
    if (overLimit) {
      notify.error(`Keep the letter under ${COVER_LETTER_WORD_SOFT_LIMIT} words before saving.`);
      return;
    }
    setSaving(true);
    try {
      const saved = await coverLetter.save(token, matchId, {
        content_md: draft,
        parent_version_id: currentVersionId,
        source: "user_edit",
      });
      notify.custom.success(`Saved as v${saved.version_number}`);
      setCurrentVersionId(saved.id);
      setSelectedVersionId(saved.id);
      await loadVersions();
    } catch (e: unknown) {
      if (e instanceof ApiError) {
        notify.error(e.detail || "Could not save.");
      } else {
        notify.error("Could not save.");
      }
    } finally {
      setSaving(false);
    }
  };

  const downloadPdf = () => {
    const slug = `${jobTitle}-${company}`.trim() || "cover-letter";
    printCoverLetter(slug);
  };

  const editorBody = (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 min-h-[280px]">
      <div className="flex flex-col gap-2 min-h-0">
        <label className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--muted)" }}>
          Edit letter
        </label>
        <MarkdownTextarea
          value={draft}
          onChangeValue={(val) => handleDraftChange(val)}
          disabled={!editorEnabled}
          rows={14}
          className="flex-1 w-full text-sm font-sans min-h-[240px]"
          style={{
            borderColor: "var(--line)",
            color: "var(--ink-2)",
            opacity: editorEnabled ? 1 : 0.55,
          }}
          placeholder="Your cover letter will appear here after generation…"
          spellCheck
        />
        <p
          className="text-xs"
          style={{ color: overLimit ? "var(--copper-600)" : "var(--muted)" }}
        >
          {wordCount} / {COVER_LETTER_WORD_SOFT_LIMIT} words
          {overLimit ? " — shorten before saving" : ""}
          <span className="ml-2">{draft.length} characters</span>
        </p>
      </div>
      <div className="flex flex-col gap-2 min-h-0">
        <label className="text-xs font-medium uppercase tracking-wide" style={{ color: "var(--muted)" }}>
          Preview
        </label>
        <div
          className="cover-letter-print-root flex-1 overflow-y-auto rounded-lg border p-4 text-sm prose prose-sm max-w-none"
          style={{ borderColor: "var(--line)", color: "var(--ink-2)" }}
        >
          {draft.trim() ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
              {draft}
            </ReactMarkdown>
          ) : (
            <p style={{ color: "var(--muted)" }}>Preview updates as you type.</p>
          )}
        </div>
      </div>
    </div>
  );

  return (
    <div className="space-y-4">
      {!editorEnabled ? (
        <div
          className="rounded-lg border px-4 py-3 text-sm"
          style={{ borderColor: "var(--line)", background: "var(--paper-2)", color: "var(--muted)" }}
          title="Upgrade to Professional or Super Standard to edit and save versions."
        >
          <p>
            Inline editing, version history, and PDF export are on{" "}
            <Link href="/pricing" className="underline" style={{ color: "var(--green-700)" }}>
              Professional
            </Link>{" "}
            and Super Standard plans.
          </p>
        </div>
      ) : null}

      <div
        className={editorEnabled ? undefined : "pointer-events-none select-none opacity-60"}
        aria-disabled={!editorEnabled}
      >
        {editorEnabled && versions.length > 0 ? (
          <div className="flex flex-wrap items-center gap-2">
            <label htmlFor="cover-letter-version" className="text-xs" style={{ color: "var(--muted)" }}>
              Version
            </label>
            <select
              id="cover-letter-version"
              className="rounded-md border px-2 py-1.5 text-sm max-w-full"
              style={{ borderColor: "var(--line)" }}
              value={selectedVersionId ?? ""}
              disabled={loadingVersions}
              onChange={(e) => void handleVersionSelect(e.target.value)}
            >
              {versions.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.label}
                </option>
              ))}
            </select>
            {loadingVersions ? (
              <span className="text-xs" style={{ color: "var(--muted)" }}>
                Loading…
              </span>
            ) : null}
          </div>
        ) : null}

        {editorBody}

        <div className="flex flex-wrap gap-2 pt-2">
          <button
            type="button"
            className="btn btn-primary btn-sm"
            disabled={!editorEnabled || saving || overLimit || !draft.trim()}
            onClick={() => void save()}
          >
            {saving ? "Saving…" : "Save version"}
          </button>
          <button
            type="button"
            className="btn btn-outline btn-sm"
            disabled={!draft.trim()}
            onClick={downloadPdf}
          >
            <Icon name="download" size={14} /> Download PDF
          </button>
        </div>
      </div>
    </div>
  );
}
