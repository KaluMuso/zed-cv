"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { AdminJobCreatePayload } from "./types";

// Bumping this suffix invalidates older drafts without manual cleanup.
// Use case: when AdminJobCreatePayload shape changes in a future PR and
// rehydrating an old draft would crash a step component.
export const DRAFT_STORAGE_KEY = "zedcv:admin:job-draft:v1";

const DRAFT_TTL_MS = 7 * 24 * 60 * 60 * 1000; // 7 days
const WRITE_DEBOUNCE_MS = 400;

type Draft = {
  version: 1;
  savedAt: string; // ISO
  data: Partial<AdminJobCreatePayload>;
};

function isDraft(value: unknown): value is Draft {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return (
    v.version === 1 &&
    typeof v.savedAt === "string" &&
    typeof v.data === "object" &&
    v.data !== null
  );
}

function readDraft(): Partial<AdminJobCreatePayload> | null {
  try {
    if (typeof window === "undefined") return null;
    const raw = window.localStorage.getItem(DRAFT_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as unknown;
    if (!isDraft(parsed)) return null;
    const savedAtMs = Date.parse(parsed.savedAt);
    if (!Number.isFinite(savedAtMs)) return null;
    if (Date.now() - savedAtMs > DRAFT_TTL_MS) {
      // Stale — clear it so future loads don't keep re-reading + skipping.
      try {
        window.localStorage.removeItem(DRAFT_STORAGE_KEY);
      } catch {
        // ignore
      }
      return null;
    }
    return parsed.data;
  } catch {
    // QuotaExceeded, JSON parse, SecurityError (Safari private mode).
    // Silent — draft is a convenience, not a correctness requirement.
    return null;
  }
}

function writeDraft(data: Partial<AdminJobCreatePayload>): void {
  try {
    if (typeof window === "undefined") return;
    const payload: Draft = {
      version: 1,
      savedAt: new Date().toISOString(),
      data,
    };
    window.localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(payload));
  } catch {
    // ignore — see readDraft
  }
}

function clearDraftStorage(): void {
  try {
    if (typeof window === "undefined") return;
    window.localStorage.removeItem(DRAFT_STORAGE_KEY);
  } catch {
    // ignore
  }
}

/**
 * Persists the wizard's in-progress form data to localStorage so the
 * admin can leave and return without losing their work. Reads once on
 * mount; writes are debounced 400ms after the latest change.
 *
 * Returns the initial draft (or null) for the wizard to seed its form
 * state with, plus setters: queue a write whenever form data changes,
 * and clear the draft on successful submit (PR 4 hooks this).
 */
export function useDraftPersistence() {
  // Snapshot taken once on mount. We expose it as state so the wizard
  // can use a normal lazy initializer. After the initial read, this
  // value is never touched again — subsequent writes update storage
  // directly, not React state.
  const [initialDraft] = useState<Partial<AdminJobCreatePayload> | null>(
    () => readDraft(),
  );

  const writeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const queueWrite = useCallback((data: Partial<AdminJobCreatePayload>) => {
    if (writeTimer.current) {
      clearTimeout(writeTimer.current);
    }
    writeTimer.current = setTimeout(() => {
      writeDraft(data);
      writeTimer.current = null;
    }, WRITE_DEBOUNCE_MS);
  }, []);

  const clearDraft = useCallback(() => {
    if (writeTimer.current) {
      clearTimeout(writeTimer.current);
      writeTimer.current = null;
    }
    clearDraftStorage();
  }, []);

  // Flush any pending write on unmount so a quick close+reopen doesn't
  // drop the most recent keystroke.
  useEffect(() => {
    return () => {
      if (writeTimer.current) {
        clearTimeout(writeTimer.current);
        writeTimer.current = null;
      }
    };
  }, []);

  return { initialDraft, queueWrite, clearDraft };
}
