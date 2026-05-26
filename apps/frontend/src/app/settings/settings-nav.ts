export type SettingsSection =
  | "account"
  | "notifications"
  | "job-preferences"
  | "billing"
  | "privacy"
  | "danger";

export const SETTINGS_NAV: {
  slug: SettingsSection;
  label: string;
  description: string;
  pageTitle: string;
}[] = [
  {
    slug: "account",
    label: "Account",
    description: "Contact details and profile basics",
    pageTitle: "Account",
  },
  {
    slug: "notifications",
    label: "Notifications",
    description: "Digests and auto-matching",
    pageTitle: "Notifications",
  },
  {
    slug: "job-preferences",
    label: "Job preferences",
    description: "Roles, salary, and work setup",
    pageTitle: "Job Preferences",
  },
  {
    slug: "billing",
    label: "Billing",
    description: "Plan and upgrades",
    pageTitle: "Billing",
  },
  {
    slug: "privacy",
    label: "Privacy & data",
    description: "Consent toggles, export, and policies",
    pageTitle: "Privacy & Data",
  },
  {
    slug: "danger",
    label: "Danger zone",
    description: "Pause or delete account",
    pageTitle: "Danger Zone",
  },
];

export function settingsPath(slug: SettingsSection): string {
  return `/settings/${slug}`;
}
