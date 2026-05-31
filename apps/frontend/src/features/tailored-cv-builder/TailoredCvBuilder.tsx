"use client";

import { useEffect, useState } from "react";
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
import { subscription as subscriptionApi } from "@/lib/api";
import { BuilderHeader } from "./BuilderHeader";
import { BasicsStepForm } from "./BasicsStepForm";
import { CoverLetterStep } from "./CoverLetterStep";
import { EducationStepForm } from "./EducationStepForm";
import { ExperienceStepForm } from "./ExperienceStepForm";
import { LivePreviewPane } from "./LivePreviewPane";
import { PreviewStepForm } from "./PreviewStepForm";
import { SkillsStepForm } from "./SkillsStepForm";
import { StyleStepForm } from "./StyleStepForm";
import { useTailoredCvBuilderStore } from "./store";
import type { BuilderStep } from "./types";
import { useHydrateBuilderFromProfile } from "./useHydrateBuilderFromProfile";
import "./builder.css";
import "./print.css";

function LeftPane({
  step,
  jobId,
  matchId,
  jobTitle,
  company,
  token,
  subscriptionTier,
  setStep,
  onOpenPreview,
}: {
  step: BuilderStep;
  jobId: string | null;
  matchId: string | null;
  jobTitle: string;
  company: string;
  token: string | null;
  subscriptionTier: string | null | undefined;
  setStep: (s: BuilderStep) => void;
  onOpenPreview?: () => void;
}) {
  switch (step) {
    case "basics":
      return <BasicsStepForm />;
    case "experience":
      return <ExperienceStepForm />;
    case "education":
      return <EducationStepForm />;
    case "skills":
      return <SkillsStepForm />;
    case "style":
      return <StyleStepForm />;
    case "coverLetter":
      return (
        <CoverLetterStep
          jobId={jobId}
          matchId={matchId}
          jobTitle={jobTitle}
          company={company}
          token={token}
          subscriptionTier={subscriptionTier}
          onBack={() => setStep("style")}
          onNext={() => setStep("preview")}
        />
      );
    case "preview":
      return <PreviewStepForm onOpenPreview={onOpenPreview} />;
    default:
      return null;
  }
}

export function TailoredCvBuilder() {
  const searchParams = useSearchParams();
  const { token } = useAuth();
  const jobId = searchParams.get("jobId");
  const matchId = searchParams.get("matchId");
  const jobTitle = searchParams.get("jobTitle") ?? "";
  const company = searchParams.get("company") ?? "";
  const [subscriptionTier, setSubscriptionTier] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setSubscriptionTier(null);
      return;
    }
    subscriptionApi
      .get(token)
      .then((sub) => setSubscriptionTier(sub.tier))
      .catch(() => setSubscriptionTier("free"));
  }, [token]);
  const step = useTailoredCvBuilderStore((s) => s.step);
  const setStep = useTailoredCvBuilderStore((s) => s.setStep);
  const hydratedFromProfile = useTailoredCvBuilderStore((s) => s.hydratedFromProfile);
  const resetDraft = useTailoredCvBuilderStore((s) => s.resetDraft);
  const isDesktop = useMediaQuery("(min-width: 1024px)");
  const [previewOpen, setPreviewOpen] = useState(false);

  useHydrateBuilderFromProfile(token);

  return (
    <div className="w-full">
      {hydratedFromProfile ? (
        <div
          className="mb-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 rounded-lg border px-4 py-3 text-sm"
          style={{ borderColor: "var(--line)", background: "var(--green-50)" }}
        >
          <span style={{ color: "var(--green-700)" }}>
            Loaded from your uploaded CV. Edit any section — the preview updates live.
          </span>
          <button type="button" className="btn btn-ghost btn-sm shrink-0" onClick={resetDraft}>
            Reset sample data
          </button>
        </div>
      ) : null}
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
            matchId={matchId}
            jobTitle={jobTitle}
            company={company}
            token={token}
            subscriptionTier={subscriptionTier}
            setStep={setStep}
            onOpenPreview={() => setPreviewOpen(true)}
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
