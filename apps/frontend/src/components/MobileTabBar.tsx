"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Icon } from "@/components/ui/Icon";
import { useAuth } from "@/lib/auth";
import { profile as profileApi, subscription as subscriptionApi } from "@/lib/api";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { settingsPath } from "@/app/settings/settings-nav";
import { useTheme } from "@/components/ThemeProvider";
import { formatTierNavSubtitle } from "@/lib/tier-display";
import { showMobileAppShell } from "@/lib/mobile-nav";

const MAIN_TABS = [
  { id: "jobs", label: "Jobs", shortLabel: "Jobs", icon: "briefcase", href: "/jobs" },
  { id: "matches", label: "Matches", shortLabel: "Matches", icon: "sparkle", href: "/matches" },
  {
    id: "applications",
    label: "Applications",
    shortLabel: "Apps",
    icon: "sliders",
    href: "/applications",
  },
  { id: "profile", label: "Profile", shortLabel: "Profile", icon: "user", href: "/profile" },
] as const;

type MoreLink = {
  href: string;
  label: string;
  icon: string;
  authOnly?: boolean;
  adminOnly?: boolean;
};

const MORE_LINKS: MoreLink[] = [
  { href: "/dashboard", label: "Dashboard", icon: "home" },
  { href: "/profile", label: "Profile & CV", icon: "user" },
  { href: settingsPath("notifications"), label: "Notifications", icon: "bell" },
  { href: settingsPath("billing"), label: "Billing & invoices", icon: "file" },
  { href: settingsPath("account"), label: "Settings", icon: "settings" },
  { href: "/pricing", label: "Pricing", icon: "star" },
  { href: "/admin", label: "Admin", icon: "shield", adminOnly: true },
];

export function MobileTabBar() {
  const pathname = usePathname();
  const router = useRouter();
  const { logout, isAuthenticated, token } = useAuth();
  const { dark, toggle } = useTheme();
  const [moreOpen, setMoreOpen] = useState(false);
  const [tierSubtitle, setTierSubtitle] = useState("");
  const [showAdmin, setShowAdmin] = useState(false);

  const shouldShow = showMobileAppShell(pathname, isAuthenticated);

  useEffect(() => {
    if (!token) {
      setTierSubtitle("");
      setShowAdmin(false);
      return;
    }
    Promise.all([
      profileApi.get(token),
      subscriptionApi.get(token).catch(() => null),
    ])
      .then(([profile, sub]) => {
        setTierSubtitle(
          formatTierNavSubtitle(
            profile.subscription_tier,
            sub?.matches_used,
            sub?.matches_limit,
          ),
        );
        setShowAdmin(profile.role === "admin" || profile.role === "superadmin");
      })
      .catch(() => {
        setTierSubtitle("");
        setShowAdmin(false);
      });
  }, [token]);

  if (!shouldShow) return null;

  const mainActiveIndex = MAIN_TABS.findIndex((t) => pathname.startsWith(t.href));
  const moreActive =
    MORE_LINKS.some((l) => pathname.startsWith(l.href)) ||
    pathname.startsWith("/settings");
  const indicatorIndex = moreActive ? MAIN_TABS.length : Math.max(mainActiveIndex, 0);

  const visibleMoreLinks = MORE_LINKS.filter((link) => {
    if (link.adminOnly && !showAdmin) return false;
    return true;
  });

  return (
    <>
      <nav className="mobile-tab-bar" aria-label="Mobile navigation">
        <div
          className="tab-indicator"
          style={{
            transform: `translateX(calc(${indicatorIndex} * (100% + 4px)))`,
          }}
        />

        {MAIN_TABS.map((tab) => {
          const isActive = pathname.startsWith(tab.href);
          return (
            <button
              key={tab.id}
              type="button"
              className={`tab-btn ${isActive ? "active" : ""}`}
              onClick={() => {
                hapticTap();
                router.push(tab.href);
              }}
              aria-label={tab.label}
              aria-current={isActive ? "page" : undefined}
            >
              <span className="tab-icon-wrap">
                <Icon name={tab.icon} size={17} />
              </span>
              <span className="tab-label">{tab.shortLabel}</span>
            </button>
          );
        })}

        <button
          type="button"
          className={`tab-btn ${moreActive ? "active" : ""}`}
          onClick={() => {
            hapticTap();
            setMoreOpen(true);
          }}
          aria-label="More"
          aria-expanded={moreOpen}
          aria-haspopup="dialog"
        >
          <span className="tab-icon-wrap">
            <Icon name="menu" size={17} />
          </span>
          <span className="tab-label">More</span>
        </button>
      </nav>

      <Sheet open={moreOpen} onOpenChange={setMoreOpen}>
        <SheetContent side="bottom" className="rounded-t-2xl pb-8 native-sheet-bottom">
          <SheetHandle />
          <SheetHeader>
            <SheetTitle>More</SheetTitle>
            {tierSubtitle ? (
              <p className="text-xs text-left" style={{ color: "var(--muted)" }}>
                {tierSubtitle}
              </p>
            ) : null}
          </SheetHeader>
          <nav className="flex flex-col gap-1 px-2" aria-label="More navigation">
            {visibleMoreLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setMoreOpen(false)}
                className="flex items-center gap-3 rounded-lg px-3 py-3 text-sm font-medium hover:bg-muted/50"
              >
                <Icon name={link.icon} size={18} className="opacity-80" />
                {link.label}
              </Link>
            ))}
            <button
              type="button"
              onClick={() => {
                toggle();
              }}
              className="flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left text-sm font-medium hover:bg-muted/50"
            >
              <Icon name={dark ? "sun" : "moon"} size={18} className="opacity-80" />
              {dark ? "Light mode" : "Dark mode"}
            </button>
            <button
              type="button"
              onClick={() => {
                setMoreOpen(false);
                logout();
              }}
              className="flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left text-sm font-medium hover:bg-muted/50"
              style={{ color: "var(--danger)" }}
            >
              <Icon name="arrowLeft" size={18} className="opacity-80" />
              Sign out
            </button>
          </nav>
        </SheetContent>
      </Sheet>

      <div className="mobile-tab-spacer" />

      <style jsx>{`
        .mobile-tab-bar {
          display: none;
        }

        @media (max-width: 767px) {
          .mobile-tab-bar {
            position: fixed;
            left: 10px;
            right: 10px;
            bottom: calc(8px + env(safe-area-inset-bottom, 0px));
            background: rgba(26, 26, 24, 0.92);
            backdrop-filter: saturate(180%) blur(24px);
            -webkit-backdrop-filter: saturate(180%) blur(24px);
            border: 1px solid rgba(26, 26, 24, 0.95);
            border-radius: 999px;
            display: flex;
            gap: 4px;
            padding: 5px;
            z-index: 50;
            box-shadow: 0 12px 36px rgba(0, 0, 0, 0.25),
              0 1px 2px rgba(0, 0, 0, 0.2),
              inset 0 1px 0 rgba(255, 255, 255, 0.08);
            animation: tabBarIn 540ms cubic-bezier(0.2, 0.7, 0.2, 1) 200ms both;
          }

          .mobile-tab-spacer {
            display: block;
            height: calc(80px + env(safe-area-inset-bottom, 0px));
          }
        }

        @keyframes tabBarIn {
          from {
            transform: translateY(20px);
            opacity: 0;
          }
          to {
            transform: translateY(0);
            opacity: 1;
          }
        }

        .tab-indicator {
          position: absolute;
          top: 5px;
          bottom: 5px;
          width: calc((100% - 10px - 16px) / 5);
          background: linear-gradient(135deg, #d27a3f 0%, #a86224 100%);
          border-radius: 999px;
          transition: transform 480ms cubic-bezier(0.34, 1.4, 0.5, 1);
          box-shadow: 0 4px 12px rgba(201, 122, 48, 0.4),
            inset 0 1px 0 rgba(255, 255, 255, 0.2);
          z-index: 0;
        }

        .tab-btn {
          flex: 1 1 0;
          min-width: 0;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          gap: 1px;
          background: transparent;
          border: none;
          cursor: pointer;
          padding: 6px 2px;
          color: rgba(255, 255, 255, 0.55);
          transition: color 260ms ease, transform 200ms ease;
          position: relative;
          z-index: 1;
          font-family: inherit;
        }

        .tab-icon-wrap {
          display: flex;
          align-items: center;
          justify-content: center;
          width: 24px;
          height: 24px;
        }

        .tab-btn.active {
          color: #fff;
        }

        .tab-btn:active {
          transform: scale(0.94);
        }

        .tab-label {
          font-size: 9px;
          font-weight: 600;
          letter-spacing: 0.01em;
          line-height: 1.1;
          max-width: 100%;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          text-align: center;
        }

        @media (prefers-reduced-motion: reduce) {
          .mobile-tab-bar {
            animation: none;
          }
          .tab-indicator {
            transition: none;
          }
        }
      `}</style>
    </>
  );
}
