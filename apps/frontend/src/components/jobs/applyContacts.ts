/** Re-export apply resolution from the single source of truth. */
export type {
  ApplyContactKind,
  ApplyContactMethod,
  ApplyJobFields,
} from "@/lib/applyLink";

export {
  hasStructuredApplyContact,
  resolveApplyContactMethods as buildApplyContactMethods,
} from "@/lib/applyLink";

/** Minimal job fields needed by the Apply modal (matches list + full job detail). */
export type ApplyModalJob = import("@/lib/applyLink").ApplyJobFields & {
  description?: string | null;
  application_instructions?: string | null;
};
