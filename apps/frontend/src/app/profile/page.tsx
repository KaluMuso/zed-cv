import type { Metadata } from "next";
import { Suspense } from "react";
import { pageMetadata } from "@/lib/site-metadata";
import ProfilePageClient from "./ProfilePageClient";

export const metadata: Metadata = pageMetadata({
  title: "Profile",
  description:
    "Manage your CV, skills, job preferences, and AI-generated CVs on ZedApply.",
});

export default function ProfilePage() {
  return (
    <Suspense fallback={null}>
      <ProfilePageClient />
    </Suspense>
  );
}
