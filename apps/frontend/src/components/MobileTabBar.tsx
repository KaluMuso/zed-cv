"use client";

import { usePathname, useRouter } from "next/navigation";
import { Icon } from "@/components/ui/Icon";

const TABS = [
  { id: "matches", label: "Matches", icon: "sparkles", href: "/matches" },
  { id: "jobs", label: "Browse", icon: "briefcase", href: "/jobs" },
  { id: "profile", label: "Profile", icon: "user", href: "/profile" },
] as const;

/**
 * Mobile bottom tab bar — pill-style with sliding copper indicator.
 * Only visible on screens < 768px. Hidden on desktop.
 * Matches the ZedApply mobile prototype design.
 */
export function MobileTabBar() {
  const pathname = usePathname();
  const router = useRouter();

  // Only show on authenticated pages
  const showOn = ["/matches", "/jobs", "/profile", "/pricing", "/applications"];
  const shouldShow = showOn.some((p) => pathname.startsWith(p));
  if (!shouldShow) return null;

  const activeIndex = TABS.findIndex((t) => pathname.startsWith(t.href));

  return (
    <>
      <nav className="mobile-tab-bar" aria-label="Mobile navigation">
        {/* Sliding indicator */}
        <div
          className="tab-indicator"
          style={{
            transform: `translateX(calc(${Math.max(activeIndex, 0)} * (100% + 6px)))`,
          }}
        />

        {TABS.map((tab) => {
          const isActive = pathname.startsWith(tab.href);
          return (
            <button
              key={tab.id}
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
      </nav>

      {/* Spacer to prevent content from hiding behind the fixed tab bar */}
      {shouldShow && <div className="mobile-tab-spacer" />}

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
          width: calc((100% - 12px) / 3);
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

        /* Hide desktop navbar on mobile when tab bar is showing */
        @media (max-width: 767px) {
          :global(.desktop-nav-hide-mobile) {
            display: none !important;
          }
        }

        /* Respect reduced motion */
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
