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
import { cn } from "@/lib/utils";

type NavProfile = {
  fullName: string;
  tierSubtitle: string;
  showAdmin: boolean;
};

export function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const { isAuthenticated, logout, token } = useAuth();
  const [navProfile, setNavProfile] = useState<NavProfile | null>(null);
  const [subscriptionTier, setSubscriptionTier] = useState<string | null>(null);
  const { dark, toggle } = useTheme();
  const pathname = usePathname();

  const interviewPrepSubLinks =
    subscriptionTier === "super_standard"
      ? [
          { href: "/interview-prep/mock", label: "Mock Interview" },
          { href: "/interview-prep/aptitude", label: "Aptitude Tests" },
          { href: "/interview-prep/history", label: "History" },
        ]
      : [];

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
          showAdmin: profile.role === "admin" || profile.role === "superadmin",
        });
      })
      .catch(() => {
        setNavProfile(null);
        setSubscriptionTier(null);
      });
  }, [token]);

  const navLinks = [
    { href: "/jobs", label: "Jobs" },
    { href: "/matches", label: "Matches" },
    { href: "/pricing", label: "Pricing" },
  ];

  const displayName = navProfile?.fullName ?? "Account";

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
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`nav-link ${pathname === link.href || pathname.startsWith(`${link.href}/`) ? "active" : ""}`}
              >
                {link.label}
              </Link>
            ))}
            {isAuthenticated ? (
              <Link
                href="/dashboard"
                className={`nav-link ${pathname === "/dashboard" ? "active" : ""}`}
              >
                Dashboard
              </Link>
            ) : null}
            {interviewPrepSubLinks.length > 0 && (
              <div className="relative group">
                <Link
                  href="/interview-prep"
                  className={`nav-link ${
                    pathname.startsWith("/interview-prep") ? "active" : ""
                  }`}
                >
                  Interview Prep
                </Link>
                <div
                  className="absolute left-0 top-full pt-2 hidden group-hover:block z-50"
                  role="menu"
                >
                  <div
                    className="min-w-[180px] py-2 rounded-xl"
                    style={{
                      background: "var(--surface)",
                      border: "1px solid var(--line)",
                      boxShadow: "var(--shadow-lg)",
                    }}
                  >
                    {interviewPrepSubLinks.map((link) => (
                      <Link
                        key={link.href}
                        href={link.href}
                        className="block px-4 py-2 text-sm hover:bg-[var(--bg-2)] transition-colors"
                        style={{ color: "var(--ink-2)" }}
                      >
                        {link.label}
                      </Link>
                    ))}
                  </div>
                </div>
              </div>
            )}
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
                {dropdownOpen && (
                  <>
                    <div
                      className="fixed inset-0 z-40"
                      onClick={() => setDropdownOpen(false)}
                      aria-hidden
                    />
                    <UserMenuDropdown
                      displayName={displayName}
                      tierSubtitle={navProfile?.tierSubtitle ?? ""}
                      showAdmin={navProfile?.showAdmin}
                      onClose={() => setDropdownOpen(false)}
                      onSignOut={logout}
                    />
                  </>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link
                  href="/auth"
                  className={cn(buttonVariants({ variant: "ghost", size: "sm" }))}
                  title="Returning user? Sign in with your phone number"
                >
                  Log in
                </Link>
                <Link
                  href="/auth?next=/matches"
                  className={cn(buttonVariants({ variant: "primary", size: "sm" }))}
                  title="New here? Create your account in under a minute"
                >
                  Get started
                  <Icon name="arrowRight" size={14} className="ml-1 inline" />
                </Link>
              </div>
            )}
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

        {menuOpen && (
          <div
            className="md:hidden fixed inset-0 top-[70px] z-40 overflow-y-auto"
            style={{ background: "var(--surface)" }}
          >
            <div className="flex flex-col p-6 gap-2">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMenuOpen(false)}
                  className="font-display text-3xl py-3 transition-colors"
                  style={{
                    color:
                      pathname === link.href ? "var(--green-700)" : "var(--ink)",
                    borderBottom: "1px solid var(--line)",
                  }}
                >
                  {link.label}
                </Link>
              ))}
              {interviewPrepSubLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  onClick={() => setMenuOpen(false)}
                  className="font-display text-2xl py-2 transition-colors pl-4"
                  style={{
                    color: pathname === link.href ? "var(--green-700)" : "var(--ink-2)",
                    borderBottom: "1px solid var(--line)",
                  }}
                >
                  {link.label}
                </Link>
              ))}

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
                    <Link
                      href="/profile"
                      onClick={() => setMenuOpen(false)}
                      className={cn(buttonVariants({ variant: "ghost" }), "w-full justify-start gap-2")}
                    >
                      <Icon name="user" size={16} /> Profile
                    </Link>
                    <Link
                      href="/settings/notifications"
                      onClick={() => setMenuOpen(false)}
                      className={cn(buttonVariants({ variant: "ghost" }), "w-full justify-start gap-2")}
                    >
                      <Icon name="bell" size={16} /> Notifications
                    </Link>
                    <Link
                      href="/settings/account"
                      onClick={() => setMenuOpen(false)}
                      className={cn(buttonVariants({ variant: "ghost" }), "w-full justify-start gap-2")}
                    >
                      <Icon name="settings" size={16} /> Account settings
                    </Link>
                    <Link
                      href="/settings/privacy"
                      onClick={() => setMenuOpen(false)}
                      className={cn(buttonVariants({ variant: "ghost" }), "w-full justify-start gap-2")}
                    >
                      <Icon name="shield" size={16} /> Privacy &amp; data
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
                ) : (
                  <>
                    <Link
                      href="/auth"
                      onClick={() => setMenuOpen(false)}
                      className={cn(buttonVariants({ variant: "ghost" }), "w-full")}
                    >
                      Log in
                    </Link>
                    <Link
                      href="/auth?next=/matches"
                      onClick={() => setMenuOpen(false)}
                      className={cn(buttonVariants({ variant: "primary" }), "w-full justify-center gap-2")}
                    >
                      Get started
                      <Icon name="arrowRight" size={16} />
                    </Link>
                  </>
                )}
              </div>
            </div>
          </div>
        )}
      </nav>
    </>
  );
}
