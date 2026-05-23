"use client";

import { useEffect, useState } from "react";
import { admin, type AdminStats, type AdminTierBreakdown } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { notify } from "@/lib/toast";

import { OverviewTab } from "./_tabs/OverviewTab";
import { JobsTab } from "./_tabs/JobsTab";
import { UsersTab } from "./_tabs/UsersTab";
import { MatchesTab } from "./_tabs/MatchesTab";
import { PricingTab } from "./_tabs/PricingTab";
import { TierConfigTab } from "./_tabs/TierConfigTab";
import { LegalTab } from "./_tabs/LegalTab";
import { ReviewJobsTab } from "./_tabs/ReviewJobsTab";

export default function AdminPage() {
  const { token } = useAuth();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [breakdown, setBreakdown] = useState<AdminTierBreakdown | null>(null);

  useEffect(() => {
    if (!token) return;
    admin
      .stats(token)
      .then(setStats)
      .catch((e) => notify.error(e instanceof Error ? e.message : "Failed to load stats"));
    admin
      .subscriptions(token, { per_page: 1 })
      .then((r) => setBreakdown(r.breakdown))
      .catch(() => setBreakdown(null));
  }, [token]);

  if (!token) return null;

  return (
    <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 py-8">
      <h1 className="text-2xl font-bold">Admin</h1>
      <p className="text-sm text-muted-foreground">
        Live data. Superadmin only.
      </p>

      <Tabs className="mt-6" defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview" className="min-h-9">Overview</TabsTrigger>
          <TabsTrigger value="jobs" className="min-h-9">Jobs</TabsTrigger>
          <TabsTrigger value="review" className="min-h-9">Review queue</TabsTrigger>
          <TabsTrigger value="users" className="min-h-9">Users</TabsTrigger>
          <TabsTrigger value="matches" className="min-h-9">Matches</TabsTrigger>
          <TabsTrigger value="pricing" className="min-h-9">Pricing</TabsTrigger>
          <TabsTrigger value="tier-config" className="min-h-9">Tier Config</TabsTrigger>
          <TabsTrigger value="legal" className="min-h-9">Legal</TabsTrigger>
        </TabsList>

        <TabsContent className="mt-4" value="overview">
          <OverviewTab token={token} stats={stats} breakdown={breakdown} />
        </TabsContent>
        <TabsContent className="mt-4" value="jobs">
          <JobsTab token={token} />
        </TabsContent>
        <TabsContent className="mt-4" value="review">
          <ReviewJobsTab token={token} />
        </TabsContent>
        <TabsContent className="mt-4" value="users">
          <UsersTab token={token} />
        </TabsContent>
        <TabsContent className="mt-4" value="matches">
          <MatchesTab token={token} />
        </TabsContent>
        <TabsContent className="mt-4" value="pricing">
          <PricingTab token={token} stats={stats} breakdown={breakdown} />
        </TabsContent>
        <TabsContent className="mt-4" value="tier-config">
          <TierConfigTab token={token} />
        </TabsContent>
        <TabsContent className="mt-4" value="legal">
          <LegalTab token={token} />
        </TabsContent>
      </Tabs>
    </div>
  );
}
