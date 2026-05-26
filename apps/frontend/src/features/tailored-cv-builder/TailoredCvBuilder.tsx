"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { Icon } from "@/components/ui/Icon";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useMediaQuery } from "@/hooks/useMediaQuery";
import { useAuth } from "@/lib/auth";
import { BuilderHeader } from "./BuilderHeader";
import { BasicsStepForm } from "./BasicsStepForm";
import { CoverLetterStep } from "./CoverLetterStep";
import { LivePreviewPane } from "./LivePreviewPane";
import { StepPlaceholder } from "./StepPlaceholder";
import { useTailoredCvBuilderStore } from "./store";
import type { BuilderStep } from "./types";
import "./builder.css";

function LeftPane({
  step,
  jobId,
  jobTitle,
  company,
  token,
  setStep,
}: {
  step: BuilderStep;
  jobId: string | null;
  jobTitle: string;
  company: string;
  token: string | null;
  setStep: (s: BuilderStep) => void;
}) {
  if (step === "basics") {
    return <BasicsStepForm />;
  }
  if (step === "coverLetter") {
    return (
      <CoverLetterStep
        jobId={jobId}
        jobTitle={jobTitle}
        company={company}
        token={token}
        onBack={() => setStep("style")}
        onNext={() => setStep("preview")}
      />
    );
  }
  if (step === "preview") {
    return (
      <div className="card p-6 max-w-xl">
        <h2 className="text-lg font-semibold mb-2" style={{ color: "var(--ink)" }}>
          Review & export
        </h2>
        <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
          Check the live preview on the right (or tap Preview on mobile). Download or copy
          sections when export is enabled for your plan.
        </p>
        <button type="button" className="btn btn-ghost" onClick={() => setStep("coverLetter")}>
          Back to cover letter
        </button>
      </div>
    );
  }
  return <StepPlaceholder step={step} />;
}

export function TailoredCvBuilder() {
  const searchParams = useSearchParams();
  const { token } = useAuth();
  const jobId = searchParams.get("jobId");
  const jobTitle = searchParams.get("jobTitle") ?? "";
  const company = searchParams.get("company") ?? "";
  const step = useTailoredCvBuilderStore((s) => s.step);
  const setStep = useTailoredCvBuilderStore((s) => s.setStep);
  const isDesktop = useMediaQuery("(min-width: 1024px)");
  const [previewOpen, setPreviewOpen] = useState(false);

  return (
    <div className="w-full">
      <BuilderHeader
        currentStep={step}
        onStepClick={setStep}
        jobTitle={jobTitle}
        company={company}
      />

      {!isDesktop && (
        <div className="mb-4">
          <button
            type="button"
            className="btn btn-ghost w-full justify-center"
            style={{ border: "1px solid var(--line-2)" }}
            onClick={() => setPreviewOpen(true)}
          >
            <Icon name="eye" size={16} />
            Preview tailored CV
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6 lg:items-stretch lg:min-h-[calc(100vh-220px)]">
        <div className="min-w-0 flex flex-col">
          <LeftPane
            step={step}
            jobId={jobId}
            jobTitle={jobTitle}
            company={company}
            token={token}
            setStep={setStep}
          />
        </div>

        {isDesktop ? (
          <LivePreviewPane className="lg:sticky lg:top-4 lg:max-h-[calc(100vh-120px)]" />
        ) : null}
      </div>

      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-lg w-[calc(100%-2rem)] p-0 gap-0 overflow-hidden">
          <DialogHeader className="px-4 pt-4 pb-0">
            <DialogTitle>CV preview</DialogTitle>
          </DialogHeader>
          <div className="max-h-[min(80vh,720px)] overflow-auto">
            <LivePreviewPane className="border-0 rounded-none shadow-none" />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
