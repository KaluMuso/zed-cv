"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import {
  autoMatchPreferences,
  profile as profileApi,
  type AutoMatchPreferences,
  type UserPreferences,
} from "@/lib/api";
import { useAppStore } from "@/lib/zustand-store";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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

export default function SettingsPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading, logout, token } = useAuth();
  const { setProfile: setZust } = useAppStore();
  const [prefs, setPrefs] = useState<UserPreferences | null>(null);
  const [autoPrefs, setAutoPrefs] = useState<AutoMatchPreferences | null>(null);
  const [prefsLoading, setPrefsLoading] = useState(true);
  const [savingAlerts, setSavingAlerts] = useState(false);
  const [savingAutoMatch, setSavingAutoMatch] = useState(false);
  const [savingLang, setSavingLang] = useState(false);
  const [openDelete, setOpenDelete] = useState(false);
  const [delConfirm, setDelConfirm] = useState("");
  const [delLoading, setDelLoading] = useState(false);

  useEffect(() => {
    if (isLoading) {
      return;
    }
    if (!isAuthenticated || !token) {
      router.push("/auth");
      return;
    }
    Promise.allSettled([
      profileApi.getPreferences(token),
      autoMatchPreferences.get(token),
    ])
      .then(([prefsRes, autoRes]) => {
        if (prefsRes.status === "fulfilled") setPrefs(prefsRes.value);
        if (autoRes.status === "fulfilled") setAutoPrefs(autoRes.value);
        if (prefsRes.status === "rejected") throw prefsRes.reason;
      })
      .catch((e) => notify.error(e instanceof Error ? e.message : "Failed to load preferences"))
      .finally(() => setPrefsLoading(false));
  }, [isAuthenticated, isLoading, router, token]);

  if (isLoading || !isAuthenticated) {
    return <p className="text-sm text-muted-foreground">…</p>;
  }

  const updateAlerts = async (next: boolean) => {
    if (!token || !prefs) {
      return;
    }
    setSavingAlerts(true);
    try {
      const r = await profileApi.updatePreferences(token, { whatsapp_alerts: next });
      setPrefs(r);
      notify.custom.success(next ? "WhatsApp alerts on." : "WhatsApp alerts off.");
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Could not save");
    } finally {
      setSavingAlerts(false);
    }
  };

  const updateLanguage = async (next: "en" | "bem") => {
    if (!token) {
      return;
    }
    setSavingLang(true);
    try {
      const r = await profileApi.updatePreferences(token, { language: next });
      setPrefs(r);
      notify.custom.success("Language preference saved.");
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Could not save");
    } finally {
      setSavingLang(false);
    }
  };

  const updateAutoMatch = async (next: boolean) => {
    if (!token) {
      return;
    }
    setSavingAutoMatch(true);
    try {
      const r = await autoMatchPreferences.patch(token, { auto_match_enabled: next });
      setAutoPrefs(r);
      notify.custom.success(next ? "Auto-match enabled." : "Auto-match disabled.");
    } catch (e) {
      notify.error(e instanceof Error ? e.message : "Could not save");
    } finally {
      setSavingAutoMatch(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl sm:text-3xl font-bold mb-2">Settings</h1>
      <p className="text-muted-foreground text-sm mb-6">How ZedApply reaches you and account safety.</p>

      <Card className="mb-4">
        <CardHeader>
          <CardTitle>WhatsApp & alerts</CardTitle>
          <CardDescription>Control daily nudges and match alerts to your WhatsApp.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center justify-between gap-4 min-h-11">
            <span className="text-sm">Daily job alerts on WhatsApp</span>
            {prefsLoading ? (
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            ) : (
              <input
                type="checkbox"
                className="h-5 w-5 rounded border-input"
                checked={prefs?.whatsapp_alerts ?? true}
                disabled={savingAlerts}
                onChange={(e) => updateAlerts(e.target.checked)}
              />
            )}
          </div>
        </CardContent>
      </Card>

      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Auto-match</CardTitle>
          <CardDescription>Let ZedApply run scheduled matching. Manual refresh still works when off.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between gap-4 min-h-11">
            <span className="text-sm">Scheduled auto-match</span>
            {prefsLoading ? (
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            ) : (
              <input
                type="checkbox"
                className="h-5 w-5 rounded border-input"
                checked={autoPrefs?.auto_match_enabled ?? true}
                disabled={savingAutoMatch}
                onChange={(e) => updateAutoMatch(e.target.checked)}
              />
            )}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Language</CardTitle>
          <CardDescription>Bemba is partially supported. WhatsApp messages will switch to Bemba where available.</CardDescription>
        </CardHeader>
        <CardContent>
          {prefsLoading ? (
            <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
          ) : (
            <select
              className="h-10 min-h-10 rounded-md border border-input bg-background px-3 text-sm"
              value={prefs?.language ?? "en"}
              disabled={savingLang}
              onChange={(e) => updateLanguage(e.target.value as "en" | "bem")}
            >
              <option value="en">English (Zambia)</option>
              <option value="bem">Bemba (icibemba)</option>
            </select>
          )}
        </CardContent>
      </Card>

      <div className="mt-8 rounded-xl border border-destructive/40 p-4">
        <h2 className="text-sm font-semibold text-destructive">Delete account</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Permanently remove your profile, CV, skills, matches, and payment history. This cannot be undone.
        </p>
        <Button
          className="mt-3"
          type="button"
          variant="destructive"
          onClick={() => setOpenDelete(true)}
        >
          Delete my account
        </Button>
      </div>

      <Dialog
        open={openDelete}
        onOpenChange={(o) => {
          setOpenDelete(o);
          if (!o) {
            setDelConfirm("");
          }
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Are you sure?</DialogTitle>
            <DialogDescription>
              Type <span className="font-mono font-semibold">DELETE</span> to confirm. We will erase your data immediately.
            </DialogDescription>
          </DialogHeader>
          <Input
            autoFocus
            value={delConfirm}
            onChange={(e) => setDelConfirm(e.target.value)}
            placeholder="DELETE"
            className="h-10"
          />
          <DialogFooter>
            <Button variant="outline" type="button" onClick={() => setOpenDelete(false)} disabled={delLoading}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              type="button"
              disabled={delConfirm !== "DELETE" || delLoading}
              onClick={async () => {
                if (!token) {
                  return;
                }
                setDelLoading(true);
                try {
                  await profileApi.remove(token);
                  notify.custom.success("Account deleted.");
                  setOpenDelete(false);
                  logout();
                  setZust(null);
                  router.push("/");
                } catch (e) {
                  notify.error(e instanceof Error ? e.message : "Could not delete");
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
