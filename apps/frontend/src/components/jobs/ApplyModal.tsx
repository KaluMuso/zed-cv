"use client";

import { useCallback, useMemo, useState } from "react";
import { Copy } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Icon } from "@/components/ui/Icon";
import { notify } from "@/lib/toast";
import {
  buildApplyContactMethods,
  type ApplyContactKind,
  type ApplyModalJob,
} from "@/components/jobs/applyContacts";

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
  const methods = useMemo(
    () => (job ? buildApplyContactMethods(job) : []),
    [job],
  );
  const [copying, setCopying] = useState<string | null>(null);

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

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent
        className="sm:max-w-md bg-popover text-popover-foreground dark:bg-popover dark:text-popover-foreground"
        showCloseButton
      >
        <DialogHeader>
          <DialogTitle className="text-foreground dark:text-foreground pr-8">
            How to apply
          </DialogTitle>
          <DialogDescription className="text-muted-foreground dark:text-muted-foreground">
            {job ? (
              <>
                <span className="font-medium text-foreground dark:text-foreground">
                  {job.title}
                </span>
                {job.company ? (
                  <span className="text-muted-foreground dark:text-muted-foreground">
                    {" "}
                    at {job.company}
                  </span>
                ) : null}
              </>
            ) : (
              "Contact details for this role"
            )}
          </DialogDescription>
        </DialogHeader>

        {methods.length === 0 ? (
          <p className="text-sm text-muted-foreground dark:text-muted-foreground">
            No direct contact details were listed for this role. Check the job
            description below or reach out via the original listing.
          </p>
        ) : (
          <ul className="flex flex-col gap-3">
            {methods.map((method) => {
              const key = `${method.kind}-${method.copyValue}`;
              return (
                <li
                  key={key}
                  className="flex items-center gap-3 rounded-lg border border-border bg-background/60 p-3 dark:border-border dark:bg-background/40"
                >
                  <span
                    className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-muted text-foreground dark:bg-muted dark:text-foreground"
                    aria-hidden
                  >
                    <Icon name={KIND_ICON[method.kind]} size={16} />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground dark:text-muted-foreground">
                      {method.label}
                    </p>
                    {method.href ? (
                      <a
                        href={method.href}
                        className="block truncate text-sm font-medium text-primary underline-offset-2 hover:underline dark:text-primary"
                        target={method.kind === "website" || method.kind === "whatsapp" ? "_blank" : undefined}
                        rel={
                          method.kind === "website" || method.kind === "whatsapp"
                            ? "noopener noreferrer"
                            : undefined
                        }
                      >
                        {method.display}
                      </a>
                    ) : (
                      <p className="truncate text-sm font-medium text-foreground dark:text-foreground">
                        {method.display}
                      </p>
                    )}
                  </div>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    className="shrink-0 dark:border-border dark:bg-background dark:hover:bg-muted"
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
        )}

        {job?.application_instructions ? (
          <p className="text-xs leading-relaxed text-muted-foreground dark:text-muted-foreground border-t border-border pt-3 dark:border-border">
            {job.application_instructions}
          </p>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}
