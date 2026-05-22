"use client";

import { useState } from "react";
import Link from "next/link";
import { contact as contactApi, ApiError } from "@/lib/api";
import { Icon } from "@/components/ui/Icon";
import { notify } from "@/lib/toast";

type Status = "idle" | "submitting" | "success" | "error";

export default function ContactPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [message, setMessage] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Phone is optional. Surface a friendly hint client-side when present
  // but non-conforming so the user fixes it before the backend's 422.
  const phoneInvalid = phone.trim() !== "" && !/^\+260\d{9}$/.test(phone.trim());

  // Mirror backend constraints so the submit button accurately reflects
  // whether the request will validate. Backend remains authoritative.
  const formValid =
    name.trim().length > 0 &&
    /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email) &&
    message.trim().length >= 10 &&
    !phoneInvalid;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formValid || status === "submitting") return;
    setStatus("submitting");
    setErrorMsg(null);
    try {
      await contactApi.submit({
        name: name.trim(),
        email: email.trim(),
        phone: phone.trim() || undefined,
        message: message.trim(),
      });
      notify.custom.success("Message sent — we'll get back to you soon.");
      setStatus("success");
    } catch (err) {
      if (err instanceof ApiError && err.status === 429) {
        setErrorMsg(
          "You've sent a few messages recently. Please wait an hour and try again.",
        );
      } else if (err instanceof ApiError && err.status === 503) {
        setErrorMsg(err.detail);
      } else {
        setErrorMsg(
          err instanceof Error
            ? err.message
            : "Could not send your message. Please try again.",
        );
      }
      setStatus("error");
    }
  };

  if (status === "success") {
    return (
      <main className="max-w-[640px] mx-auto px-5 sm:px-6 py-16 sm:py-24 text-center">
        <div
          className="w-16 h-16 mx-auto mb-6 rounded-2xl flex items-center justify-center"
          style={{ background: "var(--green-100)", color: "var(--green-700)" }}
        >
          <Icon name="check" size={28} />
        </div>
        <h1
          className="font-display mb-3"
          style={{
            fontSize: "clamp(32px, 5vw, 56px)",
            lineHeight: 1.05,
            letterSpacing: "-0.02em",
          }}
        >
          Message sent.
        </h1>
        <p
          className="text-base mb-8"
          style={{ color: "var(--ink-2)", lineHeight: 1.7 }}
        >
          Thanks for reaching out. We read every message and will get back
          to you within a couple of working days.
        </p>
        <div className="flex flex-wrap gap-3 justify-center">
          <Link href="/jobs" className="btn btn-primary">
            Browse jobs <Icon name="arrowRight" size={14} />
          </Link>
          <button
            type="button"
            onClick={() => {
              setName("");
              setEmail("");
              setPhone("");
              setMessage("");
              setStatus("idle");
              setErrorMsg(null);
            }}
            className="btn btn-ghost"
          >
            Send another
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="max-w-[640px] mx-auto px-5 sm:px-6 py-12 sm:py-16">
      <div className="eyebrow">§ Contact</div>
      <h1
        className="font-display mt-2 mb-3"
        style={{
          fontSize: "clamp(36px, 5vw, 56px)",
          lineHeight: 1.05,
          letterSpacing: "-0.02em",
        }}
      >
        Get in touch.
      </h1>
      <p
        className="text-base mb-8"
        style={{ color: "var(--ink-2)", lineHeight: 1.7 }}
      >
        Questions about pricing, a partnership idea, or a bug to report?
        Drop us a note. For data-privacy requests, see our{" "}
        <Link
          href="/legal/privacy"
          style={{ color: "var(--green-700)", textDecoration: "underline" }}
        >
          Privacy Policy
        </Link>
        .
      </p>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <Field
          label="Your name"
          required
          input={
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              maxLength={120}
              required
              disabled={status === "submitting"}
              placeholder="Chanda Mwape"
              className="form-input"
              style={inputStyle}
            />
          }
        />
        <Field
          label="Email"
          required
          input={
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={status === "submitting"}
              placeholder="you@example.com"
              className="form-input"
              style={inputStyle}
            />
          }
        />
        <Field
          label="Phone"
          hint="Optional — Zambian +260 format only"
          input={
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              maxLength={20}
              disabled={status === "submitting"}
              placeholder="+260971234567"
              className="form-input"
              style={{
                ...inputStyle,
                borderColor: phoneInvalid
                  ? "var(--danger)"
                  : inputStyle.borderColor,
              }}
            />
          }
          error={phoneInvalid ? "Use +260 followed by 9 digits." : null}
        />
        <Field
          label="Message"
          required
          hint="Minimum 10 characters."
          input={
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              minLength={10}
              maxLength={5000}
              required
              disabled={status === "submitting"}
              rows={6}
              placeholder="Tell us what you're thinking..."
              className="form-input"
              style={{ ...inputStyle, resize: "vertical", padding: 14 }}
            />
          }
        />

        {errorMsg && (
          <div
            role="alert"
            className="text-sm p-3 rounded-md"
            style={{
              background: "color-mix(in oklab, var(--danger) 8%, var(--surface))",
              color: "var(--danger)",
              border: "1px solid var(--danger)",
            }}
          >
            {errorMsg}
          </div>
        )}

        <button
          type="submit"
          disabled={!formValid || status === "submitting"}
          className="btn btn-primary btn-lg w-full mt-2"
        >
          {status === "submitting" ? (
            <span className="spinner" />
          ) : (
            <>
              Send message <Icon name="arrowRight" size={16} />
            </>
          )}
        </button>
      </form>
    </main>
  );
}

const inputStyle: React.CSSProperties = {
  border: "1px solid var(--line-2)",
  borderRadius: "var(--r-sm)",
  background: "var(--surface)",
  color: "var(--ink)",
  height: 48,
  padding: "0 14px",
  fontSize: 15,
  outline: "none",
  width: "100%",
};

function Field({
  label,
  required,
  hint,
  error,
  input,
}: {
  label: string;
  required?: boolean;
  hint?: string;
  error?: string | null;
  input: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span
        className="text-sm font-medium"
        style={{ color: "var(--ink-2)" }}
      >
        {label}
        {required && (
          <span style={{ color: "var(--danger)", marginLeft: 4 }}>*</span>
        )}
      </span>
      {input}
      {error ? (
        <span className="text-xs" style={{ color: "var(--danger)" }}>
          {error}
        </span>
      ) : hint ? (
        <span className="text-xs" style={{ color: "var(--muted)" }}>
          {hint}
        </span>
      ) : null}
    </label>
  );
}
