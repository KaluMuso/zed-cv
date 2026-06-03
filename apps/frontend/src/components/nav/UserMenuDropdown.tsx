"use client";

import Link from "next/link";
import { Icon } from "@/components/ui/Icon";
import { Avatar } from "@/components/ui/Avatar";
import { settingsPath } from "@/app/settings/settings-nav";

type MenuItem = {
  href: string;
  label: string;
  icon: string;
};

function MenuSection({
  title,
  items,
  onClose,
  footnote,
}: {
  title: string;
  items: MenuItem[];
  onClose: () => void;
  footnote?: string;
}) {
  if (items.length === 0) return null;

  return (
    <div className="py-1">
      <div
        className="px-4 py-1.5 text-[10px] font-semibold uppercase tracking-wider"
        style={{ color: "var(--muted)" }}
      >
        {title}
      </div>
      {items.map((item) => (
        <Link
          key={item.href + item.label}
          href={item.href}
          onClick={onClose}
          className="flex items-center gap-2.5 px-4 py-2.5 text-sm hover:bg-[var(--bg-2)] transition-colors"
          style={{ color: "var(--ink-2)" }}
          role="menuitem"
        >
          <Icon name={item.icon} size={16} className="shrink-0 opacity-80" />
          {item.label}
        </Link>
      ))}
      {footnote ? (
        <p
          className="px-4 pb-2 pt-0.5 text-[10px] leading-snug"
          style={{ color: "var(--muted)" }}
        >
          {footnote}
        </p>
      ) : null}
    </div>
  );
}

function canAccessCvGenerator(tier: string | null | undefined): boolean {
  return (
    tier === "starter" ||
    tier === "professional" ||
    tier === "super_standard"
  );
}

export function UserMenuDropdown({
  displayName,
  tierSubtitle,
  subscriptionTier,
  onClose,
  onSignOut,
  showAdmin,
}: {
  displayName: string;
  tierSubtitle: string;
  subscriptionTier?: string | null;
  onClose: () => void;
  onSignOut: () => void;
  showAdmin?: boolean;
}) {
  const engagementLinks: MenuItem[] = [
    { href: "/dashboard", label: "Dashboard", icon: "home" },
  ];

  const notifications: MenuItem[] = [
    { href: "/matches", label: "Match digests", icon: "sparkle" },
    {
      href: settingsPath("notifications"),
      label: "Channel preferences",
      icon: "bell",
    },
    { href: settingsPath("billing"), label: "Invoices & billing", icon: "file" },
  ];

  const careerData: MenuItem[] = [
    { href: "/profile", label: "Profile (CV & Skills)", icon: "user" },
    ...(canAccessCvGenerator(subscriptionTier)
      ? [
          {
            href: "/profile?tab=cv-generator",
            label: "CV Generator",
            icon: "file",
          },
        ]
      : []),
    { href: "/matches", label: "My matches", icon: "sparkle" },
  ];

  const account: MenuItem[] = [
    { href: settingsPath("account"), label: "Settings", icon: "settings" },
    ...(showAdmin
      ? [{ href: "/admin", label: "Admin", icon: "shield" }]
      : []),
  ];

  return (
    <div
      className="absolute right-0 top-full mt-2 w-64 py-2 rounded-xl z-50"
      style={{
        background: "var(--surface)",
        border: "1px solid var(--line)",
        boxShadow: "var(--shadow-lg)",
      }}
      role="menu"
    >
      <div className="px-4 py-3 border-b" style={{ borderColor: "var(--line)" }}>
        <div className="font-semibold text-sm truncate" style={{ color: "var(--ink)" }}>
          {displayName}
        </div>
        {tierSubtitle ? (
          <div className="text-xs mt-0.5 truncate" style={{ color: "var(--muted)" }}>
            {tierSubtitle}
          </div>
        ) : null}
      </div>

      <MenuSection title="Engagement" items={engagementLinks} onClose={onClose} />
      <MenuSection
        title="Notifications"
        items={notifications}
        onClose={onClose}
        footnote="Web push is a browser permission, not an in-app notification feed."
      />
      <MenuSection title="Career data" items={careerData} onClose={onClose} />
      <MenuSection title="Account" items={account} onClose={onClose} />

      <hr style={{ borderColor: "var(--line)" }} className="my-1" />
      <button
        type="button"
        onClick={() => {
          onClose();
          onSignOut();
        }}
        className="flex w-full items-center gap-2.5 px-4 py-2.5 text-sm hover:bg-[var(--bg-2)] transition-colors text-left"
        style={{ color: "var(--danger)" }}
        role="menuitem"
      >
        <Icon name="arrowLeft" size={16} className="shrink-0" />
        Sign out
      </button>
    </div>
  );
}

export function UserMenuTrigger({
  displayName,
  open,
  onToggle,
}: {
  displayName: string;
  open: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="relative flex items-center gap-2 rounded-lg py-1 pl-1 pr-2 hover:bg-[var(--bg-2)] transition-colors"
      aria-expanded={open}
      aria-haspopup="menu"
      aria-label={`${displayName} account menu`}
    >
      <Avatar name={displayName} size={36} />
      <Icon name="chevronDown" size={14} />
    </button>
  );
}
