"use client";

import { ArrowUpRight, Check, Globe, Mail, MessageCircle } from "lucide-react";
import { cn } from "@/lib/utils";

const channels = [
  {
    label: "EMAIL",
    value: "careers@zanaco.co.zm",
    icon: Mail,
  },
  {
    label: "WHATSAPP",
    value: "+260 211 221 222",
    icon: MessageCircle,
  },
  {
    label: "WEBSITE",
    value: "zanaco.co.zm/careers",
    icon: Globe,
  },
] as const;

/** Apply channels mock below hero WhatsApp card (marketing decoration). */
export function ApplyChannelsDetectedCard({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "w-full max-w-[300px] rounded-md border border-border bg-card p-4 shadow-xl sm:max-w-[320px]",
        className
      )}
      role="img"
      aria-label="Apply channels detected for ZANACO Senior Accountant"
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-2.5">
        <span className="font-mono text-[9px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
          Apply channels detected
        </span>
        <span className="inline-flex items-center gap-1 text-[10px] font-medium text-brand">
          <Check className="h-3 w-3" aria-hidden />
          verified
        </span>
      </div>
      <p className="mt-2 font-display text-sm text-foreground">
        ZANACO · Senior Accountant
      </p>
      <ul className="mt-3 flex flex-col gap-2.5">
        {channels.map(({ label, value, icon: Icon }) => (
          <li
            key={label}
            className="flex items-start justify-between gap-2 rounded-sm bg-bg-2/80 px-2.5 py-2"
          >
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <Icon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" aria-hidden />
                <span className="font-mono text-[9px] font-medium tracking-wider text-muted-foreground">
                  {label}
                </span>
              </div>
              <p className="mt-1 truncate pl-5 text-[12px] text-muted-foreground">{value}</p>
            </div>
            <ArrowUpRight
              className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground"
              aria-hidden
            />
          </li>
        ))}
      </ul>
    </div>
  );
}
