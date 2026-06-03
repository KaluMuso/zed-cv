"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Icon } from "@/components/ui/Icon";
import { useAuth } from "@/lib/auth";
import { inAppNotifications, type InAppNotification } from "@/lib/api";

function formatWhen(iso: string): string {
  try {
    const date = new Date(iso);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    if (diffHours < 1) return "Just now";
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
  } catch {
    return "";
  }
}

function typeIcon(type: InAppNotification["type"]): string {
  switch (type) {
    case "web_push":
      return "sparkle";
    case "tier_expiry":
      return "clock";
    case "invoice":
      return "file";
    case "admin_broadcast":
      return "bell";
    default:
      return "bell";
  }
}

export function NotificationsPanel({
  onBack,
  onClose,
  onUnreadCountChange,
}: {
  onBack: () => void;
  onClose: () => void;
  onUnreadCountChange?: (count: number) => void;
}) {
  const { token } = useAuth();
  const router = useRouter();
  const [items, setItems] = useState<InAppNotification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    setError(null);
    try {
      const data = await inAppNotifications.list(token);
      setItems(data.items);
      onUnreadCountChange?.(data.unread_count);
    } catch {
      setError("Could not load notifications.");
    } finally {
      setLoading(false);
    }
  }, [token, onUnreadCountChange]);

  useEffect(() => {
    void load();
  }, [load]);

  const handleOpen = async (item: InAppNotification) => {
    if (!token) return;
    const url = typeof item.payload.url === "string" ? item.payload.url : "/dashboard";
    if (!item.read_at) {
      try {
        const res = await inAppNotifications.markRead(token, item.id);
        setItems((prev) => {
          const next = prev.map((n) => (n.id === item.id ? res.notification : n));
          onUnreadCountChange?.(next.filter((n) => !n.read_at).length);
          return next;
        });
      } catch {
        // Still navigate even if mark-read fails
      }
    }
    onClose();
    router.push(url);
  };

  return (
    <div className="flex flex-col max-h-[min(24rem,70vh)]">
      <div
        className="flex items-center gap-2 px-4 py-3 border-b shrink-0"
        style={{ borderColor: "var(--line)" }}
      >
        <button
          type="button"
          onClick={onBack}
          className="p-1 rounded-md hover:bg-[var(--bg-2)] transition-colors"
          aria-label="Back to menu"
        >
          <Icon name="arrowLeft" size={16} />
        </button>
        <span className="font-semibold text-sm" style={{ color: "var(--ink)" }}>
          Notifications
        </span>
      </div>

      <div className="overflow-y-auto flex-1 py-1">
        {loading ? (
          <p className="px-4 py-6 text-sm text-center" style={{ color: "var(--muted)" }}>
            Loading…
          </p>
        ) : error ? (
          <p className="px-4 py-6 text-sm text-center" style={{ color: "var(--danger)" }}>
            {error}
          </p>
        ) : items.length === 0 ? (
          <p className="px-4 py-6 text-sm text-center" style={{ color: "var(--muted)" }}>
            No notifications yet. Match alerts, billing reminders, and updates will appear here.
          </p>
        ) : (
          items.map((item) => {
            const title =
              typeof item.payload.title === "string"
                ? item.payload.title
                : "Notification";
            const body =
              typeof item.payload.body === "string" ? item.payload.body : "";
            const unread = !item.read_at;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => void handleOpen(item)}
                className="flex w-full items-start gap-2.5 px-4 py-2.5 text-left hover:bg-[var(--bg-2)] transition-colors"
                role="menuitem"
              >
                <Icon
                  name={typeIcon(item.type)}
                  size={16}
                  className="shrink-0 mt-0.5 opacity-80"
                />
                <div className="min-w-0 flex-1">
                  <div
                    className={`text-sm truncate ${unread ? "font-semibold" : ""}`}
                    style={{ color: "var(--ink)" }}
                  >
                    {title}
                  </div>
                  {body ? (
                    <div
                      className="text-xs truncate mt-0.5"
                      style={{ color: "var(--muted)" }}
                    >
                      {body}
                    </div>
                  ) : null}
                  <div className="text-[10px] mt-0.5" style={{ color: "var(--muted)" }}>
                    {formatWhen(item.created_at)}
                  </div>
                </div>
                {unread ? (
                  <span
                    className="w-2 h-2 rounded-full shrink-0 mt-1.5"
                    style={{ background: "var(--green-600)" }}
                    aria-hidden
                  />
                ) : null}
              </button>
            );
          })
        )}
      </div>

      <div
        className="px-4 py-2 border-t shrink-0"
        style={{ borderColor: "var(--line)" }}
      >
        <Link
          href="/settings/notifications"
          onClick={onClose}
          className="text-xs underline"
          style={{ color: "var(--green-700)" }}
        >
          Notification preferences
        </Link>
      </div>
    </div>
  );
}
