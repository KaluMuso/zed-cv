"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  autoMatchPreferences,
  me as meApi,
  profile as profileApi,
  ApiError,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useAppStore } from "@/lib/zustand-store";
import { notify } from "@/lib/toast";
import { Loader2 } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SettingsCard, SettingsSectionHeader } from "../_components/SettingsShell";

export function DangerSection() {
  const router = useRouter();
  const { token, logout } = useAuth();
  const { setProfile: setZust } = useAppStore();
  const [phone, setPhone] = useState<string | null>(null);
  const [autoEnabled, setAutoEnabled] = useState(true);
  const [loading, setLoading] = useState(true);
  const [pausing, setPausing] = useState(false);
  const [openDelete, setOpenDelete] = useState(false);
  const [delConfirm, setDelConfirm] = useState("");
  const [delLoading, setDelLoading] = useState(false);
  const [delError, setDelError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    Promise.all([
      profileApi.get(token).then((p) => setPhone(p.phone)),
      autoMatchPreferences.get(token).then((r) => setAutoEnabled(r.auto_match_enabled)),
    ]).finally(() => setLoading(false));
  }, [token]);

  const pauseMatching = async () => {
    if (!token) return;
    setPausing(true);
    try {
      await autoMatchPreferences.patch(token, { auto_match_enabled: false });
      setAutoEnabled(false);
      notify.custom.success("Matching paused — turn it back on under Notifications.");
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Could not pause");
    } finally {
      setPausing(false);
    }
  };

  const phoneMatches = phone !== null && delConfirm === phone;

  return (
    <div>
      <SettingsSectionHeader title="Danger zone" />

      <SettingsCard className="mb-4 border-[color-mix(in_srgb,var(--copper-500)_35%,var(--line))]">
        <div className="eyebrow mb-2" style={{ color: "var(--copper-600)" }}>
          Pause matching
        </div>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <p className="text-sm max-w-md" style={{ color: "var(--muted)" }}>
            Stop receiving new scheduled matches without losing your CV, skills, or saved jobs.
          </p>
          <button
            type="button"
            className="btn btn-outline btn-sm shrink-0"
            disabled={loading || pausing || !autoEnabled}
            onClick={() => void pauseMatching()}
          >
            {pausing ? "Pausing…" : "Pause"}
          </button>
        </div>
      </SettingsCard>

      <SettingsCard className="border-[color-mix(in_srgb,var(--danger)_35%,var(--line))]">
        <div className="eyebrow mb-2" style={{ color: "var(--danger)" }}>
          Delete account
        </div>
        <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
          Permanently delete your account and all data. This cannot be undone. Payment records are
          retained, anonymised, for 7 years (Zambian tax law).
        </p>
        <Button type="button" variant="destructive" onClick={() => setOpenDelete(true)}>
          Delete account
        </Button>
      </SettingsCard>

      <Dialog
        open={openDelete}
        onOpenChange={(o) => {
          setOpenDelete(o);
          if (!o) {
            setDelConfirm("");
            setDelError(null);
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete your account?</DialogTitle>
            <DialogDescription>
              Type your WhatsApp number exactly as on your account, including the{" "}
              <span className="font-mono font-semibold">+260</span> prefix. We will erase your
              profile, CVs, and matches immediately.
            </DialogDescription>
          </DialogHeader>
          <Input
            autoFocus
            type="tel"
            autoComplete="off"
            value={delConfirm}
            onChange={(e) => {
              setDelConfirm(e.target.value);
              if (delError) setDelError(null);
            }}
            placeholder={phone ?? "+260971234567"}
            className="h-10 font-mono"
          />
          {delError ? (
            <p className="text-xs" style={{ color: "var(--danger)" }}>
              {delError}
            </p>
          ) : null}
          <DialogFooter>
            <Button variant="outline" type="button" onClick={() => setOpenDelete(false)} disabled={delLoading}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              type="button"
              disabled={!phoneMatches || delLoading}
              onClick={async () => {
                if (!token || !phoneMatches) return;
                setDelLoading(true);
                setDelError(null);
                try {
                  const result = await meApi.deleteAccount(token, delConfirm);
                  if (!result.deleted && !result.already_deleted) {
                    setDelError("The server reported the deletion did not run.");
                    return;
                  }
                  notify.custom.success("Account deleted.");
                  setOpenDelete(false);
                  logout();
                  setZust(null);
                  router.push("/");
                } catch (e) {
                  if (e instanceof ApiError && e.status === 400) {
                    setDelError(
                      "That doesn't match the phone number on your account. Type it exactly, including +260.",
                    );
                  } else {
                    setDelError(e instanceof Error ? e.message : "Could not delete");
                  }
                } finally {
                  setDelLoading(false);
                }
              }}
            >
              {delLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : "Delete forever"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
