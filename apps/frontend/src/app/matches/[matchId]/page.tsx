import type { Metadata } from "next";
import { pageMetadata } from "@/lib/site-metadata";
import MatchDeepLinkClient from "./MatchDeepLinkClient";

export const metadata: Metadata = pageMetadata({
  title: "Match",
  description: "Open a job match on ZedApply.",
});

type Props = { params: { matchId: string } };

export default function MatchDeepLinkPage({ params }: Props) {
  return <MatchDeepLinkClient matchId={params.matchId} />;
}
