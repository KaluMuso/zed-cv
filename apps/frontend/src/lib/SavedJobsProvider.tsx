"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { notify } from "@/lib/toast";
import { savedJobs as savedJobsApi } from "@/lib/api";
import { useAuth } from "@/lib/auth";

interface SavedJobsContextValue {
  savedIds: Set<string>;
  loading: boolean;
  isSaved: (jobId: string) => boolean;
  toggle: (jobId: string) => Promise<void>;
  refresh: () => Promise<void>;
}

const SavedJobsContext = createContext<SavedJobsContextValue | undefined>(
  undefined
);

export function SavedJobsProvider({ children }: { children: ReactNode }) {
  const { token, isAuthenticated } = useAuth();
  const [savedIds, setSavedIds] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!token) {
      setSavedIds(new Set());
      return;
    }
    setLoading(true);
    try {
      const res = await savedJobsApi.list(token);
      setSavedIds(new Set(res.jobs.map((j) => j.id)));
    } catch {
      setSavedIds(new Set());
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => {
    if (!isAuthenticated || !token) {
      setSavedIds(new Set());
      return;
    }
    void refresh();
  }, [isAuthenticated, token, refresh]);

  const toggle = useCallback(
    async (jobId: string) => {
      if (!token) {
        notify.error("Sign in to save jobs.");
        return;
      }
      const wasSaved = savedIds.has(jobId);
      setSavedIds((prev) => {
        const next = new Set(prev);
        if (wasSaved) next.delete(jobId);
        else next.add(jobId);
        return next;
      });
      try {
        if (wasSaved) {
          await savedJobsApi.unsave(token, jobId);
          notify.unsaved("Removed from saved.");
        } else {
          await savedJobsApi.save(token, jobId);
          notify.saved("Saved.");
        }
      } catch {
        setSavedIds((prev) => {
          const next = new Set(prev);
          if (wasSaved) next.add(jobId);
          else next.delete(jobId);
          return next;
        });
        notify.error("Could not update saved jobs.");
      }
    },
    [token, savedIds]
  );

  const value = useMemo(
    () => ({
      savedIds,
      loading,
      isSaved: (jobId: string) => savedIds.has(jobId),
      toggle,
      refresh,
    }),
    [savedIds, loading, toggle, refresh]
  );

  return (
    <SavedJobsContext.Provider value={value}>
      {children}
    </SavedJobsContext.Provider>
  );
}

export function useSavedJobs(): SavedJobsContextValue {
  const ctx = useContext(SavedJobsContext);
  if (!ctx) {
    throw new Error("useSavedJobs must be used within SavedJobsProvider");
  }
  return ctx;
}
