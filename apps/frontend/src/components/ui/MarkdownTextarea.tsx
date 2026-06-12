import React, { useRef } from "react";
import { Icon } from "./Icon";

type MarkdownTextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement> & {
  value: string;
  onChangeValue: (val: string) => void;
};

export function MarkdownTextarea({
  value,
  onChangeValue,
  className,
  style,
  disabled,
  ...props
}: MarkdownTextareaProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const insertText = (before: string, after: string = "", defaultText: string = "") => {
    const el = textareaRef.current;
    if (!el || disabled) return;

    const start = el.selectionStart;
    const end = el.selectionEnd;
    const selectedText = value.substring(start, end);

    const replacement = before + (selectedText || defaultText) + after;
    const newValue = value.substring(0, start) + replacement + value.substring(end);

    onChangeValue(newValue);

    // Set focus back and select the inner text
    setTimeout(() => {
      el.focus();
      if (selectedText) {
        el.setSelectionRange(start + before.length, start + before.length + selectedText.length);
      } else {
        el.setSelectionRange(start + before.length, start + before.length + defaultText.length);
      }
    }, 0);
  };

  const buttons = [
    {
      icon: "bold" as const,
      label: "Bold",
      action: () => insertText("**", "**", "bold text"),
    },
    {
      icon: "italic" as const,
      label: "Italic",
      action: () => insertText("_", "_", "italic text"),
    },
    {
      icon: "list" as const,
      label: "Bullet List",
      action: () => insertText("\n- ", "", "list item"),
    },
    {
      icon: "link" as const,
      label: "Link",
      action: () => insertText("[", "](url)", "link text"),
    },
  ];

  return (
    <div className={`flex flex-col border rounded-md overflow-hidden ${className || ""}`} style={style}>
      <div className="flex items-center gap-1 p-1 border-b bg-[var(--paper-2)]" style={{ borderColor: "var(--line-2)" }}>
        {buttons.map((b) => (
          <button
            key={b.label}
            type="button"
            disabled={disabled}
            onClick={b.action}
            className="p-1.5 rounded-md hover:bg-[var(--line-2)] text-[var(--ink-2)] disabled:opacity-50 transition-colors"
            title={b.label}
          >
            <Icon name={b.icon} size={14} />
          </button>
        ))}
      </div>
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChangeValue(e.target.value)}
        disabled={disabled}
        className="w-full p-3 text-sm leading-relaxed outline-none border-none resize-y min-h-[100px]"
        style={{ background: "transparent", color: "inherit", fontFamily: "inherit" }}
        {...props}
      />
    </div>
  );
}
