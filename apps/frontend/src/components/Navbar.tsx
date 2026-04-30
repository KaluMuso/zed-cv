"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { useTheme } from "@/components/ThemeProvider";
import { Logo } from "@/components/ui/Logo";
import { Icon } from "@/components/ui/Icon";
import { Avatar } from "@/components/ui/Avatar";

export function Navbar() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const { isAuthenticated, logout, user } = useAuth();
  const { dark, toggle } = useTheme();
  const pathname = usePathname();

  useEffect(() => {
    const handleScroll = () => setScrolled(window.scrollY > 10);
    window.addEventListener("scroll", handleScroll, { passive: true });
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  // Close menu on route change
  useEffect(() => {
    setMenuOpen(false);
    setDropdownOpen(false);
  }, [pathname]);

  const navLinks = [
    { href: "/jobs", label: "Jobs" },
    { href: "/matches", label: "Matches" },
    { href: "/pricing", label: "Pricing" },
  ];

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

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-8">
            {navLinks.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={`nav-link ${pathname === link.href ? "active" : ""}`}
              >
                {link.label}
              </Link>
            ))}
          </div>

          <div className="hidden md:flex items-center gap-3">
            {/* Theme toggle */}
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
                <button
                  onClick={() => setDropdownOpen(!dropdownOpen)}
                  className="flex items-center gap-2"
                >
                  <Avatar name={user?.id?.slice(0, 4) || "ZC"} size={32} />
                  <Icon name="chevronDown" size={14} />
                </button>
                {dropdownOpen && (
                  <>
                    <div
                      className="fixed inset-0 z-40"
                      onClick={() => setDropdownOpen(false)}
                    />
                    <div
                      className="absolute right-0 top-full mt-2 w-48 py-2 rounded-xl z-50"
                      style={{
                        background: "var(--surface)",
                        border: "1px solid var(--line)",
                        boxShadow: "var(--shadow-lg)",
                      }}
                    >
                      <Link
                        href="/profile"
                        className="block px-4 py-2 text-sm hover:bg-[var(--bg-2)] transition-colors"
                        style={{ color: "var(--ink-2)" }}
                      >
                        Profile
                      </Link>
                      <Link
                        href="/matches"
                        className="block px-4 py-2 text-sm hover:bg-[var(--bg-2)] transition-colors"
                        style={{ color: "var(--ink-2)" }}
                      >
                        My Matches
                      </Link>
                      <hr style={{ borderColor: "var(--line)" }} className="my-1" />
                      <button
                        onClick={logout}
                        className="block w-full text-left px-4 py-2 text-sm hover:bg-[var(--bg-2)] transition-colors"
                        style={{ color: "var(--danger)" }}
                      >
                        Sign Out
                      </button>
                    </div>
                  </>
                )}
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <Link href="/auth" className="btn btn-ghost btn-sm">
                  Sign In
                </Link>
                <Link href="/auth" className="btn btn-primary btn-sm">
                  Get Started
                </Link>
              </div>
            )}
          </div>

          {/* Mobile hamburger */}
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            className="md:hidden touch-target flex items-center justify-center"
            aria-label="Toggle menu"
            style={{ color: "var(--ink)" }}
          >
            <Icon name={menuOpen ? "x" : "menu"} size={24} />
          </button>
        </div>

        {/* Mobile menu */}
        {menuOpen && (
          <div
            className="md:hidden fixed inset-0 top-[70px] z-40"
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
                      pathname === link.href
                        ? "var(--green-700)"
                        : "var(--ink)",
                    borderBottom: "1px solid var(--line)",
                  }}
                >
                  {link.label}
                </Link>
              ))}

              <div className="mt-6 flex flex-col gap-3">
                <button
                  onClick={toggle}
                  className="btn btn-ghost w-full"
                >
                  <Icon name={dark ? "sun" : "moon"} size={16} />
                  {dark ? "Light Mode" : "Dark Mode"}
                </button>

                {isAuthenticated ? (
                  <>
                    <Link
                      href="/profile"
                      onClick={() => setMenuOpen(false)}
                      className="btn btn-ghost w-full"
                    >
                      Profile
                    </Link>
                    <button
                      onClick={() => {
                        logout();
                        setMenuOpen(false);
                      }}
                      className="btn btn-ghost w-full"
                      style={{ color: "var(--danger)" }}
                    >
                      Sign Out
                    </button>
                  </>
                ) : (
                  <Link
                    href="/auth"
                    onClick={() => setMenuOpen(false)}
                    className="btn btn-primary w-full"
                  >
                    Get Started
                  </Link>
                )}
              </div>
            </div>
          </div>
        )}
      </nav>
    </>
  );
}
