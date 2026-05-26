"use client";

import Link from "next/link";
import { Icon } from "@/components/ui/Icon";
import { Avatar } from "@/components/ui/Avatar";
import { formatTierNavSubtitle } from "@/lib/tier-display";

type MenuItem = {
  href: string;
  label: string;
  icon: string;
  onClick?: () => void;
};

export function UserMenuDropdown({
  displayName,
  tierSubtitle,
  onClose,
  onSignOut,
  showAdmin,
}: {
  displayName: string;
  tierSubtitle: string;
  onClose: () => void;
  onSignOut: () => void;
  showAdmin?: boolean;
}) {
  const items: MenuItem[] = [
    { href: "/dashboard", label: "Dashboard", icon: "home" },
    { href: "/profile", label: "Profile", icon: "user" },
    { href: "/profile?tab=cv-generator", label: "CV Generator", icon: "file" },
    { href: "/matches", label: "My matches", icon: "sparkle" },
    { href: "/settings/notifications", label: "Notifications", icon: "bell" },
    { href: "/settings/account", label: "Account settings", icon: "settings" },
    { href: "/settings/privacy", label: "Privacy & data", icon: "shield" },
  ];

  if (showAdmin) {
    items.push({ href: "/admin", label: "Admin (internal)", icon: "shield" });
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
      className="flex items-center gap-2 rounded-lg py-1 pl-1 pr-2 hover:bg-[var(--bg-2)] transition-colors"
      aria-expanded={open}
      aria-haspopup="menu"
    >
      <Avatar name={displayName} size={36} />
      <Icon name="chevronDown" size={14} />
    </button>
  );
}
