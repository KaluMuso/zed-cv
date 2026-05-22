"use client";

import { Icon } from "@/components/ui/Icon";
import { notify } from "@/lib/toast";
import { useTailoredCvBuilderStore } from "./store";
import { AtsLivePreview } from "./AtsLivePreview";

export function LivePreviewPane({ className = "" }: { className?: string }) {
  const draft = useTailoredCvBuilderStore((s) => s.draft);

  const onDownloadPdf = () => {
    notify.info("PDF export is coming soon. Your live preview updates as you type.");
  };

  return (
    <div
      className={`relative flex flex-col min-h-0 rounded-lg ${className}`}
      style={{
        background: "var(--bg-2)",
        border: "1px solid var(--line)",
      }}
    >
      <div
        className="sticky top-0 z-10 flex items-center justify-between gap-2 px-4 py-3 border-b"
        style={{ borderColor: "var(--line)", background: "var(--bg-2)" }}
      >
        <span className="eyebrow">Live preview</span>
        <button
          type="button"
          onClick={onDownloadPdf}
          className="btn btn-primary btn-sm shadow-md"
          aria-label="Download PDF"
        >
          <Icon name="download" size={14} />
          Download PDF
        </button>
      </div>

      <div className="flex-1 overflow-auto p-4 sm:p-6">
        <AtsLivePreview draft={draft} />
      </div>
    </div>
  );
}
