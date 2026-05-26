import type { Metadata } from "next";
import { pageMetadata } from "@/lib/site-metadata";

export const metadata: Metadata = pageMetadata({
  title: "Settings",
  description: "Notification preferences, auto-matching, and account options for Zed Apply.",
});

export default function SettingsLayout({ children }: { children: React.ReactNode }) {
  return children;
}
