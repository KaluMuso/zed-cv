/** Web Push helpers — permission UX + subscription sync. */

const DECLINED_KEY = "zedapply_push_declined_at";
const MATCHES_VISITED_KEY = "zedapply_matches_page_visited";
const DECLINE_COOLDOWN_MS = 30 * 24 * 60 * 60 * 1000;

export const PUSH_UX_STORAGE = {
  declinedAt: DECLINED_KEY,
  matchesVisited: MATCHES_VISITED_KEY,
} as const;

export function markMatchesPageVisited(): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(MATCHES_VISITED_KEY, "1");
  } catch {
    /* quota / private mode */
  }
}

export function hasVisitedMatchesPage(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return localStorage.getItem(MATCHES_VISITED_KEY) === "1";
  } catch {
    return false;
  }
}

export function recordPushDeclined(): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(DECLINED_KEY, new Date().toISOString());
  } catch {
    /* ignore */
  }
}

function declinedWithinCooldown(): boolean {
  if (typeof window === "undefined") return false;
  try {
    const raw = localStorage.getItem(DECLINED_KEY);
    if (!raw) return false;
    const at = Date.parse(raw);
    if (Number.isNaN(at)) return false;
    return Date.now() - at < DECLINE_COOLDOWN_MS;
  } catch {
    return false;
  }
}

export function isEligibleForPushPrompt(creditedMatchCount: number): boolean {
  if (typeof window === "undefined") return false;
  if (!("Notification" in window) || !("serviceWorker" in navigator)) return false;
  if (creditedMatchCount < 1) return false;
  if (!hasVisitedMatchesPage()) return false;
  if (declinedWithinCooldown()) return false;
  const perm = Notification.permission;
  return perm === "default";
}

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = atob(base64);
  const out = new Uint8Array(raw.length);
  for (let i = 0; i < raw.length; i += 1) {
    out[i] = raw.charCodeAt(i);
  }
  return out;
}

export async function subscribeToWebPush(token: string): Promise<boolean> {
  const vapidPublic = process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY;
  if (!vapidPublic) {
    throw new Error("Push is not configured (missing VAPID public key)");
  }

  const registration = await navigator.serviceWorker.ready;
  let subscription = await registration.pushManager.getSubscription();
  if (!subscription) {
    subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidPublic) as BufferSource,
    });
  }

  const json = subscription.toJSON();
  if (!json.endpoint || !json.keys?.p256dh || !json.keys?.auth) {
    throw new Error("Invalid push subscription from browser");
  }

  const { push } = await import("@/lib/api");
  await push.subscribe(token, {
    endpoint: json.endpoint,
    keys: { p256dh: json.keys.p256dh, auth: json.keys.auth },
    expirationTime: json.expirationTime ?? null,
  });
  return true;
}

export async function requestPushPermissionAndSubscribe(
  token: string,
): Promise<"granted" | "denied" | "unsupported"> {
  if (!("Notification" in window)) return "unsupported";
  const permission = await Notification.requestPermission();
  if (permission !== "granted") return "denied";
  await subscribeToWebPush(token);
  return "granted";
}
