"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function MatchDeepLinkClient({ matchId }: { matchId: string }) {
  const router = useRouter();

  useEffect(() => {
    const q = new URLSearchParams({ open: matchId });
    router.replace(`/matches?${q.toString()}`);
  }, [matchId, router]);

  return (
    <p className="p-6 text-sm text-[var(--muted-foreground)]">Opening your match…</p>
  );
}
