"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Copy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/Icon";
import { ModalPortal } from "@/components/shared/ModalPortal";
import { btnClass } from "@/lib/cn-ui";
import { cn } from "@/lib/utils";
import { notify } from "@/lib/toast";
import type { ApplyModalJob } from "@/components/jobs/applyContacts";
import {
  buildEmailIntroduction,
  buildEmailSubject,
  resolveApplyAction,
  resolveApplyContactMethods,
  type ApplyContactKind,
  type ApplyJobFields,
} from "@/lib/applyLink";

const KIND_ICON: Record<ApplyContactKind, string> = {
  email: "user",
  whatsapp: "whatsapp",
  phone: "user",
  website: "external",
};

export interface ApplyModalProps {
  job: ApplyModalJob | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ApplyModal({ job, open, onOpenChange }: ApplyModalProps) {
  const fields = job as ApplyJobFields | null;
  const primary = useMemo(
    () => (fields ? resolveApplyAction(fields) : null),
    [fields],
  );
  const methods = useMemo(
    () => (fields ? resolveApplyContactMethods(fields) : []),
    [fields],
  );
  const emailIntro = useMemo(
    () => (fields ? buildEmailIntroduction(fields) : ""),
    [fields],
  );
  const emailSubject = useMemo(
    () => (fields ? buildEmailSubject(fields) : ""),
    [fields],
  );
  const hasEmail = Boolean(fields?.apply_email?.trim());
  const showWebsitePrimary = Boolean(primary?.external && primary.href.startsWith("http"));
  const [copying, setCopying] = useState<string | null>(null);

  const close = useCallback(() => onOpenChange(false), [onOpenChange]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, close]);

  const copy = useCallback(async (value: string, key: string) => {
    setCopying(key);
    try {
      await navigator.clipboard.writeText(value);
      notify.custom.success("Copied to clipboard");
    } catch {
      notify.error("Could not copy — try selecting the text manually");
    } finally {
      setCopying(null);
    }
  }, []);

  if (!open) return null;

  return (
    <ModalPortal>
      <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4">
        <div className="modal-backdrop" onClick={close} aria-hidden />
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="apply-modal-title"
          className="modal-panel w-full max-w-md rounded-2xl p-5 sm:p-6 max-h-[min(90vh,640px)] overflow-y-auto"
        >
          <header className="flex items-start justify-between gap-3 mb-4">
            <div className="min-w-0 pr-2">
              <h2
                id="apply-modal-title"
                className="font-display text-lg leading-tight"
              >
                How to apply
              </h2>
              <p className="text-sm mt-1" style={{ color: "var(--muted)" }}>
                {job ? (
                  <>
                    <span className="font-medium" style={{ color: "var(--ink)" }}>
                      {job.title}
                    </span>
                    {job.company ? (
                      <>
                        {" "}
                        at {job.company}
                      </>
                    ) : null}
                  </>
                ) : (
                  "Copy contact details and paste into your email or browser"
                )}
              </p>
            </div>
            <button
              type="button"
              onClick={close}
              aria-label="Close"
              className="shrink-0 w-8 h-8 rounded-full flex items-center justify-center"
              style={{ border: "1px solid var(--line-2)", color: "var(--muted)" }}
            >
              <Icon name="x" size={14} />
            </button>
          </header>

          {showWebsitePrimary && primary ? (
            <div className="flex flex-col gap-2 mb-4">
              <a
                href={primary.href}
                className={cn(btnClass("primary"), "w-full justify-center gap-2")}
                target="_blank"
                rel="noopener noreferrer"
                data-testid="apply-modal-primary"
              >
                {primary.label}
                <Icon name="external" size={14} />
              </a>
            </div>
          ) : null}

          {methods.length > 0 ? (
            <>
              {showWebsitePrimary && methods.length > 1 ? (
                <p
                  className="text-xs font-medium uppercase tracking-wide mb-2"
                  style={{ color: "var(--muted)" }}
                >
                  Or copy details
                </p>
              ) : null}
              <ul className="flex flex-col gap-3">
                {methods.map((method, index) => {
                  const key = `${method.kind}-${method.copyValue}`;
                  const fieldId = `apply-method-${index}`;
                  const openExternal =
                    method.kind === "website" || method.kind === "whatsapp";
                  return (
                    <li
                      key={key}
                      className="flex items-center gap-3 rounded-lg border p-3"
                      style={{
                        borderColor: "var(--line)",
                        background: "var(--bg-2)",
                      }}
                    >
                      <span
                        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full"
                        style={{
                          background: "var(--surface)",
                          color: "var(--ink)",
                          border: "1px solid var(--line)",
                        }}
                        aria-hidden
                      >
                        <Icon name={KIND_ICON[method.kind]} size={16} />
                      </span>
                      <div className="min-w-0 flex-1">
                        <label
                          htmlFor={method.href ? undefined : fieldId}
                          className="text-xs font-medium uppercase tracking-wide"
                          style={{ color: "var(--muted)" }}
                        >
                          {method.label}
                        </label>
                        {method.href && openExternal ? (
                          <a
                            href={method.href}
                            className="block truncate text-sm font-medium text-primary underline-offset-2 hover:underline"
                            target="_blank"
                            rel="noopener noreferrer"
                          >
                            {method.display}
                          </a>
                        ) : (
                          <p
                            id={fieldId}
                            className="truncate text-sm font-medium"
                            style={{ color: "var(--ink)" }}
                          >
                            {method.display}
                          </p>
                        )}
                      </div>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        className="shrink-0"
                        disabled={copying === key}
                        onClick={() => void copy(method.copyValue, key)}
                      >
                        <Copy className="size-3.5" aria-hidden />
                        Copy
                      </Button>
                    </li>
                  );
                })}
              </ul>
            </>
          ) : (
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              No direct apply link is listed yet. Check the job description below or
              contact support if you need help.
            </p>
          )}

          {hasEmail ? (
            <div
              className="rounded-lg border p-3 mt-4"
              style={{
                borderColor: "var(--line)",
                background: "var(--bg-2)",
              }}
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <div>
                  <p
                    className="text-xs font-medium uppercase tracking-wide"
                    style={{ color: "var(--muted)" }}
                  >
                    Email introduction
                  </p>
                  <p className="text-[11px] mt-0.5" style={{ color: "var(--muted)" }}>
                    Subject: {emailSubject}
                  </p>
                </div>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="shrink-0"
                  disabled={copying === "email-intro"}
                  onClick={() => void copy(emailIntro, "email-intro")}
                >
                  <Copy className="size-3.5" aria-hidden />
                  Copy
                </Button>
              </div>
              <p
                className="text-sm leading-relaxed whitespace-pre-wrap"
                style={{ color: "var(--ink)" }}
              >
                {emailIntro}
              </p>
            </div>
          ) : null}

          {job?.application_instructions ? (
            <p
              className="text-xs leading-relaxed border-t pt-3 mt-4"
              style={{ color: "var(--muted)", borderColor: "var(--line)" }}
            >
              {job.application_instructions}
            </p>
          ) : null}
        </div>
      </div>
    </ModalPortal>
  );
}
