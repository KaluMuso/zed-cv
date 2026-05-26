"use client";

import Link from "next/link";
import { Logo } from "@/components/ui/Logo";

const columns = [
  {
    title: "Product",
    links: [
      { label: "Job Matching", href: "/jobs" },
      { label: "CV Analysis", href: "/profile" },
      { label: "Pricing", href: "/pricing" },
      { label: "WhatsApp Alerts", href: "/auth" },
    ],
  },
  {
    title: "Company",
    links: [
      { label: "About", href: "/about" },
      // TODO: re-add Blog, Careers, Contact once those pages exist.
      // Removed 2026-05-10 — links pointed at /blog /careers /contact
      // which have no page.tsx, generating 404s on Next.js prefetch.
    ],
  },
  {
    title: "Legal",
    links: [
      { label: "Terms of Service", href: "/legal/terms" },
      { label: "Privacy Policy", href: "/legal/privacy" },
      { label: "Refund Policy", href: "/legal/refund" },
      { label: "Cookie Policy", href: "/legal/cookies" },
    ],
  },
];

export function Footer() {
  return (
    <footer style={{ borderTop: "1px solid var(--line)" }}>
      <div className="chevron-strip" />
      <div className="max-w-[1280px] mx-auto px-6 py-12 md:py-16">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-10 md:gap-8">
          {/* Brand column */}
          <div>
            <Logo size={24} />
            <p
              className="mt-4 text-sm leading-relaxed"
              style={{ color: "var(--muted)", maxWidth: 260 }}
            >
              AI-powered job matching for Zambian professionals. Upload your CV,
              get scored matches, receive alerts on WhatsApp.
            </p>
            <div
              className="mt-4 inline-flex items-center gap-2 text-xs font-mono px-3 py-1.5 rounded-full"
              style={{
                background: "var(--green-100)",
                color: "var(--green-700)",
              }}
            >
              <span
                className="w-2 h-2 rounded-full animate-pulse"
                style={{ background: "var(--green-500)" }}
              />
              Built in Zambia
            </div>
          </div>

          {/* Link columns */}
          {columns.map((col) => (
            <div key={col.title}>
              <p
                className="eyebrow mb-4 m-0"
                style={{ color: "var(--muted)" }}
              >
                {col.title}
              </p>
              <ul className="space-y-2.5">
                {col.links.map((link) => (
                  <li key={link.label}>
                    <Link
                      href={link.href}
                      className="text-sm transition-colors hover:underline"
                      style={{ color: "var(--ink-2)" }}
                    >
                      {link.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom bar */}
        <div
          className="mt-12 pt-6 flex flex-col sm:flex-row items-center justify-between gap-3"
          style={{ borderTop: "1px solid var(--line)" }}
        >
          <p
            className="text-xs font-mono"
            style={{ color: "var(--muted)" }}
          >
            ZED APPLY &middot; VERGEO &middot; LUSAKA &middot; 2026
          </p>
          <p
            className="text-xs"
            style={{ color: "var(--muted-2)" }}
          >
            convergeozambia@gmail.com
          </p>
        </div>
      </div>
    </footer>
  );
}
