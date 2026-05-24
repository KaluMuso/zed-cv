"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { dataRights, profile as profileApi } from "@/lib/api";
import { SensitiveActionOtpDialog } from "@/components/settings/SensitiveActionOtpDialog";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";
import { notify } from "@/lib/toast";

function formatCountdown(scheduledAt: string): string {
  const end = new Date(scheduledAt).getTime();
  const diff = Math.max(0, end - Date.now());
  const days = Math.floor(diff / (24 * 3600 * 1000));
  const hours = Math.floor((diff % (24 * 3600 * 1000)) / (3600000));
  if (days > 0) return `${days} day${days === 1 ? "" : "s"}, ${hours} hour${hours === 1 ? "" : "s"}`;
  return `${hours} hour${hours === 1 ? "" : "s"}`;
}

export default function AccountSettingsPage() {
  const router = useRouter();
  const { isAuthenticated, isLoading, token, logout } = useAuth();
  const [phone, setPhone] = useState("");
  const [loadingProfile, setLoadingProfile] = useState(true);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [pendingDeletion, setPendingDeletion] = useState<{
    requestId: string;
    scheduledAt: string;
  } | null>(null);
  const [exportJob, setExportJob] = useState<{
    requestId: string;
    status: string;
    downloadUrl?: string;
    expiresAt?: string;
  } | null>(null);
  const [exportPolling, setExportPolling] = useState(false);

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated || !token) {
      router.push("/auth");
      return;
    }
    profileApi
      .get(token)
      .then((p) => setPhone(p.phone))
      .catch((e) => notify.error(e instanceof Error ? e.message : "Failed to load profile"))
      .finally(() => setLoadingProfile(false));
  }, [isAuthenticated, isLoading, router, token]);

  const pollExport = useCallback(
    async (requestId: string) => {
      if (!token) return;
      setExportPolling(true);
      try {
        for (let i = 0; i < 40; i++) {
          const status = await dataRights.exportStatus(token, requestId);
          if (status.status === "ready" && status.download_url) {
            setExportJob({
              requestId,
              status: "ready",
              downloadUrl: status.download_url,
              expiresAt: status.download_expires_at ?? undefined,
            });
            return;
          }
          if (status.status === "failed") {
            notify.error(status.failure_reason ?? "Export failed");
            return;
          }
          await new Promise((r) => setTimeout(r, 2000));
        }
        notify.error("Export is taking longer than expected. Check back shortly.");
      } finally {
        setExportPolling(false);
      }
    },
    [token]
  );

  if (isLoading || !isAuthenticated) {
    return <p className="text-sm text-muted-foreground">…</p>;
  }

  return (
    <div>
      <p className="text-sm text-muted-foreground mb-4">
        <Link href="/settings" className="underline">
          Settings
        </Link>{" "}
        / Account &amp; data
      </p>
      <h1 className="text-2xl sm:text-3xl font-bold mb-2">Account &amp; data</h1>
      <p className="text-muted-foreground text-sm mb-6">
        Export or delete your personal data under the Zambia Data Protection Act 2021.
      </p>

      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Download my data</CardTitle>
          <CardDescription>
            ZIP with profile, CV files, matches, payments, and consent history. Link expires in 7
            days.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {exportJob?.status === "ready" && exportJob.downloadUrl ? (
            <div className="space-y-2">
              <p className="text-sm text-green-700 dark:text-green-400">Your export is ready.</p>
              <Button asChild>
                <a href={exportJob.downloadUrl} download rel="noopener noreferrer">
                  Download ZIP
                </a>
              </Button>
              {exportJob.expiresAt && (
                <p className="text-xs text-muted-foreground">
                  Link expires {new Date(exportJob.expiresAt).toLocaleString()}
                </p>
              )}
            </div>
          ) : (
            <Button
              type="button"
              variant="outline"
              disabled={loadingProfile || exportPolling || !phone}
              onClick={() => setExportOpen(true)}
            >
              {exportPolling ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  Preparing export…
                </>
              ) : (
                "Download my data"
              )}
            </Button>
          )}
        </CardContent>
      </Card>

      <Card className="border-destructive/40">
        <CardHeader>
          <CardTitle className="text-destructive">Delete my account</CardTitle>
          <CardDescription>
            After confirmation you have 7 days to cancel. Then we erase CVs, matches, and skills;
            payment rows are anonymised for tax retention.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {pendingDeletion ? (
            <div className="space-y-3">
              <p className="text-sm">
                Deletion scheduled for{" "}
                <strong>{new Date(pendingDeletion.scheduledAt).toLocaleString()}</strong> (
                {formatCountdown(pendingDeletion.scheduledAt)} remaining).
              </p>
              <Button
                type="button"
                variant="outline"
                onClick={async () => {
                  if (!token) return;
                  try {
                    await dataRights.cancelDeletion(token, pendingDeletion.requestId);
                    setPendingDeletion(null);
                    notify.custom.success("Deletion cancelled.");
                  } catch (e) {
                    notify.error(e instanceof Error ? e.message : "Could not cancel");
                  }
                }}
              >
                Cancel deletion
              </Button>
            </div>
          ) : (
            <Button
              type="button"
              variant="destructive"
              disabled={loadingProfile || !phone}
              onClick={() => setDeleteOpen(true)}
            >
              Delete my account
            </Button>
          )}
        </CardContent>
      </Card>

      <SensitiveActionOtpDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        phone={phone}
        title="Confirm account deletion"
        description="Enter the OTP we sent to verify this sensitive action."
        onVerified={async (otpCode) => {
          if (!token) return;
          const res = await dataRights.requestDeletion(token, otpCode);
          if (res.request_id && res.scheduled_at) {
            setPendingDeletion({
              requestId: res.request_id,
              scheduledAt: res.scheduled_at,
            });
            notify.custom.success("Deletion scheduled. You can cancel within 7 days.");
          }
        }}
      />

      <SensitiveActionOtpDialog
        open={exportOpen}
        onOpenChange={setExportOpen}
        phone={phone}
        title="Confirm data export"
        description="Enter the OTP we sent to verify this sensitive action."
        onVerified={async (otpCode) => {
          if (!token) return;
          const res = await dataRights.requestExport(token, otpCode);
          if (res.request_id) {
            setExportJob({ requestId: res.request_id, status: res.status });
            notify.custom.success("Export started.");
            await pollExport(res.request_id);
          }
        }}
      />
    </div>
  );
}
