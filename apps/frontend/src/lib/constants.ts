const rawSite =
  (typeof process !== "undefined" && process.env.NEXT_PUBLIC_SITE_URL) || "https://www.zedapply.com";

export const SITE_URL = rawSite.replace(/\/$/, "");

export const ZAMBIAN_CITIES = [
  "Lusaka",
  "Kitwe",
  "Ndola",
  "Livingstone",
  "Kabwe",
  "Chipata",
  "Solwezi",
  "Kasama",
  "Mansa",
  "Mongu",
  "Chingola",
  "Mufulira",
  "Choma",
  "Remote",
] as const;

export const FEATURE_JOBS: string[] = ["All types", "Full-time", "Part-time", "Contract", "Graduate", "Remote"];

export const TIER_INFO = {
  free: { name: "Free", bemba: "Get Started", priceLabel: "K0", sub: "Forever" },
  starter: { name: "Starter", bemba: "Most Popular", priceLabel: "K125", sub: "Monthly" },
  professional: { name: "Professional", bemba: "Best Value", priceLabel: "K250", sub: "Monthly" },
} as const;
