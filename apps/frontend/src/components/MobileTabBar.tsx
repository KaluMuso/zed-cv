"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Icon } from "@/components/ui/Icon";
import { useAuth } from "@/lib/auth";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { settingsPath } from "@/app/settings/settings-nav";

const MAIN_TABS = [
  { id: "jobs", label: "Jobs", icon: "briefcase", href: "/jobs" },
  { id: "matches", label: "Matches", icon: "sparkle", href: "/matches" },
  { id: "applications", label: "Applications", icon: "briefcase", href: "/applications" },
  { id: "profile", label: "Profile", icon: "user", href: "/profile" },
] as const;

const MORE_LINKS = [
  { href: "/dashboard", label: "Dashboard", icon: "home" },
  { href: settingsPath("account"), label: "Settings", icon: "settings" },
  { href: "/pricing", label: "Pricing", icon: "star" },
  { href: "/interview-prep", label: "Interview Prep", icon: "target" },
] as const;

/**
 * Mobile bottom tab bar — pill-style with sliding copper indicator.
 * Only visible on screens < 768px. Hidden on desktop.
 */
export function MobileTabBar() {
  const pathname = usePathname();
  const router = useRouter();
  const { logout, isAuthenticated } = useAuth();
  const [moreOpen, setMoreOpen] = useState(false);

  const showOn = [
    "/matches",
    "/jobs",
    "/profile",
    "/pricing",
    "/applications",
    "/dashboard",
    "/settings",
    "/interview-prep",
  ];
  const shouldShow =
    isAuthenticated && showOn.some((p) => pathname.startsWith(p));
  if (!shouldShow) return null;

  const mainActiveIndex = MAIN_TABS.findIndex((t) => pathname.startsWith(t.href));
  const moreActive =
    MORE_LINKS.some((l) => pathname.startsWith(l.href)) ||
    pathname.startsWith("/settings");
  const indicatorIndex = moreActive ? MAIN_TABS.length : Math.max(mainActiveIndex, 0);

  return (
    <>
      <nav className="mobile-tab-bar" aria-label="Mobile navigation">
        <div
          className="tab-indicator"
          style={{
            transform: `translateX(calc(${indicatorIndex} * (100% + 6px)))`,
          }}
        />

        {MAIN_TABS.map((tab) => {
          const isActive = pathname.startsWith(tab.href);
          return (
            <button
              key={tab.id}
              type="button"
              className={`tab-btn ${isActive ? "active" : ""}`}
              onClick={() => router.push(tab.href)}
              aria-label={tab.label}
              aria-current={isActive ? "page" : undefined}
            >
              <Icon name={tab.icon} size={18} />
              <span className="tab-label">{tab.label}</span>
            </button>
          );
        })}

        <button
          type="button"
          className={`tab-btn ${moreActive ? "active" : ""}`}
          onClick={() => setMoreOpen(true)}
          aria-label="More"
          aria-expanded={moreOpen}
          aria-haspopup="dialog"
        >
          <Icon name="menu" size={18} />
          <span className="tab-label">More</span>
        </button>
      </nav>

      <Sheet open={moreOpen} onOpenChange={setMoreOpen}>
        <SheetContent side="bottom" className="rounded-t-2xl pb-8">
          <SheetHeader>
            <SheetTitle>More</SheetTitle>
          </SheetHeader>
          <nav className="flex flex-col gap-1 px-2" aria-label="More navigation">
            {MORE_LINKS.map((link) => (
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

      {shouldShow ? <div className="mobile-tab-spacer" /> : null}

      <style jsx>{`
        .mobile-tab-bar {
          display: none;
        }

        @media (max-width: 767px) {
          .mobile-tab-bar {
            position: fixed;
            left: 12px;
            right: 12px;
            bottom: calc(8px + env(safe-area-inset-bottom, 0px));
            background: rgba(26, 26, 24, 0.88);
            backdrop-filter: saturate(180%) blur(24px);
            -webkit-backdrop-filter: saturate(180%) blur(24px);
            border: 1px solid rgba(26, 26, 24, 0.95);
            border-radius: 999px;
            display: flex;
            padding: 6px;
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
          top: 6px;
          bottom: 6px;
          width: calc((100% - 12px) / 5);
          background: linear-gradient(135deg, #d27a3f 0%, #a86224 100%);
          border-radius: 999px;
          transition: transform 480ms cubic-bezier(0.34, 1.4, 0.5, 1);
          box-shadow: 0 4px 12px rgba(201, 122, 48, 0.4),
            inset 0 1px 0 rgba(255, 255, 255, 0.2);
          z-index: 0;
        }

        .tab-btn {
          flex: 1;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 2px;
          background: transparent;
          border: none;
          cursor: pointer;
          padding: 10px 4px;
          color: rgba(255, 255, 255, 0.55);
          transition: color 260ms ease, transform 200ms ease;
          position: relative;
          z-index: 1;
          font-family: inherit;
        }

        .tab-btn.active {
          color: #fff;
        }

        .tab-btn:active {
          transform: scale(0.9);
        }

        .tab-label {
          font-size: 10px;
          font-weight: 600;
          letter-spacing: 0.02em;
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
