"use client";

import { useEffect } from "react";
import type { JobPreferences, UserProfile } from "@/lib/api";
import type { ProfileCompletenessFieldId } from "@/lib/profileCompleteness";
import { ModalPortal } from "@/components/shared/ModalPortal";
import { ProfileCompletenessModalBody } from "./ProfileCompletenessModalBody";

interface ProfileCompletenessModalProps {
  fieldId: ProfileCompletenessFieldId | null;
  open: boolean;
  onClose: () => void;
  token: string;
  profile: UserProfile;
  preferences: JobPreferences | null;
  onProfileSaved: (next: UserProfile) => void;
  onPreferencesSaved: (next: JobPreferences) => void;
}

export function ProfileCompletenessModal({
  fieldId,
  open,
  onClose,
  token,
  profile,
  preferences,
  onProfileSaved,
  onPreferencesSaved,
}: ProfileCompletenessModalProps) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prev;
    };
  }, [open, onClose]);

  if (!open || !fieldId) return null;

  return (
    <ModalPortal>
      <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4">
        <div className="modal-backdrop" onClick={onClose} aria-hidden />
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="profile-completeness-modal-title"
          className="modal-panel w-full max-w-lg max-h-[90vh] flex flex-col rounded-t-2xl sm:rounded-2xl overflow-hidden"
        >
          <ProfileCompletenessModalBody
            fieldId={fieldId}
            token={token}
            profile={profile}
            preferences={preferences}
            onClose={onClose}
            onProfileSaved={onProfileSaved}
            onPreferencesSaved={onPreferencesSaved}
          />
        </div>
      </div>
    </ModalPortal>
  );
}
