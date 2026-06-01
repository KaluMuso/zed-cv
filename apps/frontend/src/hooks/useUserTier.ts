"use client";

import { useEffect, useState } from "react";

import { useAuth } from "@/lib/auth";
import { profile as profileApi } from "@/lib/api";
import { normalizeTier, type SubscriptionTier } from "@/lib/tier-features";

export function useUserTier(): {
  tier: SubscriptionTier;
  loading: boolean;
} {
  const { token, isAuthenticated, isLoading: authLoading } = useAuth();
  const [tier, setTier] = useState<SubscriptionTier>("free");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated || !token) {
      setTier("free");
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    profileApi
      .get(token)
      .then((p) => {
        if (!cancelled) setTier(normalizeTier(p.subscription_tier));
      })
      .catch(() => {
        if (!cancelled) setTier("free");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [authLoading, isAuthenticated, token]);

  return { tier, loading };
}
