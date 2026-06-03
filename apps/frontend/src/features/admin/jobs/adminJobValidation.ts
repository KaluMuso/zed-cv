/** Mirrors AdminJobCreate._check_invariants in apps/backend/app/schemas/jobs.py */

export function validateAdminJobApplyContact(
  applyUrl?: string,
  applyEmail?: string,
  contactPhone?: string,
): string | null {
  const url = applyUrl?.trim();
  const email = applyEmail?.trim();
  const phone = contactPhone?.trim();
  if (!url && !email && !phone) {
    return "Provide apply URL, apply email, or contact phone";
  }
  if (url && email) {
    return "Provide apply URL or apply email, not both";
  }
  return null;
}

/** admin_published is PATCH-only; POST with extra=forbid rejects it. */
export function finalizeAdminJobPayload<T extends Record<string, unknown>>(
  mode: "create" | "edit",
  payload: T,
  forcePublish: boolean,
): T {
  const out = { ...payload };
  if (mode === "create") {
    delete (out as { admin_published?: unknown }).admin_published;
  } else {
    (out as { admin_published?: boolean }).admin_published = forcePublish;
  }
  return out;
}
