"use client";

import { notify } from "@/lib/toast";

/** @deprecated Use `notify` from `@/lib/toast` directly. */
export function notifySuccess(message: string) {
  notify.custom.success(message);
}

/** @deprecated Use `notify` from `@/lib/toast` directly. */
export function notifyError(message: string) {
  notify.error(message);
}

/** @deprecated Use `notify` from `@/lib/toast` directly. */
export function notifyInfo(message: string) {
  notify.info(message);
}
