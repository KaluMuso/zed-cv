"use client";

import { FaqsEditor } from "./FaqsEditor";

export function FaqsTab({ token }: { token: string }) {
  return <FaqsEditor token={token} />;
}
