"use client";

import { useState } from "react";
import { me as meApi, ApiError } from "@/lib/api";
import { Icon } from "@/components/ui/Icon";

export function DataPrivacyCard({
  token,
  phone,
  onDeleted,
}: {
  token: string;
  phone: string;
  onDeleted: () => void;
}) {
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const handleExport = async () => {
    setExporting(true);
    setExportError(null);
    try {
      await meApi.export(token);
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setExportError(
          "You can export your data once per hour. Please try again later.",
        );
      } else {
        setExportError(
          err instanceof Error ? err.message : "Could not export your data.",
        );
      }
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="card p-6">
      <div className="eyebrow mb-3">Data &amp; privacy</div>
      <p
        className="text-xs mb-4"
        style={{ color: "var(--muted)", lineHeight: 1.6 }}
      >
        Exercise your rights under the Zambia Data Protection Act 2021.
      </p>

      <div className="space-y-3">
        <div>
          <button
            type="button"
            onClick={handleExport}
            disabled={exporting}
            className="btn btn-ghost w-full btn-sm"
            style={{ justifyContent: "space-between" }}
          >
            <span>
              {exporting ? "Preparing download..." : "Export my data"}
            </span>
            <Icon name={exporting ? "zap" : "arrowRight"} size={14} />
          </button>
          {exportError && (
            <p
              className="text-xs mt-2"
              style={{ color: "var(--danger)" }}
            >
              {exportError}
            </p>
          )}
          <p
            className="text-xs mt-2"
            style={{ color: "var(--muted)" }}
          >
            Downloads a JSON file with your profile, CVs, matches, and
            payment history.
          </p>
        </div>

        <div
          style={{ borderTop: "1px solid var(--line)", paddingTop: 12 }}
        >
          <button
            type="button"
            onClick={() => setModalOpen(true)}
            className="btn btn-ghost w-full btn-sm"
            style={{
              justifyContent: "space-between",
              color: "var(--danger)",
            }}
          >
            <span>Delete my account</span>
            <Icon name="x" size={14} />
          </button>
          <p
            className="text-xs mt-2"
            style={{ color: "var(--muted)" }}
          >
            Permanently removes your account. Some payment records are
            retained, anonymised, for 7 years (Zambian tax law).
          </p>
        </div>
      </div>

      {modalOpen && (
        <DeleteAccountModal
          token={token}
          phone={phone}
          onClose={() => setModalOpen(false)}
          onDeleted={onDeleted}
        />
      )}
    </div>
  );
}

function DeleteAccountModal({
  token,
  phone,
  onClose,
  onDeleted,
}: {
  token: string;
  phone: string;
  onClose: () => void;
  onDeleted: () => void;
}) {
  const [typed, setTyped] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Disable the destructive button until the user has typed something
  // that at least matches the stored phone client-side. The backend is
  // the authoritative check (byte-exact compare), but mirroring it in
  // the UI avoids a confusing 400 round-trip on the obvious typo case.
  const matches = typed === phone;

  const handleDelete = async () => {
    if (!matches) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await meApi.deleteAccount(token, typed);
      if (result.deleted || result.already_deleted) {
        onDeleted();
      } else {
        setError("The server reported the deletion did not run.");
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setError(
          "That doesn't match the phone number on your account. Type it exactly, including +260.",
        );
      } else {
        setError(
          err instanceof Error ? err.message : "Could not delete your account.",
        );
      }
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
      <div
        className="fixed inset-0"
        style={{ background: "rgba(0,0,0,0.5)", backdropFilter: "blur(4px)" }}
        onClick={submitting ? undefined : onClose}
      />
      <div
        className="relative z-10 w-full max-w-md rounded-t-2xl sm:rounded-2xl"
        style={{
          background: "var(--surface)",
          boxShadow: "var(--shadow-lg)",
          padding: 24,
        }}
      >
        <div className="flex items-start justify-between mb-4">
          <div>
            <div className="eyebrow mb-1" style={{ color: "var(--danger)" }}>
              Permanent action
            </div>
            <h3
              className="font-display"
              style={{ fontSize: 24, letterSpacing: "-0.01em" }}
            >
              Delete your account
            </h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            aria-label="Close"
            className="shrink-0 w-8 h-8 rounded-full flex items-center justify-center"
            style={{
              border: "1px solid var(--line-2)",
              color: "var(--muted)",
            }}
          >
            <Icon name="x" size={14} />
          </button>
        </div>

        <p
          className="text-sm mb-4"
          style={{ color: "var(--ink-2)", lineHeight: 1.6 }}
        >
          This will permanently delete your profile, CVs, matches and
          generated documents. Payment records will be retained,
          anonymised, for 7 years as required by Zambian tax law.
        </p>
        <p
          className="text-sm mb-4"
          style={{ color: "var(--ink-2)", lineHeight: 1.6 }}
        >
          To confirm, type your phone number exactly as it appears on
          your account, including the <code>+260</code> prefix.
        </p>

        <label
          className="text-xs font-medium block mb-2"
          style={{ color: "var(--ink-2)" }}
        >
          Phone number on your account
        </label>
        <input
          type="tel"
          autoComplete="off"
          value={typed}
          onChange={(e) => {
            setTyped(e.target.value);
            if (error) setError(null);
          }}
          disabled={submitting}
          placeholder="+260971234567"
          className="w-full px-3.5 h-[44px] text-sm font-mono outline-none"
          style={{
            border: error
              ? "1px solid var(--danger)"
              : "1px solid var(--line-2)",
            borderRadius: "var(--r-sm)",
            background: "var(--bg-2)",
            color: "var(--ink)",
          }}
        />
        {error && (
          <p
            className="text-xs mt-2"
            style={{ color: "var(--danger)" }}
          >
            {error}
          </p>
        )}

        <div className="flex gap-2 mt-6">
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="btn btn-ghost flex-1"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={handleDelete}
            disabled={!matches || submitting}
            className="btn flex-1"
            style={{
              background: matches ? "var(--danger)" : "var(--line-2)",
              color: matches ? "#fff" : "var(--muted)",
              border: "none",
            }}
          >
            {submitting ? "Deleting..." : "Delete my account"}
          </button>
        </div>
      </div>
    </div>
  );
}
