"use client";

import { useEffect, useState } from "react";
import { adminLegal, type AdminLegalDoc, type LegalSlug, ApiError } from "@/lib/api";
import { notify } from "@/lib/toast";
import { LegalMarkdown } from "@/app/legal/_components/LegalMarkdown";
import { LegalPublishedPreview } from "@/app/legal/_components/LegalPublishedPreview";

const SLUGS: { slug: LegalSlug; label: string; description: string }[] = [
  {
    slug: "privacy",
    label: "Privacy Policy",
    description: "/legal/privacy — Zambia DPA 2021 compliant data notice",
  },
  {
    slug: "terms",
    label: "Terms of Service",
    description: "/legal/terms — eligibility, paid tiers, governing law",
  },
  {
    slug: "cookies",
    label: "Cookie Policy",
    description: "/legal/cookies — strictly-necessary + preferences + opt-in",
  },
  {
    slug: "refund",
    label: "Refund Policy",
    description: "/legal/refund — 7-day guarantee, Lenco/DPO billing disputes",
  },
];

export function LegalTab({ token }: { token: string }) {
  const [active, setActive] = useState<LegalSlug | null>(null);

  return (
    <div>
      <p className="text-sm text-muted-foreground mb-4">
        Edit the markdown for each public legal page. Save publishes the
        change immediately — the public page re-renders within a second
        via on-demand ISR revalidation.
      </p>

      {/* List of pages */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {SLUGS.map((s) => (
          <button
            key={s.slug}
            type="button"
            onClick={() => setActive(s.slug)}
            className="card card-hover p-5 text-left"
            style={{
              border:
                active === s.slug
                  ? "1px solid var(--copper-400)"
                  : "1px solid var(--line)",
              background: "var(--surface)",
            }}
          >
            <div className="font-display text-lg" style={{ letterSpacing: "-0.01em" }}>
              {s.label}
            </div>
            <p
              className="text-xs mt-1"
              style={{ color: "var(--muted)", lineHeight: 1.5 }}
            >
              {s.description}
            </p>
            <div
              className="mt-3 text-xs font-medium"
              style={{ color: "var(--green-700)" }}
            >
              {active === s.slug ? "Editing →" : "Open editor →"}
            </div>
          </button>
        ))}
      </div>

      {active && (
        <div className="mt-6">
          <LegalEditor key={active} token={token} slug={active} />
        </div>
      )}
    </div>
  );
}

type PreviewMode = "draft" | "published";

function LegalEditor({ token, slug }: { token: string; slug: LegalSlug }) {
  const [doc, setDoc] = useState<AdminLegalDoc | null>(null);
  const [version, setVersion] = useState("");
  const [contentMd, setContentMd] = useState("");
  const [previewMode, setPreviewMode] = useState<PreviewMode>("draft");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setLoading(true);
    adminLegal
      .get(token, slug)
      .then((d) => {
        setDoc(d);
        setVersion(d.version || "1.0");
        setContentMd(d.content_md || "");
      })
      .catch((e) =>
        notify.error(
          e instanceof Error ? e.message : `Could not load /legal/${slug}`,
        ),
      )
      .finally(() => setLoading(false));
  }, [token, slug]);

  const handleSave = async () => {
    if (!contentMd.trim()) {
      notify.error("Content can't be empty.");
      return;
    }
    setSaving(true);
    try {
      const saved = await adminLegal.update(token, slug, {
        version,
        content_md: contentMd,
      });
      setDoc(saved);

      // Fire the Next.js on-demand revalidation so the public page picks
      // up the change within ~1s, before the 300s ISR window would have.
      try {
        await fetch("/api/admin/revalidate-legal", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ slug }),
        });
      } catch {
        // If revalidation fails (network blip, route handler error),
        // the page still updates within the ISR window. Surface a
        // warning so the operator knows propagation is slower than
        // usual, but DON'T fail the save.
        notify.custom.warning(
          "Saved, but couldn't trigger immediate cache refresh. Page will update within 5 minutes.",
        );
        return;
      }

      notify.custom.success(`Saved /legal/${slug}. Public page refreshed.`);
    } catch (e) {
      if (e instanceof ApiError && e.status === 403) {
        notify.error("You don't have permission to edit legal pages.");
      } else {
        notify.error(e instanceof Error ? e.message : "Save failed.");
      }
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="card p-8">
        <div className="skeleton h-6 w-32 mb-4" />
        <div className="skeleton h-96 w-full" />
      </div>
    );
  }

  return (
    <div className="card p-5 sm:p-6">
      <div className="flex flex-wrap items-end justify-between gap-3 mb-4">
        <div>
          <div className="eyebrow">Editing</div>
          <h3
            className="font-display"
            style={{ fontSize: 22, letterSpacing: "-0.01em" }}
          >
            /legal/{slug}
          </h3>
          {doc?.last_modified_at && (
            <p className="text-xs mt-1" style={{ color: "var(--muted)" }}>
              Last saved {new Date(doc.last_modified_at).toLocaleString()}
            </p>
          )}
        </div>

        <div className="flex items-end gap-3">
          <label className="flex flex-col gap-1">
            <span className="text-xs font-medium" style={{ color: "var(--muted)" }}>
              Version
            </span>
            <input
              type="text"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              maxLength={32}
              placeholder="1.0"
              className="px-3 py-2 text-sm font-mono"
              style={{
                border: "1px solid var(--line-2)",
                borderRadius: "var(--r-sm)",
                background: "var(--surface)",
                color: "var(--ink)",
                width: 100,
              }}
            />
          </label>
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="btn btn-primary"
          >
            {saving ? "Saving..." : "Save & publish"}
          </button>
        </div>
      </div>

      {/* Split-pane: textarea on the left, live preview on the right.
          A full WYSIWYG (TipTap/Lexical) is heavier and adds a new
          editor dep; markdown + live preview hits the same workflow
          contract for legal copy and keeps the bundle slim. */}
      <div className="grid lg:grid-cols-2 gap-4">
        <div>
          <div className="eyebrow mb-2">Markdown source</div>
          <textarea
            value={contentMd}
            onChange={(e) => setContentMd(e.target.value)}
            spellCheck
            className="w-full font-mono text-sm"
            style={{
              minHeight: 520,
              padding: 14,
              border: "1px solid var(--line-2)",
              borderRadius: "var(--r-sm)",
              background: "var(--bg-2)",
              color: "var(--ink)",
              resize: "vertical",
              lineHeight: 1.6,
            }}
          />
          <p className="text-xs mt-2" style={{ color: "var(--muted)" }}>
            HTML in markdown is stripped server-side before storage.
          </p>
        </div>

        <div>
          <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
            <div className="eyebrow">Preview</div>
            <div className="flex rounded-md border border-[var(--line)] overflow-hidden text-xs">
              <button
                type="button"
                className="px-3 py-1.5 font-medium"
                style={{
                  background: previewMode === "draft" ? "var(--bg-2)" : "transparent",
                  color: previewMode === "draft" ? "var(--ink)" : "var(--muted)",
                }}
                onClick={() => setPreviewMode("draft")}
              >
                Draft (markdown)
              </button>
              <button
                type="button"
                className="px-3 py-1.5 font-medium border-l border-[var(--line)]"
                style={{
                  background: previewMode === "published" ? "var(--bg-2)" : "transparent",
                  color: previewMode === "published" ? "var(--ink)" : "var(--muted)",
                }}
                onClick={() => setPreviewMode("published")}
              >
                Published (DB HTML)
              </button>
            </div>
          </div>
          <div
            className="overflow-y-auto"
            style={{
              minHeight: 520,
              maxHeight: 720,
              padding: 16,
              border: "1px solid var(--line)",
              borderRadius: "var(--r-sm)",
              background: "var(--surface)",
            }}
          >
            {previewMode === "draft" ? (
              <LegalMarkdown markdown={contentMd} />
            ) : (
              <LegalPublishedPreview html={doc?.content_html ?? ""} />
            )}
          </div>
          {previewMode === "published" && (
            <p className="text-xs mt-2" style={{ color: "var(--muted)" }}>
              Matches what candidates see after save — HTML is bleach-sanitized on the server.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
