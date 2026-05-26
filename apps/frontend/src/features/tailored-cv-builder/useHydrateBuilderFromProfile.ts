"use client";

import { useEffect, useRef } from "react";
import { profile as profileApi } from "@/lib/api";
import { mapProfileToDraft } from "./mapProfileToDraft";
import { useTailoredCvBuilderStore } from "./store";

/**
 * Loads the builder draft from the user's uploaded CV (GET /profile → cv_sections).
 * Runs once per mount when a token is present.
 */
export function useHydrateBuilderFromProfile(token: string | null) {
  const setDraft = useTailoredCvBuilderStore((s) => s.setDraft);
  const hydratedFromProfile = useTailoredCvBuilderStore((s) => s.hydratedFromProfile);
  const ranRef = useRef(false);

  useEffect(() => {
    if (!token || ranRef.current || hydratedFromProfile) return;
    ranRef.current = true;

    let cancelled = false;
    profileApi
      .get(token)
      .then((prof) => {
        if (cancelled) return;
        const mapped = mapProfileToDraft(prof);
        if (mapped) {
          setDraft(mapped, { fromProfile: true });
        }
      })
      .catch(() => {
        /* keep sample draft */
      });

    return () => {
      cancelled = true;
    };
  }, [token, hydratedFromProfile, setDraft]);
}
