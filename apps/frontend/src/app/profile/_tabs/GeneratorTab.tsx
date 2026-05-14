"use client";

import { useState } from "react";
import { cv as cvApi, type CVSections, type UserProfile } from "@/lib/api";
import { InputStep, type InputStepValues } from "./generator/InputStep";
import { PreviewStep, type TemplateKey } from "./generator/PreviewStep";
import { EditStep } from "./generator/EditStep";
import { HistoryPanel } from "./generator/HistoryPanel";
import {
  parseGeneratedCv,
  cvSectionsToParsed,
  type ParsedCV,
} from "./generator/parseCv";

import "./generator/print.css";

type Step = "input" | "preview" | "edit";

type GenerationMeta = {
  jobTitle: string;
  company: string;
  wordCount: number;
};

/**
 * Multi-step CV generator: input → preview → edit → export.
 *
 * State is held here so navigation between steps preserves edits and the
 * Download PDF action always uses the latest parsed CV. The original LLM
 * output is kept in `originalParsed` so the editor's Reset can roll back
 * without an extra LLM call.
 *
 * History items are fetched by HistoryPanel; clicking one re-loads it into
 * the preview state via `loadFromHistory` so a user can re-export old CVs
 * (saves OpenRouter spend on re-runs).
 */
export function GeneratorTab({
  token,
  profileData,
}: {
  token: string;
  profileData: UserProfile;
}) {
  const tier = profileData.subscription_tier;
  const tierAllowed = tier === "starter" || tier === "professional" || tier === "super_standard";

  const [step, setStep] = useState<Step>("input");
  const [inputs, setInputs] = useState<InputStepValues>({
    jobTitle: "",
    company: "",
    jobDescription: "",
  });
  const [parsed, setParsed] = useState<ParsedCV | null>(null);
  const [originalParsed, setOriginalParsed] = useState<ParsedCV | null>(null);
  // Structured sections from /cv/generate (task #59). Non-null when the
  // LLM returned the new shape; templates prefer this for richer rendering.
  // Cleared on user edit so templates fall back to the edited ParsedCV.
  const [cvSections, setCvSections] = useState<CVSections | null>(null);
  const [originalCvSections, setOriginalCvSections] = useState<CVSections | null>(null);
  const [meta, setMeta] = useState<GenerationMeta | null>(null);
  const [template, setTemplate] = useState<TemplateKey>("ats");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [historyRefresh, setHistoryRefresh] = useState(0);

  const startOver = () => {
    setStep("input");
    setParsed(null);
    setOriginalParsed(null);
    setCvSections(null);
    setOriginalCvSections(null);
    setMeta(null);
    setError(null);
  };

  // Header fields the structured → ParsedCV converter needs. Pulled from
  // profileData so the edit view shows the user's real name + contact,
  // not whatever the LLM happened to echo.
  const profileHeader = {
    full_name: profileData.full_name,
    phone: profileData.phone,
    email: profileData.email,
    location: profileData.location ?? null,
  };

  const handleGenerate = async (values: InputStepValues) => {
    setInputs(values);
    setLoading(true);
    setError(null);
    try {
      const r = await cvApi.generate(token, {
        job_title: values.jobTitle,
        company: values.company || undefined,
        job_description: values.jobDescription || undefined,
      });
      // Prefer the structured shape when the backend supplied it
      // (task #59 hybrid mode). Free-text parseGeneratedCv() is the
      // fallback for legacy responses where r.sections is null.
      const p = r.sections
        ? cvSectionsToParsed(r.sections, profileHeader)
        : parseGeneratedCv(r.content);
      setParsed(p);
      setOriginalParsed(p);
      setCvSections(r.sections ?? null);
      setOriginalCvSections(r.sections ?? null);
      setMeta({
        jobTitle: r.job_title,
        company: r.company ?? "",
        wordCount: r.word_count,
      });
      setStep("preview");
      // Bump history so the new generation appears at the top of the panel.
      setHistoryRefresh((n) => n + 1);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setLoading(false);
    }
  };

  const handleLoadFromHistory = async (id: string) => {
    setError(null);
    try {
      const detail = await cvApi.getGeneration(token, id);
      // Structured sections live in cv_generations.metadata.sections for
      // post-#59 rows; pre-#59 rows have only content text. Mirror the
      // generate path's preference order.
      const p = detail.sections
        ? cvSectionsToParsed(detail.sections, profileHeader)
        : parseGeneratedCv(detail.content);
      setParsed(p);
      setOriginalParsed(p);
      setCvSections(detail.sections ?? null);
      setOriginalCvSections(detail.sections ?? null);
      setMeta({
        jobTitle: detail.job_title,
        company: detail.company ?? "",
        wordCount: detail.word_count,
      });
      setInputs({
        jobTitle: detail.job_title,
        company: detail.company ?? "",
        jobDescription: "",
      });
      setStep("preview");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load that generation");
    }
  };

  if (!profileData.cv_uploaded) {
    return (
      <div className="card p-6">
        <div className="eyebrow mb-2">CV generator</div>
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          Upload your CV first — the generator tailors your existing CV to a target role.
        </p>
      </div>
    );
  }

  const showHistory = step === "input";

  return (
    <div className={`grid grid-cols-1 ${showHistory ? "lg:grid-cols-[1fr_280px]" : ""} gap-6`}>
      <div className="space-y-6 min-w-0">
        {step === "input" && (
          <InputStep
            initial={inputs}
            tierAllowed={tierAllowed}
            loading={loading}
            error={error}
            onSubmit={handleGenerate}
          />
        )}

        {step === "preview" && parsed && meta && (
          <PreviewStep
            parsed={parsed}
            cvSections={cvSections}
            template={template}
            setTemplate={setTemplate}
            meta={meta}
            onBack={() => setStep("input")}
            onEdit={() => setStep("edit")}
            onStartOver={startOver}
          />
        )}

        {step === "edit" && parsed && originalParsed && (
          <EditStep
            parsed={parsed}
            onChange={(next) => {
              // Edits invalidate the structured shape — they only flow into
              // the ParsedCV view. Drop structured so templates fall back
              // to the edited ParsedCV and the preview reflects edits.
              setParsed(next);
              setCvSections(null);
            }}
            onDone={() => setStep("preview")}
            onReset={() => {
              setParsed(originalParsed);
              setCvSections(originalCvSections);
            }}
          />
        )}
      </div>

      {showHistory && (
        <div className="space-y-6">
          <HistoryPanel
            token={token}
            refreshKey={historyRefresh}
            onLoad={handleLoadFromHistory}
          />
        </div>
      )}
    </div>
  );
}
