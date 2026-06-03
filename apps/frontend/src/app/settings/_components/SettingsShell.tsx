"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { Icon } from "@/components/ui/Icon";
import { SETTINGS_NAV, settingsPath, type SettingsSection } from "../settings-nav";

function activeSection(pathname: string): SettingsSection {
  const slug = pathname.replace(/^\/settings\/?/, "").split("/")[0];
  const found = SETTINGS_NAV.find((n) => n.slug === slug);
  return found?.slug ?? "account";
}

export function SettingsShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, isLoading } = useAuth();
  const current = activeSection(pathname ?? "");

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.replace("/auth?next=/settings/account");
    }
  }, [isAuthenticated, isLoading, router]);

  if (isLoading || !isAuthenticated) {
    return (
      <div className="max-w-[1280px] mx-auto px-6 py-12">
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          Loading settings…
        </p>
      </div>
    );
  }

  const sectionMeta = SETTINGS_NAV.find((n) => n.slug === current) ?? SETTINGS_NAV[0];

  return (
    <div className="max-w-[1280px] mx-auto px-6 py-8 md:py-12">
      <div className="mb-8">
        <div className="eyebrow mb-2">Settings</div>
        <h1
          className="font-display text-foreground"
          style={{
            fontSize: "clamp(2rem, 4vw, 2.75rem)",
            letterSpacing: "-0.02em",
            lineHeight: 1.1,
          }}
        >
          Your{" "}
          <span className="italic" style={{ color: "var(--copper-500)" }}>
            preferences
          </span>
        </h1>
        <p className="text-sm mt-2" style={{ color: "var(--muted)" }}>
          {sectionMeta.description}
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[220px_minmax(0,1fr)] gap-8 lg:gap-12">
        <nav
          className="flex lg:flex-col gap-1 overflow-x-auto pb-2 lg:pb-0 lg:sticky lg:top-24 lg:self-start"
          aria-label="Settings sections"
        >
          {SETTINGS_NAV.map((item) => {
            const active = current === item.slug;
            const isDanger = item.slug === "danger";
            return (
              <Link
                key={item.slug}
                href={settingsPath(item.slug)}
                className="shrink-0 rounded-lg px-4 py-2.5 text-sm font-medium transition-colors"
                style={{
                  background: active ? "var(--bg-2)" : "transparent",
                  color: isDanger
                    ? active
                      ? "var(--danger)"
                      : "var(--danger)"
                    : active
                      ? "var(--ink)"
                      : "var(--muted)",
                  border: active ? "1px solid var(--line)" : "1px solid transparent",
                }}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="min-w-0">{children}</div>
      </div>
    </div>
  );
}

export function SettingsSectionHeader({
  title,
  action,
}: {
  title: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 mb-6">
      <h2 className="font-display text-xl text-foreground" style={{ letterSpacing: "-0.01em" }}>
        {title}
      </h2>
      {action}
    </div>
  );
}

export function SettingsCard({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return <div className={`card p-6 ${className}`.trim()}>{children}</div>;
}

export function SettingsRow({
  label,
  value,
  action,
}: {
  label: string;
  value: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div
      className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 py-4 first:pt-0 last:pb-0"
      style={{ borderBottom: "1px solid var(--line)" }}
    >
      <div>
        <div
          className="text-xs font-medium uppercase tracking-wider mb-1"
          style={{ color: "var(--muted)" }}
        >
          {label}
        </div>
        <div className="text-sm font-medium" style={{ color: "var(--ink)" }}>
          {value}
        </div>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}

export function SettingsEditLink({
  onClick,
  children = "Edit",
}: {
  onClick: () => void;
  children?: string;
}) {
  return (
    <button type="button" className="btn btn-outline btn-sm" onClick={onClick}>
      {children}
    </button>
  );
}

export function VerifiedBadge() {
  return (
    <span className="tag tag-green inline-flex items-center gap-1 text-xs">
      <Icon name="check" size={10} />
      verified
    </span>
  );
}
