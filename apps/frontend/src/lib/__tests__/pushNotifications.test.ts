import { afterEach, describe, expect, it, vi } from "vitest";
import {
  isEligibleForPushPrompt,
  PUSH_UX_STORAGE,
  markMatchesPageVisited,
  recordPushDeclined,
} from "@/lib/pushNotifications";

describe("pushNotifications UX gates", () => {
  afterEach(() => {
    localStorage.clear();
    vi.unstubAllGlobals();
  });

  it("never prompts without a credited match", () => {
    markMatchesPageVisited();
    vi.stubGlobal("Notification", { permission: "default" });
    vi.stubGlobal("navigator", { serviceWorker: {} });
    expect(isEligibleForPushPrompt(0)).toBe(false);
  });

  it("never prompts before matches page visit", () => {
    vi.stubGlobal("Notification", { permission: "default" });
    vi.stubGlobal("navigator", { serviceWorker: {} });
    expect(isEligibleForPushPrompt(3)).toBe(false);
  });

  it("prompts after credit + visit when permission is default", () => {
    markMatchesPageVisited();
    vi.stubGlobal("Notification", { permission: "default" });
    vi.stubGlobal("navigator", { serviceWorker: {} });
    expect(isEligibleForPushPrompt(1)).toBe(true);
  });

  it("respects 30-day decline cooldown", () => {
    markMatchesPageVisited();
    const thirtyOneDaysMs = 31 * 24 * 60 * 60 * 1000;
    localStorage.setItem(
      PUSH_UX_STORAGE.declinedAt,
      new Date(Date.now() - thirtyOneDaysMs).toISOString(),
    );
    vi.stubGlobal("Notification", { permission: "default" });
    vi.stubGlobal("navigator", { serviceWorker: {} });
    expect(isEligibleForPushPrompt(2)).toBe(true);

    recordPushDeclined();
    expect(isEligibleForPushPrompt(2)).toBe(false);
  });
});
