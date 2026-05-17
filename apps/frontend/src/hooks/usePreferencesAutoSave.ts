"use client";

/**
 * Debounced auto-save for the Preferences tab.
 *
 * Reasoning: every form field on the tab is "save on blur with 800ms
 * debounce". Centralised here so PreferencesTab.tsx doesn't reimplement
 * a debounce + status state machine for each field.
 *
 * Save status drives the sticky indicator at the top of the tab:
 *   - "idle"     — nothing pending, nothing saving
 *   - "pending"  — change registered, debounce timer running
 *   - "saving"   — PATCH in flight
 *   - "saved"    — most recent save succeeded; carries a timestamp
 *   - "error"    — most recent save failed; carries an error message
 */
import { useCallback, useEffect, useRef, useState } from "react";
import {
  preferencesApi,
  type JobPreferences,
  type JobPreferencesUpdate,
  ApiError,
} from "@/lib/api";

export type SaveStatus =
  | { kind: "idle" }
  | { kind: "pending" }
  | { kind: "saving" }
  | { kind: "saved"; at: Date }
  | { kind: "error"; message: string };

interface UsePreferencesAutoSaveOptions {
  token: string;
  debounceMs?: number;
  onSaved: (next: JobPreferences) => void;
}

export function usePreferencesAutoSave({
  token,
  debounceMs = 800,
  onSaved,
}: UsePreferencesAutoSaveOptions) {
  const [status, setStatus] = useState<SaveStatus>({ kind: "idle" });
  const pendingPatch = useRef<JobPreferencesUpdate>({});
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Token of the most recent flush. Used to drop stale responses if
  // the user fires off another save before the previous one returns —
  // without this, a slow save could clobber a faster one.
  const flushToken = useRef(0);

  const flush = useCallback(async () => {
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
    const patch = pendingPatch.current;
    pendingPatch.current = {};
    if (Object.keys(patch).length === 0) {
      return;
    }
    const myToken = ++flushToken.current;
    setStatus({ kind: "saving" });
    try {
      const next = await preferencesApi.patch(token, patch);
      if (myToken !== flushToken.current) {
        // A newer save has started; ignore our success.
        return;
      }
      setStatus({ kind: "saved", at: new Date() });
      onSaved(next);
    } catch (err) {
      if (myToken !== flushToken.current) return;
      let msg = "Couldn't save";
      if (err instanceof ApiError) {
        msg = err.detail || msg;
      } else if (err instanceof Error) {
        msg = err.message;
      }
      setStatus({ kind: "error", message: msg });
    }
  }, [token, onSaved]);

  const queue = useCallback(
    (patch: JobPreferencesUpdate) => {
      pendingPatch.current = mergePatch(pendingPatch.current, patch);
      setStatus({ kind: "pending" });
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => {
        void flush();
      }, debounceMs);
    },
    [debounceMs, flush],
  );

  // Best-effort flush before the page unloads. Synchronous: uses
  // navigator.sendBeacon if available — falls back to fetch keepalive.
  // Without this, a user hitting "Back" between blur and the timer
  // firing loses their edits.
  useEffect(() => {
    const handler = () => {
      if (Object.keys(pendingPatch.current).length === 0) return;
      // We can't use the preferencesApi.patch path because it relies on
      // the standard fetch promise that the browser cancels on unload.
      // sendBeacon takes a Blob and ignores the response.
      const body = JSON.stringify(pendingPatch.current);
      const url = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1"}/preferences`;
      if (navigator.sendBeacon) {
        // sendBeacon doesn't carry the Authorization header. Fall through
        // to fetch-keepalive when we have a token to send.
        if (!token) {
          navigator.sendBeacon(url, body);
          return;
        }
      }
      // fetch with keepalive=true lets the request outlive the page.
      fetch(url, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body,
        keepalive: true,
      }).catch(() => {});
    };
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [token]);

  // Clear the timer on unmount so a late save doesn't fire against a
  // dead component.
  useEffect(() => {
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);

  return { status, queue, flush, setStatus };
}

function mergePatch(
  prev: JobPreferencesUpdate,
  next: JobPreferencesUpdate,
): JobPreferencesUpdate {
  // Last-write-wins per field. extras gets a shallow merge so a
  // partial update to one key doesn't clear the others.
  const merged: JobPreferencesUpdate = { ...prev, ...next };
  if (prev.extras && next.extras) {
    merged.extras = { ...prev.extras, ...next.extras };
  }
  return merged;
}
