/// <reference lib="webworker" />
/**
 * Custom service worker chunk merged into public/sw.js at build time
 * (@ducanh2912/next-pwa customWorkerSrc). Handles Web Push display + clicks.
 */

declare const self: ServiceWorkerGlobalScope;

type PushPayload = {
  title?: string;
  body?: string;
  url?: string;
  tag?: string;
  icon?: string;
  badge?: string;
  data?: { url?: string; match_id?: string };
};

function parsePushPayload(event: PushEvent): PushPayload {
  if (!event.data) {
    return { title: "ZedApply", body: "You have a new notification", url: "/matches" };
  }
  try {
    return event.data.json() as PushPayload;
  } catch {
    return {
      title: "ZedApply",
      body: event.data.text(),
      url: "/matches",
    };
  }
}

self.addEventListener("push", (event: PushEvent) => {
  const payload = parsePushPayload(event);
  const title = payload.title ?? "ZedApply";
  const options: NotificationOptions = {
    body: payload.body ?? "",
    tag: payload.tag,
    icon: payload.icon ?? "/icons/icon-192.svg",
    badge: payload.badge ?? "/icons/icon-192.svg",
    data: payload.data ?? { url: payload.url ?? "/matches" },
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event: NotificationEvent) => {
  event.notification.close();
  const raw = event.notification.data as { url?: string } | undefined;
  const targetPath = raw?.url ?? "/matches";
  const absolute =
    targetPath.startsWith("http") ? targetPath : `${self.location.origin}${targetPath}`;

  event.waitUntil(
    (async () => {
      const windowClients = await self.clients.matchAll({
        type: "window",
        includeUncontrolled: true,
      });
      for (const client of windowClients) {
        if ("focus" in client) {
          await client.focus();
          if ("navigate" in client && typeof client.navigate === "function") {
            await client.navigate(absolute);
          }
          return;
        }
      }
      await self.clients.openWindow(absolute);
    })(),
  );
});

export {};
