"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";

type MarkdownDescriptionFieldProps = {
  value: string;
  onChange: (value: string) => void;
  label?: string;
};

export function MarkdownDescriptionField({
  value,
  onChange,
  label = "Description (Markdown)",
}: MarkdownDescriptionFieldProps) {
  return (
    <div className="grid lg:grid-cols-2 gap-4">
      <div>
        <label className="text-sm font-medium block mb-2">{label} *</label>
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          className="w-full font-mono text-sm min-h-[420px] rounded-md border border-input bg-background p-3"
          spellCheck
          data-testid="admin-job-description-md"
        />
        <p className="text-xs text-muted-foreground mt-2">
          HTML in markdown is stripped server-side before storage.
        </p>
      </div>
      <div>
        <div className="text-sm font-medium mb-2">Live preview</div>
        <div
          className="prose prose-sm dark:prose-invert max-w-none min-h-[420px] rounded-md border border-border p-4 overflow-y-auto bg-muted/20"
          data-testid="admin-job-description-preview"
        >
          {value.trim() ? (
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>
              {value}
            </ReactMarkdown>
          ) : (
            <p className="text-muted-foreground text-sm">Preview appears as you type.</p>
          )}
        </div>
      </div>
    </div>
  );
}
