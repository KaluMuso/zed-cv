"use client";

import { useCallback, useMemo, useState } from "react";
import { Icon } from "@/components/ui/Icon";
import { notify } from "@/lib/toast";

export function ProfileReferralCard({
  userId,
  userName,
  referralCode,
  referralSignupsCount = 0,
  referralQualifiedCount = 0,
}: {
  userId: string;
  userName?: string | null;
  referralCode: string;
  referralSignupsCount?: number;
  referralQualifiedCount?: number;
}) {
  const [copied, setCopied] = useState(false);
  const code = referralCode.trim().toUpperCase();

  const inviteLink = useMemo(() => {
    if (typeof window === "undefined" || !code) return "";
    const url = new URL("/auth", window.location.origin);
    url.searchParams.set("next", "/matches");
    url.searchParams.set("ref", code);
    return url.toString();
  }, [code]);

  const inviteMessage = useMemo(() => {
    const who = userName?.trim() || "A friend";
    const codeLine = code ? ` Use code ${code} if asked.` : "";
    return `${who} invited you to ZedApply — AI job matching for Zambia.${codeLine} Sign up: ${inviteLink}`;
  }, [inviteLink, userName, code]);

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

  if (!code) {
    return (
      <div className="card p-6">
        <div className="eyebrow mb-2">Invite friends</div>
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          Your referral code is being set up. Refresh the page in a moment.
        </p>
      </div>
    );
  }

  return (
    <div className="card p-6">
      <div className="eyebrow mb-2">Invite friends</div>
      <p className="text-sm mb-4 leading-relaxed" style={{ color: "var(--muted)" }}>
        Share ZedApply with people job hunting in Zambia. When they sign up with your link,
        we track the referral on your account.
      </p>

      <div
        className="rounded-lg border px-4 py-3 mb-4"
        style={{ borderColor: "var(--line)", background: "var(--bg-2)" }}
      >
        <div
          className="text-xs font-medium uppercase tracking-wider mb-1"
          style={{ color: "var(--muted)" }}
        >
          Your referral code
        </div>
        <div
          className="font-mono text-xl font-semibold tracking-widest"
          style={{ color: "var(--green-700)" }}
        >
          {code}
        </div>
        <p className="text-xs mt-2" style={{ color: "var(--muted)" }}>
          <span className="font-semibold" style={{ color: "var(--ink-2)" }}>
            {referralSignupsCount}
          </span>{" "}
          {referralSignupsCount === 1 ? "friend has" : "friends have"} signed up
          {referralQualifiedCount > 0 ? (
            <>
              {" "}
              ·{" "}
              <span className="font-semibold" style={{ color: "var(--ink-2)" }}>
                {referralQualifiedCount}
              </span>{" "}
              uploaded a CV (you earned +5 bonus matches each)
            </>
          ) : null}
        </p>
      </div>

      <div className="flex flex-col gap-2">
        <button
          type="button"
          className="btn btn-primary w-full btn-sm"
          onClick={() => void copyLink()}
        >
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
        Referral rewards (bonus matches or credits) will apply automatically once you qualify
        paid tiers. Link also accepts your user id for older invites.
      </p>
    </div>
  );
}
