"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ManualCvDraft } from "./types";

export const MANUAL_DRAFT_STORAGE_KEY = "zedapply:manual-cv-draft:v1";
const DRAFT_TTL_MS = 14 * 24 * 60 * 60 * 1000;
const WRITE_DEBOUNCE_MS = 400;

type StoredDraft = {
  version: 1;
  savedAt: string;
  step: string;
  data: ManualCvDraft;
};

function isStoredDraft(value: unknown): value is StoredDraft {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return (
    v.version === 1 &&
    typeof v.savedAt === "string" &&
    typeof v.step === "string" &&
    typeof v.data === "object" &&
    v.data !== null
  );
}

function readStored(): { step: string; data: ManualCvDraft } | null {
  try {
    if (typeof window === "undefined") return null;
    const raw = window.localStorage.getItem(MANUAL_DRAFT_STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as unknown;
    if (!isStoredDraft(parsed)) return null;
    const savedAtMs = Date.parse(parsed.savedAt);
    if (!Number.isFinite(savedAtMs) || Date.now() - savedAtMs > DRAFT_TTL_MS) {
      window.localStorage.removeItem(MANUAL_DRAFT_STORAGE_KEY);
      return null;
    }
    return { step: parsed.step, data: parsed.data };
  } catch {
    return null;
  }
}

function writeStored(step: string, data: ManualCvDraft): void {
  try {
    if (typeof window === "undefined") return;
    const payload: StoredDraft = {
      version: 1,
      savedAt: new Date().toISOString(),
      step,
      data,
    };
    window.localStorage.setItem(MANUAL_DRAFT_STORAGE_KEY, JSON.stringify(payload));
  } catch {
    /* quota / private mode */
  }
}

export function clearManualDraftStorage(): void {
  try {
    if (typeof window === "undefined") return;
    window.localStorage.removeItem(MANUAL_DRAFT_STORAGE_KEY);
  } catch {
    /* ignore */
  }
}

export function useManualDraftPersistence() {
  const [initial] = useState(() => readStored());
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const queueWrite = useCallback((step: string, data: ManualCvDraft) => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      writeStored(step, data);
      timer.current = null;
    }, WRITE_DEBOUNCE_MS);
  }, []);

  const clearDraft = useCallback(() => {
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
    clearManualDraftStorage();
  }, []);

  useEffect(() => {
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);

  return { initialDraft: initial?.data ?? null, initialStep: initial?.step ?? null, queueWrite, clearDraft };
}
