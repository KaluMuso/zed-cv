"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { profile as profileApi, subscription as subscriptionApi } from "@/lib/api";
import { useTheme } from "@/components/ThemeProvider";
import { Logo } from "@/components/ui/Logo";
import { Icon } from "@/components/ui/Icon";
import { buttonVariants } from "@/components/ui/button";
import { UserMenuDropdown, UserMenuTrigger } from "@/components/nav/UserMenuDropdown";
import { formatTierNavSubtitle } from "@/lib/tier-display";
import { AUTH_GET_STARTED } from "@/lib/auth-paths";
import { InterviewPrepNav } from "@/components/nav/InterviewPrepNav";
import { settingsPath } from "@/app/settings/settings-nav";
import { cn } from "@/lib/utils";

type NavProfile = {
  fullName: string;
  tierSubtitle: string;
  subscriptionTier: string;
  showAdmin: boolean;
};

type NavLink = {
  href: string;
  label: string;
  authOnly?: boolean;
  guestOnly?: boolean;
};

const SIGNED_IN_LINKS: NavLink[] = [
  { href: "/jobs", label: "Jobs" },
  { href: "/matches", label: "Matches" },
  { href: "/applications", label: "Applications", authOnly: true },
  { href: "/pricing", label: "Pricing" },
];

const SIGNED_OUT_LINKS: NavLink[] = [
  { href: "/jobs", label: "Jobs" },
  { href: "/matches", label: "Matches" },
  { href: "/pricing", label: "Pricing" },
  { href: "/auth", label: "Log in", guestOnly: true },
  { href: AUTH_GET_STARTED, label: "Get started", guestOnly: true },
];

export function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const { isAuthenticated, logout, token } = useAuth();
  const [navProfile, setNavProfile] = useState<NavProfile | null>(null);
  const [subscriptionTier, setSubscriptionTier] = useState<string | null>(null);
  const { dark, toggle } = useTheme();
  const pathname = usePathname();

  const showInterviewPrep = isAuthenticated;

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    setMenuOpen(false);
    setDropdownOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!token) {
      setNavProfile(null);
      setSubscriptionTier(null);
      return;
    }
    Promise.all([
      profileApi.get(token),
      subscriptionApi.get(token).catch(() => null),
    ])
      .then(([profile, sub]) => {
        const fullName =
          profile.full_name?.trim() ||
          profile.email?.split("@")[0] ||
          "Your account";
        const tierSubtitle = formatTierNavSubtitle(
          profile.subscription_tier,
          sub?.matches_used,
          sub?.matches_limit,
        );
        setSubscriptionTier(profile.subscription_tier);
        setNavProfile({
          fullName,
          tierSubtitle,
          subscriptionTier: profile.subscription_tier,
          showAdmin: profile.role === "admin" || profile.role === "superadmin",
        });
      })
      .catch(() => {
        setNavProfile(null);
        setSubscriptionTier(null);
      });
  }, [token]);

  const navLinks = isAuthenticated ? SIGNED_IN_LINKS : SIGNED_OUT_LINKS;
  const visibleNavLinks = navLinks.filter((link) => {
    if (link.authOnly && !isAuthenticated) return false;
    if (link.guestOnly && isAuthenticated) return false;
    return true;
  });

  const displayName = navProfile?.fullName ?? "Account";

  const linkActive = (href: string) =>
    pathname === href || pathname.startsWith(`${href}/`);

  return (
    <>
      <div className="chevron-strip" />
      <nav
        className="sticky top-0 z-50 transition-all duration-200"
        style={{
          background: scrolled
            ? "color-mix(in srgb, var(--surface) 85%, transparent)"
            : "var(--surface)",
          backdropFilter: scrolled ? "blur(16px) saturate(180%)" : "none",
          borderBottom: "1px solid var(--line)",
        }}
      >
        <div className="max-w-[1280px] mx-auto px-6 h-[64px] flex items-center justify-between">
          <Link href="/" className="shrink-0">
            <Logo size={28} />
          </Link>

          <div className="hidden md:flex items-center gap-8">
            {visibleNavLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`nav-link ${linkActive(link.href) ? "active" : ""}`}
              >
                {link.label}
              </Link>
            ))}
            {showInterviewPrep ? (
              <InterviewPrepNav subscriptionTier={subscriptionTier} />
            ) : null}
          </div>

          <div className="hidden md:flex items-center gap-3">
            <button
              onClick={toggle}
              className="w-9 h-9 rounded-lg flex items-center justify-center transition-colors"
              style={{
                border: "1px solid var(--line-2)",
                color: "var(--muted)",
              }}
              aria-label="Toggle theme"
            >
              <Icon name={dark ? "sun" : "moon"} size={16} />
            </button>

            {isAuthenticated ? (
              <div className="relative">
                <UserMenuTrigger
                  displayName={displayName}
                  open={dropdownOpen}
                  onToggle={() => setDropdownOpen(!dropdownOpen)}
                />
                {dropdownOpen ? (
                  <>
                    <div
                      className="fixed inset-0 z-40"
                      onClick={() => setDropdownOpen(false)}
                      aria-hidden
                    />
                    <UserMenuDropdown
                      displayName={displayName}
                      tierSubtitle={navProfile?.tierSubtitle ?? ""}
                      subscriptionTier={navProfile?.subscriptionTier ?? subscriptionTier}
                      showAdmin={navProfile?.showAdmin}
                      onClose={() => setDropdownOpen(false)}
                      onSignOut={logout}
                    />
                  </>
                ) : null}
              </div>
            ) : null}
          </div>

          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="md:hidden touch-target flex items-center justify-center"
            aria-label="Toggle menu"
            style={{ color: "var(--ink)" }}
          >
            <Icon name={menuOpen ? "x" : "menu"} size={24} />
          </button>
        </div>

        {menuOpen ? (
          <div
            className="md:hidden fixed inset-0 top-[70px] z-40 overflow-y-auto"
            style={{ background: "var(--surface)" }}
          >
            <div className="flex flex-col p-6 gap-2">
              {visibleNavLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMenuOpen(false)}
                  className="font-display text-3xl py-3 transition-colors"
                  style={{
                    color: linkActive(link.href) ? "var(--green-700)" : "var(--ink)",
                    borderBottom: "1px solid var(--line)",
                  }}
                >
                  {link.label}
                </Link>
              ))}
              {showInterviewPrep ? (
                <InterviewPrepNav
                  variant="stacked"
                  subscriptionTier={subscriptionTier}
                  onNavigate={() => setMenuOpen(false)}
                />
              ) : null}

              <div className="mt-6 flex flex-col gap-3">
                <button
                  type="button"
                  onClick={toggle}
                  className={cn(buttonVariants({ variant: "ghost" }), "w-full justify-center gap-2")}
                >
                  <Icon name={dark ? "sun" : "moon"} size={16} />
                  {dark ? "Light Mode" : "Dark Mode"}
                </button>

                {isAuthenticated ? (
                  <>
                    {navProfile ? (
                      <div
                        className="px-3 py-3 rounded-xl mb-1"
                        style={{ background: "var(--bg-2)", border: "1px solid var(--line)" }}
                      >
                        <div className="font-semibold">{navProfile.fullName}</div>
                        <div className="text-sm" style={{ color: "var(--muted)" }}>
                          {navProfile.tierSubtitle}
                        </div>
                      </div>
                    ) : null}
                    <Link
                      href="/dashboard"
                      onClick={() => setMenuOpen(false)}
                      className={cn(buttonVariants({ variant: "ghost" }), "w-full justify-start gap-2")}
                    >
                      <Icon name="home" size={16} /> Dashboard
                    </Link>
                    <div
                      className="px-3 py-2 rounded-xl"
                      style={{ background: "var(--bg-2)", border: "1px solid var(--line)" }}
                    >
                      <div
                        className="text-[10px] font-semibold uppercase tracking-wider mb-1"
                        style={{ color: "var(--muted)" }}
                      >
                        Notifications
                      </div>
                      <p className="text-[11px] mb-2" style={{ color: "var(--muted)" }}>
                        Web push is a browser permission, not an in-app notification feed.
                      </p>
                      <div className="flex flex-col gap-1">
                        <Link
                          href="/matches"
                          onClick={() => setMenuOpen(false)}
                          className={cn(
                            buttonVariants({ variant: "ghost" }),
                            "w-full justify-start gap-2 h-9",
                          )}
                        >
                          <Icon name="sparkle" size={16} /> Match digests
                        </Link>
                        <Link
                          href="/settings/notifications"
                          onClick={() => setMenuOpen(false)}
                          className={cn(
                            buttonVariants({ variant: "ghost" }),
                            "w-full justify-start gap-2 h-9",
                          )}
                        >
                          <Icon name="bell" size={16} /> Channel preferences
                        </Link>
                        <Link
                          href="/settings/billing"
                          onClick={() => setMenuOpen(false)}
                          className={cn(
                            buttonVariants({ variant: "ghost" }),
                            "w-full justify-start gap-2 h-9",
                          )}
                        >
                          <Icon name="file" size={16} /> Invoices & billing
                        </Link>
                      </div>
                    </div>
                    <Link
                      href={settingsPath("account")}
                      onClick={() => setMenuOpen(false)}
                      className={cn(buttonVariants({ variant: "ghost" }), "w-full justify-start gap-2")}
                    >
                      <Icon name="settings" size={16} /> Settings
                    </Link>
                    <button
                      type="button"
                      onClick={() => {
                        logout();
                        setMenuOpen(false);
                      }}
                      className={cn(buttonVariants({ variant: "ghost" }), "w-full")}
                      style={{ color: "var(--danger)" }}
                    >
                      Sign out
                    </button>
                  </>
                ) : null}
              </div>
            </div>
          </div>
        ) : null}
      </nav>
    </>
  );
}
