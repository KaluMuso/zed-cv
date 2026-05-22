import type { Metadata } from "next";
import { pageMetadata } from "@/lib/site-metadata";
import MatchesPageClient from "./MatchesPageClient";

export const metadata: Metadata = pageMetadata({
  title: "Matches",
  description:
    "See AI-scored job matches tailored to your CV and skills on ZedApply.",
});

export default function MatchesPage() {
  return <MatchesPageClient />;
}
