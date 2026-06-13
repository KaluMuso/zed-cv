export type AdminSection =
  | "overview"
  | "jobs"
  | "users"
  | "subscriptions"
  | "matches"
  | "notifications"
  | "tier-config"
  | "bwana"
  | "faqs"
  | "legal"
  | "scrape-targets"
  | "referrals";

export const ADMIN_NAV: {
  slug: AdminSection;
  label: string;
  description: string;
  href: string;
}[] = [
  {
    slug: "overview",
    label: "Overview",
    description: "Platform health, exports, and LLM costs",
    href: "/admin/overview",
  },
  {
    slug: "jobs",
    label: "Jobs",
    description: "List, create, and deactivate job postings",
    href: "/admin/jobs",
  },
  {
    slug: "users",
    label: "Users",
    description: "Search users and override subscription tiers",
    href: "/admin/users",
  },
  {
    slug: "subscriptions",
    label: "Subscriptions",
    description: "MRR, churn, and recent payments",
    href: "/admin/subscriptions",
  },
  {
    slug: "matches",
    label: "Matches",
    description: "Recent match scores across users",
    href: "/admin/matches",
  },
  {
    slug: "notifications",
    label: "Notifications",
    description: "Compose and send broadcast Web Push alerts",
    href: "/admin/notifications",
  },
  {
    slug: "tier-config",
    label: "Tier config",
    description: "Pricing and match limits per plan",
    href: "/admin/tier-config",
  },
  {
    slug: "bwana",
    label: "Bwana",
    description: "Chatbot analytics, transcripts, config, and knowledge",
    href: "/admin/bwana",
  },
  {
    slug: "faqs",
    label: "FAQs",
    description: "Manage frequently asked questions",
    href: "/admin/faqs",
  },
  {
    slug: "legal",
    label: "Legal",
    description: "Edit privacy, terms, cookies, and refund pages",
    href: "/admin/legal",
  },
  {
    slug: "scrape-targets",
    label: "Scrape Targets",
    description: "Manage dynamic scraping targets",
    href: "/admin/scrape-targets",
  },
  {
    slug: "referrals",
    label: "Referrals",
    description: "Manage referral rewards, payouts, and milestones",
    href: "/admin/referrals",
  },
];

/** Resolve nav item from pathname (supports nested routes like /admin/jobs/review). */
export function adminSectionFromPath(pathname: string): AdminSection {
  const segment = pathname.replace(/^\/admin\/?/, "").split("/")[0];
  const found = ADMIN_NAV.find((n) => n.slug === segment);
  return found?.slug ?? "overview";
}
