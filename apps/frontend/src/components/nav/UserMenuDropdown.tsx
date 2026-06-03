"use client";

import { useState } from "react";
import Link from "next/link";
import { Icon } from "@/components/ui/Icon";
import { Avatar } from "@/components/ui/Avatar";
import { settingsPath } from "@/app/settings/settings-nav";
import { NotificationsPanel } from "@/components/nav/NotificationsPanel";

type MenuItem = {
  href: string;
  label: string;
  icon: string;
};

function MenuSection({
  title,
  items,
  onClose,
}: {
  title: string;
  items: MenuItem[];
  onClose: () => void;
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
  unreadCount = 0,
  onUnreadCountChange,
}: {
  displayName: string;
  tierSubtitle: string;
  subscriptionTier?: string | null;
  onClose: () => void;
  onSignOut: () => void;
  showAdmin?: boolean;
  unreadCount?: number;
  onUnreadCountChange?: (count: number) => void;
}) {
  const [panel, setPanel] = useState<"menu" | "notifications">("menu");

  const engagementLinks: MenuItem[] = [
    { href: "/dashboard", label: "Dashboard", icon: "home" },
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

  if (panel === "notifications") {
    return (
      <div
        className="absolute right-0 top-full mt-2 w-80 rounded-xl z-50 overflow-hidden"
        style={{
          background: "var(--surface)",
          border: "1px solid var(--line)",
          boxShadow: "var(--shadow-lg)",
        }}
        role="menu"
      >
        <NotificationsPanel
          onBack={() => setPanel("menu")}
          onClose={onClose}
          onUnreadCountChange={onUnreadCountChange}
        />
      </div>
    );
  }

  return (
    <div
      className="absolute right-0 top-full mt-2 w-56 py-2 rounded-xl z-50"
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

      <div className="py-1">
        <div
          className="px-4 py-1.5 text-[10px] font-semibold uppercase tracking-wider"
          style={{ color: "var(--muted)" }}
        >
          Engagement
        </div>
        {engagementLinks.map((item) => (
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
        <button
          type="button"
          onClick={() => setPanel("notifications")}
          className="flex w-full items-center gap-2.5 px-4 py-2.5 text-sm hover:bg-[var(--bg-2)] transition-colors text-left"
          style={{ color: "var(--ink-2)" }}
          role="menuitem"
        >
          <Icon name="bell" size={16} className="shrink-0 opacity-80" />
          <span className="flex-1">Notifications</span>
          {unreadCount > 0 ? (
            <span
              className="min-w-[1.25rem] h-5 px-1.5 rounded-full text-[10px] font-semibold flex items-center justify-center"
              style={{
                background: "var(--green-600)",
                color: "white",
              }}
              aria-label={`${unreadCount} unread`}
            >
              {unreadCount > 99 ? "99+" : unreadCount}
            </span>
          ) : null}
        </button>
      </div>

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
  unreadCount = 0,
}: {
  displayName: string;
  open: boolean;
  onToggle: () => void;
  unreadCount?: number;
}) {
  return (
    <button
      type="button"
      onClick={onToggle}
      className="relative flex items-center gap-2 rounded-lg py-1 pl-1 pr-2 hover:bg-[var(--bg-2)] transition-colors"
      aria-expanded={open}
      aria-haspopup="menu"
      aria-label={
        unreadCount > 0
          ? `${displayName} account menu, ${unreadCount} unread notifications`
          : `${displayName} account menu`
      }
    >
      <Avatar name={displayName} size={36} />
      {unreadCount > 0 ? (
        <span
          className="absolute top-0 left-7 min-w-[1.125rem] h-[1.125rem] px-0.5 rounded-full text-[9px] font-bold flex items-center justify-center leading-none"
          style={{ background: "var(--green-600)", color: "white" }}
          aria-hidden
        >
          {unreadCount > 99 ? "99+" : unreadCount}
        </span>
      ) : null}
      <Icon name="chevronDown" size={14} />
    </button>
  );
}
