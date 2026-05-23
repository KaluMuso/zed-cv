"use client";

import { TierConfigEditor } from "./TierConfigEditor";

export function TierConfigTab({ token }: { token: string }) {
  return <TierConfigEditor token={token} />;
}
