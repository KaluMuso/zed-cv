"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize from "rehype-sanitize";

type MarkdownDescriptionFieldProps = {
  value: string;
  onChange: (value: string) => void;
  label?: string;
};

import { useRef } from "react";
import { Button } from "@/components/ui/button";

export function MarkdownDescriptionField({
  value,
  onChange,
  label = "Description (Markdown)",
}: MarkdownDescriptionFieldProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const insertMarkdown = (type: "bold" | "heading" | "list" | "link") => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const text = value;

    const before = text.slice(0, start);
    const selected = text.slice(start, end);
    const after = text.slice(end);

    let newText = "";
    let newStart = start;
    let newEnd = end;

    if (type === "bold") {
      if (selected) {
        newText = before + `**${selected}**` + after;
        newStart = start + 2;
        newEnd = end + 2;
      } else {
        newText = before + "**bold**" + after;
        newStart = start + 2;
        newEnd = start + 6;
      }
    } else if (type === "heading") {
      const lastNewline = before.lastIndexOf("\n");
      const lineStart = lastNewline === -1 ? 0 : lastNewline + 1;
      const lineBefore = text.slice(0, lineStart);
      const lineAfter = text.slice(lineStart);
      
      newText = lineBefore + "## " + lineAfter;
      newStart = start + 3;
      newEnd = end + 3;
    } else if (type === "list") {
      const lastNewline = before.lastIndexOf("\n");
      const lineStart = lastNewline === -1 ? 0 : lastNewline + 1;
      const lineBefore = text.slice(0, lineStart);
      const lineAfter = text.slice(lineStart);

      newText = lineBefore + "- " + lineAfter;
      newStart = start + 2;
      newEnd = end + 2;
    } else if (type === "link") {
      if (selected) {
        newText = before + `[${selected}](url)` + after;
        newStart = start + selected.length + 3;
        newEnd = newStart + 3;
      } else {
        newText = before + "[text](url)" + after;
        newStart = start + 1;
        newEnd = start + 5;
      }
    }

    onChange(newText);

    setTimeout(() => {
      textarea.focus();
      textarea.setSelectionRange(newStart, newEnd);
    }, 0);
  };

  return (
    <div className="grid lg:grid-cols-2 gap-4">
      <div>
        <label className="text-sm font-medium block mb-2">{label} *</label>
        <div className="flex items-center gap-1 mb-2 p-1 bg-muted/40 rounded-md border border-input">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => insertMarkdown("bold")}
            aria-label="Bold"
            className="h-8 w-8 p-0"
          >
            <span className="font-bold text-sm">B</span>
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => insertMarkdown("heading")}
            aria-label="Heading"
            className="h-8 w-8 p-0"
          >
            <span className="font-bold text-sm">H</span>
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => insertMarkdown("list")}
            aria-label="Bullet list"
            className="h-8 w-8 p-0"
          >
            <span className="font-bold text-base leading-none">•</span>
          </Button>
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => insertMarkdown("link")}
            aria-label="Link"
            className="h-8 w-8 p-0"
          >
            <span className="text-sm">🔗</span>
          </Button>
        </div>
        <textarea
          ref={textareaRef}
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
