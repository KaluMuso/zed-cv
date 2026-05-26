"use client";

import { Suspense } from "react";
import { TailoredCvBuilder } from "@/features/tailored-cv-builder/TailoredCvBuilder";

export function CvBuilderPageClient() {
  return (
    <Suspense fallback={<p className="text-sm text-muted-foreground">Loading builder…</p>}>
      <TailoredCvBuilder />
    </Suspense>
  );
}
