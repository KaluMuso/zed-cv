import type { Metadata } from "next";
import { Suspense } from "react";
import AuthPageClient from "./AuthPageClient";

export const metadata: Metadata = {
  title: "Sign In",
  description:
    "Sign in to ZedApply with your Zambian phone number — WhatsApp OTP, no password.",
};

// Server entry — exports metadata so the browser tab reads
// "Sign In | ZedApply" per the root layout's title template. The
// interactive form lives in AuthPageClient. Suspense is required
// because AuthPageClient calls `useSearchParams()` (Next 14 enforces
// a Suspense boundary around any Client Component that reads it).
export default function AuthPage() {
  return (
    <Suspense fallback={null}>
      <AuthPageClient />
    </Suspense>
  );
}
