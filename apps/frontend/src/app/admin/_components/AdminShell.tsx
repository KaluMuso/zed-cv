"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ADMIN_NAV, adminSectionFromPath } from "../admin-nav";

export function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() ?? "";
  const current = adminSectionFromPath(pathname);
  const sectionMeta =
    ADMIN_NAV.find((n) => n.slug === current) ??
    (pathname.includes("/jobs/review")
      ? {
          slug: "jobs" as const,
          label: "Review queue",
          description: "Jobs flagged for admin review",
          href: "/admin/jobs/review",
        }
      : ADMIN_NAV[0]);

  return (
    <div className="max-w-7xl mx-auto w-full">
      <div className="mb-8">
        <div className="text-xs font-medium uppercase tracking-wider text-muted-foreground mb-2">
          Admin
        </div>
        <h1 className="text-2xl font-bold tracking-tight">{sectionMeta.label}</h1>
        <p className="text-sm text-muted-foreground mt-1">{sectionMeta.description}</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[200px_minmax(0,1fr)] gap-8 lg:gap-10">
        <nav
          className="flex lg:flex-col gap-1 overflow-x-auto pb-2 lg:pb-0 lg:sticky lg:top-24 lg:self-start"
          aria-label="Admin sections"
        >
          {ADMIN_NAV.map((item) => {
            const active =
              current === item.slug ||
              (item.slug === "jobs" && pathname.startsWith("/admin/jobs"));
            return (
              <Link
                key={item.slug}
                href={item.href}
                className="shrink-0 rounded-lg px-3 py-2 text-sm font-medium transition-colors border"
                style={{
                  background: active ? "var(--bg-2, hsl(var(--muted) / 0.15))" : "transparent",
                  color: active ? "var(--ink, inherit)" : "var(--muted-foreground)",
                  borderColor: active ? "hsl(var(--border))" : "transparent",
                }}
              >
                {item.label}
              </Link>
            );
          })}
          {pathname.startsWith("/admin/jobs/review") ? (
            <Link
              href="/admin/jobs/review"
              className="shrink-0 rounded-lg px-3 py-2 text-sm font-medium border border-amber-300 bg-amber-50 text-amber-900 dark:border-amber-800 dark:bg-amber-950/90 dark:text-amber-100"
            >
              Review queue
            </Link>
          ) : null}
        </nav>

        <div className="min-w-0">
          {children}
          <p className="mt-10 text-xs text-muted-foreground leading-relaxed max-w-2xl">
            API automation: use{" "}
            <code className="text-[11px]">Authorization: Bearer &lt;superadmin JWT&gt;</code> or{" "}
            <code className="text-[11px]">X-ADMIN-API-KEY</code> — do not use a browser session JWT
            as the API key (<span className="font-mono text-[11px]">docs/ADMIN_API_KEYS.md</span>).
          </p>
        </div>
      </div>
    </div>
  );
}
