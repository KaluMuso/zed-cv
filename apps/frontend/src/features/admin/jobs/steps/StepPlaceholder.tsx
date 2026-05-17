"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export type StepPlaceholderProps = {
  stepNumber: number;
  title: string;
};

// Steps 3-5 of the wizard ship in the next PR. This placeholder keeps
// the navigation honest (Back works, the progress indicator renders
// the full 1-5 range) without dangling half-finished form code.
export function StepPlaceholder({ stepNumber, title }: StepPlaceholderProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          Step {stepNumber} — {title}
        </CardTitle>
        <CardDescription>
          This step lands in the next PR. Use Back to return.
        </CardDescription>
      </CardHeader>
      <CardContent />
    </Card>
  );
}
