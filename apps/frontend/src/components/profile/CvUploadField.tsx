"use client";

import { useCallback, useRef, useState } from "react";
import { cv as cvApi, ApiError } from "@/lib/api";
import { Icon } from "@/components/ui/Icon";

const VALID_TYPES = [
  "application/pdf",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "image/jpeg",
  "image/png",
];

export function CvUploadField({
  token,
  cvUploaded,
  onUploaded,
}: {
  token: string;
  cvUploaded: boolean;
  onUploaded: () => void;
}) {
  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const handleUpload = useCallback(
    async (file: File) => {
      if (!VALID_TYPES.includes(file.type)) {
        setMessage("Please upload a PDF, Word document, or image.");
        return;
      }
      if (file.size > 10 * 1024 * 1024) {
        setMessage("File must be under 10MB.");
        return;
      }
      setUploading(true);
      setMessage("");
      try {
        const result = await cvApi.upload(token, file);
        const skillsCount = result?.parsed_skills?.length ?? 0;
        if (result?.queued) {
          setMessage("CV queued — we'll process it when AI capacity is back.");
        } else {
          setMessage(`CV uploaded! ${skillsCount} skills extracted.`);
        }
        onUploaded();
      } catch (err) {
        if (err instanceof ApiError) {
          setMessage(err.detail || "Upload failed");
        } else if (err instanceof Error) {
          setMessage(err.message);
        } else {
          setMessage("Upload failed");
        }
      } finally {
        setUploading(false);
      }
    },
    [token, onUploaded],
  );

  return (
    <div>
      {cvUploaded ? (
        <p className="text-sm mb-3" style={{ color: "var(--muted)" }}>
          You already have a CV on file. Upload a new file to replace it and refresh skills.
        </p>
      ) : (
        <p className="text-sm mb-3" style={{ color: "var(--muted)" }}>
          Upload a PDF, Word document, or image (max 10MB).
        </p>
      )}
      <input
        ref={fileRef}
        type="file"
        accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"
        className="sr-only"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) void handleUpload(file);
          e.target.value = "";
        }}
      />
      <button
        type="button"
        disabled={uploading}
        onClick={() => fileRef.current?.click()}
        className="btn btn-outline w-full justify-center gap-2"
      >
        {uploading ? (
          "Uploading…"
        ) : (
          <>
            <Icon name="upload" size={18} />
            {cvUploaded ? "Replace CV" : "Choose file"}
          </>
        )}
      </button>
      {message ? (
        <p className="text-xs mt-2" style={{ color: "var(--muted)" }} role="status">
          {message}
        </p>
      ) : null}
    </div>
  );
}
