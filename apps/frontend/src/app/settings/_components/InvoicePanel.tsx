"use client";

import { useCallback, useEffect, useState } from "react";
import {
  subscription as subscriptionApi,
  type InvoiceDetail,
  type PaymentHistoryRow,
} from "@/lib/api";
import { notify } from "@/lib/toast";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

function formatNgwee(amount: number, currency: string): string {
  const major = amount / 100;
  const symbol = currency === "USD" ? "$" : "K";
  return `${symbol}${major.toLocaleString("en-ZM", { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
}

function formatPaymentDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-ZM", {
      day: "numeric",
      month: "short",
      year: "numeric",
    });
  } catch {
    return "—";
  }
}

function statusLabel(status: string): string {
  if (status === "completed") return "Paid";
  if (status === "pending") return "Pending";
  if (status === "failed") return "Failed";
  if (status === "refunded") return "Refunded";
  return status;
}

type InvoicePanelProps = {
  token: string;
  payments: PaymentHistoryRow[];
  onRefresh?: () => void;
};

export function InvoicePanel({ token, payments, onRefresh }: InvoicePanelProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [invoice, setInvoice] = useState<InvoiceDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [emailSending, setEmailSending] = useState(false);

  const openInvoice = useCallback(
    async (paymentId: string) => {
      setSelectedId(paymentId);
      setLoading(true);
      setInvoice(null);
      try {
        const detail = await subscriptionApi.getInvoice(token, paymentId);
        setInvoice(detail);
      } catch {
        notify.error("Could not load invoice");
        setSelectedId(null);
      } finally {
        setLoading(false);
      }
    },
    [token],
  );

  useEffect(() => {
    if (!selectedId) setInvoice(null);
  }, [selectedId]);

  const downloadInvoice = async () => {
    if (!selectedId) return;
    try {
      const res = await fetch(
        `${API_BASE}/subscription/payments/${selectedId}/invoice/download`,
        { headers: { Authorization: `Bearer ${token}` } },
      );
      if (!res.ok) throw new Error("download failed");
      const html = await res.text();
      const blob = new Blob([html], { type: "text/html;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${invoice?.invoice_number ?? "invoice"}.html`;
      a.click();
      URL.revokeObjectURL(url);
      notify.success("Invoice downloaded — open in browser and Print → Save as PDF");
    } catch {
      notify.error("Download failed");
    }
  };

  const emailInvoice = async () => {
    if (!selectedId) return;
    setEmailSending(true);
    try {
      await subscriptionApi.emailInvoice(token, selectedId);
      notify.success("Invoice sent to your email");
      onRefresh?.();
    } catch {
      notify.error("Could not email invoice — check notification settings");
    } finally {
      setEmailSending(false);
    }
  };

  if (payments.length === 0) {
    return (
      <p className="text-sm" style={{ color: "var(--muted)" }}>
        No invoices yet. Completed payments will appear here after you upgrade.
      </p>
    );
  }

  return (
    <>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-[var(--line)] text-left text-xs uppercase tracking-wide" style={{ color: "var(--muted)" }}>
              <th className="py-2 pr-3 font-medium">Invoice</th>
              <th className="py-2 pr-3 font-medium">Date</th>
              <th className="py-2 pr-3 font-medium">Amount</th>
              <th className="py-2 pr-3 font-medium">Status</th>
              <th className="py-2 font-medium"> </th>
            </tr>
          </thead>
          <tbody>
            {payments.map((row) => (
              <tr key={row.id} className="border-b border-[var(--line)] last:border-0">
                <td className="py-3 pr-3 font-mono text-xs">
                  ZED-{row.id.replace(/-/g, "").slice(0, 8).toUpperCase()}
                </td>
                <td className="py-3 pr-3">{formatPaymentDate(row.completed_at ?? row.created_at)}</td>
                <td className="py-3 pr-3 font-medium">{formatNgwee(row.amount, row.currency)}</td>
                <td className="py-3 pr-3">{statusLabel(row.status)}</td>
                <td className="py-3 text-right">
                  {row.status === "completed" || row.status === "refunded" ? (
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => openInvoice(row.id)}
                    >
                      View
                    </Button>
                  ) : (
                    <span className="text-xs" style={{ color: "var(--muted)" }}>—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Dialog open={Boolean(selectedId)} onOpenChange={(open) => !open && setSelectedId(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{invoice?.invoice_number ?? "Invoice"}</DialogTitle>
          </DialogHeader>
          {loading ? (
            <p className="text-sm text-muted-foreground">Loading invoice…</p>
          ) : invoice ? (
            <div className="space-y-4 text-sm">
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <div className="text-xs uppercase tracking-wide text-muted-foreground">Plan</div>
                  <div className="font-medium">{invoice.tier_label}</div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-muted-foreground">Amount</div>
                  <div className="font-medium">
                    {formatNgwee(invoice.amount_ngwee, invoice.currency)}
                  </div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-muted-foreground">Date</div>
                  <div>{formatPaymentDate(invoice.issued_at)}</div>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wide text-muted-foreground">Reference</div>
                  <div className="font-mono text-xs break-all">{invoice.reference}</div>
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                Bill to {invoice.customer_name}
                {invoice.customer_email ? ` · ${invoice.customer_email}` : ""}
              </p>
              <div className="flex flex-wrap gap-2 pt-2">
                <Button type="button" size="sm" onClick={downloadInvoice}>
                  Download
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant="outline"
                  disabled={emailSending}
                  onClick={emailInvoice}
                >
                  {emailSending ? "Sending…" : "Email copy"}
                </Button>
              </div>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </>
  );
}
