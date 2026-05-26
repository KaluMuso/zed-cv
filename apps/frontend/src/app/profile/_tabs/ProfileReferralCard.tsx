"use client";

import { useCallback, useMemo, useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { notify } from "@/lib/toast";

function referralCodeFromUserId(userId: string): string {
  return userId.replace(/-/g, "").slice(0, 8).toUpperCase();
}

export function ProfileReferralCard({
  userId,
  userName,
}: {
  userId: string;
  userName?: string | null;
}) {
  const [copied, setCopied] = useState(false);
  const code = useMemo(() => referralCodeFromUserId(userId), [userId]);

  const inviteLink = useMemo(() => {
    if (typeof window === "undefined") return "";
    const url = new URL("/auth", window.location.origin);
    url.searchParams.set("next", "/matches");
    url.searchParams.set("ref", userId);
    return url.toString();
  }, [userId]);

  const inviteMessage = useMemo(() => {
    const who = userName?.trim() || "A friend";
    return `${who} invited you to ZedApply — AI job matching for Zambia. Sign up with your phone: ${inviteLink}`;
  }, [inviteLink, userName]);

  const copyLink = useCallback(async () => {
    if (!inviteLink) return;
    try {
      await navigator.clipboard.writeText(inviteMessage);
      setCopied(true);
      notify.custom.success("Invite link copied");
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      notify.error("Could not copy — select the link manually");
    }
  }, [inviteLink, inviteMessage]);

  const whatsappHref = useMemo(() => {
    if (!inviteLink) return "#";
    return `https://wa.me/?text=${encodeURIComponent(inviteMessage)}`;
  }, [inviteLink, inviteMessage]);

  return (
    <div className="card p-6">
      <div className="eyebrow mb-2">Invite friends</div>
      <p className="text-sm mb-4 leading-relaxed" style={{ color: "var(--muted)" }}>
        Share ZedApply with people job hunting in Zambia. Your personal link opens sign-in and
        sends them to matches after they upload a CV.
      </p>

      <div
        className="rounded-lg border px-4 py-3 mb-4"
        style={{ borderColor: "var(--line)", background: "var(--bg-2)" }}
      >
        <div className="text-xs font-medium uppercase tracking-wider mb-1" style={{ color: "var(--muted)" }}>
          Your referral code
        </div>
        <div className="font-mono text-xl font-semibold tracking-widest" style={{ color: "var(--green-700)" }}>
          {code}
        </div>
      </div>

      <div className="flex flex-col gap-2">
        <button type="button" className="btn btn-primary w-full btn-sm" onClick={() => void copyLink()}>
          <Icon name={copied ? "check" : "link"} size={14} />
          {copied ? "Copied" : "Copy invite message"}
        </button>
        <a
          href={whatsappHref}
          target="_blank"
          rel="noopener noreferrer"
          className="btn btn-outline w-full btn-sm justify-center gap-1.5"
        >
          <Icon name="whatsapp" size={14} />
          Share on WhatsApp
        </a>
      </div>

      <p className="text-xs mt-3 leading-relaxed" style={{ color: "var(--muted)" }}>
        Referral rewards tracking is coming soon. Your code is saved with this link for when we
        launch credits.
      </p>
    </div>
  );
}
