"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Icon } from "@/components/ui/Icon";
import { cn } from "@/lib/utils";
import { tierAtLeast } from "@/lib/tier-features";

const SUB_LINKS = [
  { href: "/interview-prep/mock", label: "Mock Interview" },
  { href: "/interview-prep/aptitude", label: "Aptitude Tests" },
  { href: "/interview-prep/history", label: "History" },
] as const;

const PREMIUM_PURPLE = "#a855f7";

type InterviewPrepNavProps = {
  className?: string;
  subscriptionTier?: string | null;
  /** Mobile drawer: render as stacked links instead of dropdown */
  variant?: "dropdown" | "stacked";
  onNavigate?: () => void;
};

function hasInterviewPrepAccess(tier: string | null | undefined): boolean {
  return tierAtLeast(tier, "super_standard");
}

export function InterviewPrepNav({
  className,
  subscriptionTier,
  variant = "dropdown",
  onNavigate,
}: InterviewPrepNavProps) {
  const pathname = usePathname();
  const active = pathname.startsWith("/interview-prep");
  const premium = !hasInterviewPrepAccess(subscriptionTier);

  const labelClass = cn(
    premium && "font-medium",
    className,
  );
  const labelStyle = premium
    ? { color: PREMIUM_PURPLE }
    : undefined;

  const prepLabel = (
    <>
      <Icon
        name="sparkle"
        size={14}
        className="shrink-0"
        style={premium ? { color: PREMIUM_PURPLE } : undefined}
        aria-hidden
      />
      Interview Prep
    </>
  );

  if (variant === "stacked") {
    return (
      <div className={cn("flex flex-col gap-1", className)}>
        <Link
          href="/interview-prep"
          onClick={onNavigate}
          className={cn(
            "font-display text-2xl py-2 transition-colors pl-4 inline-flex items-center gap-2",
            active && !premium && "text-primary",
          )}
          style={labelStyle}
        >
          {prepLabel}
        </Link>
        {SUB_LINKS.map((link) => (
          <Link
            key={link.href}
            href={link.href}
            onClick={onNavigate}
            className={cn(
              "font-display text-xl py-2 transition-colors pl-8",
              pathname === link.href && !premium ? "text-primary" : "text-ink-2",
            )}
            style={premium ? { color: "var(--ink-2)" } : undefined}
          >
            {link.label}
          </Link>
        ))}
      </div>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        className={cn(
          "nav-link inline-flex items-center gap-1.5 bg-transparent border-0 cursor-pointer font-inherit",
          active && !premium && "active",
          labelClass,
        )}
        style={labelStyle}
        aria-label="Interview prep menu"
      >
        {prepLabel}
        <Icon name="chevronDown" size={14} className="opacity-70" aria-hidden />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="min-w-[200px]">
        <DropdownMenuItem>
          <Link href="/interview-prep" className="w-full">
            Overview
          </Link>
        </DropdownMenuItem>
        {SUB_LINKS.map((link) => (
          <DropdownMenuItem key={link.href}>
            <Link href={link.href} className="w-full">
              {link.label}
            </Link>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
