"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";

import { InterviewPrepGate } from "@/app/interview-prep/_components/InterviewPrepGate";
import { useAuth } from "@/lib/auth";
import {
  bwanaInterview,
  type AptitudePack,
  type AptitudePackResult,
  type AptitudeScoreResult,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { notify } from "@/lib/toast";

const PACKS: { id: AptitudePack; label: string; minutes: number }[] = [
  { id: "numerical", label: "Numerical Reasoning", minutes: 20 },
  { id: "verbal", label: "Verbal Reasoning", minutes: 20 },
  { id: "abstract", label: "Abstract Reasoning", minutes: 15 },
];

const STORAGE_KEY = "zedcv_aptitude_session";

interface SavedSession {
  pack: AptitudePack;
  questionIds: string[];
  questions: AptitudePackResult["questions"];
  answers: Record<string, string>;
  index: number;
  elapsedSeconds: number;
  timeLimitSeconds: number;
  runningSince: number | null;
}

function loadSaved(): SavedSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as SavedSession) : null;
  } catch {
    return null;
  }
}

function saveSession(session: SavedSession | null) {
  if (typeof window === "undefined") return;
  if (!session) {
    localStorage.removeItem(STORAGE_KEY);
    return;
  }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
}

export default function AptitudePage() {
  return (
    <InterviewPrepGate nextPath="/interview-prep/aptitude">
      <AptitudeContent />
    </InterviewPrepGate>
  );
}

function AptitudeContent() {
  const { token } = useAuth();
  const [pack, setPack] = useState<AptitudePack | null>(null);
  const [session, setSession] = useState<SavedSession | null>(null);
  const [result, setResult] = useState<AptitudeScoreResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    setSession(loadSaved());
  }, []);

  useEffect(() => {
    if (!session || session.runningSince == null || result) return;
    const id = window.setInterval(() => setTick((t) => t + 1), 1000);
    return () => window.clearInterval(id);
  }, [session, result]);

  const elapsed = useMemo(() => {
    if (!session) return 0;
    void tick;
    if (session.runningSince == null) return session.elapsedSeconds;
    return (
      session.elapsedSeconds +
      Math.floor((Date.now() - session.runningSince) / 1000)
    );
  }, [session, tick]);

  const remaining = session
    ? Math.max(0, session.timeLimitSeconds - elapsed)
    : 0;

  const startPack = useCallback(
    async (p: AptitudePack) => {
      if (!token) return;
      setBusy(true);
      setResult(null);
      try {
        const data = await bwanaInterview.aptitudePack(token, p);
        const fresh: SavedSession = {
          pack: p,
          questionIds: data.questions.map((q) => q.id),
          questions: data.questions,
          answers: {},
          index: 0,
          elapsedSeconds: 0,
          timeLimitSeconds: data.time_limit_seconds,
          runningSince: Date.now(),
        };
        setSession(fresh);
        setPack(p);
        saveSession(fresh);
      } catch (err) {
        notify.error(err instanceof Error ? err.message : "Could not load pack.");
      } finally {
        setBusy(false);
      }
    },
    [token],
  );

  const resumeSaved = () => {
    if (!session) return;
    setPack(session.pack);
    const resumed = { ...session, runningSince: Date.now() };
    setSession(resumed);
    saveSession(resumed);
  };

  const pauseSession = () => {
    if (!session || session.runningSince == null) return;
    const paused: SavedSession = {
      ...session,
      elapsedSeconds: elapsed,
      runningSince: null,
    };
    setSession(paused);
    saveSession(paused);
    notify.info("Progress saved — resume anytime.");
  };

  const selectOption = (value: string) => {
    if (!session) return;
    const q = session.questions[session.index];
    const nextAnswers = { ...session.answers, [q.id]: value };
    const nextIndex = session.index + 1;
    const next: SavedSession = {
      ...session,
      answers: nextAnswers,
      index: nextIndex,
      elapsedSeconds: elapsed,
      runningSince: session.runningSince,
    };
    setSession(next);
    saveSession(next);
  };

  const submitPack = useCallback(async () => {
    if (!token || !session) return;
    setBusy(true);
    try {
      const answers = session.questionIds.map((id) => ({
        question_id: id,
        value: session.answers[id] ?? "",
      }));
      const scored = await bwanaInterview.aptitudeScore(
        token,
        session.pack,
        answers,
        elapsed,
      );
      setResult(scored);
      saveSession(null);
      setSession(null);
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Could not submit pack.");
    } finally {
      setBusy(false);
    }
  }, [token, session, elapsed]);

  const formatTime = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${m}:${s.toString().padStart(2, "0")}`;
  };

  const saved = loadSaved();
  const showResume = saved && !session && !result;

  if (result) {
    return (
      <div className="max-w-xl mx-auto px-6 py-12">
        <h1 className="font-display text-3xl mb-4">Results</h1>
        <p className="text-sm mb-2">
          Score: <strong>{result.score}%</strong> ({result.correct_count}/
          {result.total_questions} correct)
        </p>
        <p className="text-sm mb-6" style={{ color: "var(--muted)" }}>
          Percentile vs Zambian benchmark (placeholder):{" "}
          <strong>{result.percentile.toFixed(1)}</strong>
        </p>
        <div
          className="h-4 rounded-full overflow-hidden mb-8"
          style={{ background: "var(--bg-2)" }}
          aria-hidden
        >
          <div
            className="h-full transition-all"
            style={{
              width: `${result.percentile}%`,
              background: "var(--green-600)",
            }}
          />
        </div>
        <div className="flex gap-3">
          <Button type="button" variant="outline" onClick={() => setResult(null)}>
            Try another pack
          </Button>
          <Link href="/interview-prep/history">
            <Button type="button" variant="primary">
              History
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  if (!session) {
    return (
      <div className="max-w-3xl mx-auto px-6 py-10">
        <h1 className="font-display text-4xl mb-2">Aptitude tests</h1>
        <p className="text-sm mb-8" style={{ color: "var(--muted)" }}>
          20 questions per pack. Timer runs while active; pause saves progress locally.
        </p>
        {showResume && saved && (
          <div className="card p-4 mb-6 flex flex-wrap items-center justify-between gap-3">
            <span className="text-sm">
              Paused {saved.pack} pack — question {saved.index + 1}/20
            </span>
            <Button type="button" variant="primary" size="sm" onClick={resumeSaved}>
              Resume
            </Button>
          </div>
        )}
        <div className="grid gap-4 md:grid-cols-3">
          {PACKS.map((p) => (
            <div key={p.id} className="card p-5">
              <h2 className="font-display text-lg mb-1">{p.label}</h2>
              <p className="text-xs mb-4" style={{ color: "var(--muted)" }}>
                20 questions · {p.minutes} min
              </p>
              <Button
                type="button"
                variant="outline"
                size="sm"
                disabled={busy}
                onClick={() => void startPack(p.id)}
              >
                Start
              </Button>
            </div>
          ))}
        </div>
        <Link href="/interview-prep" className="inline-block mt-8 text-sm" style={{ color: "var(--muted)" }}>
          ← Hub
        </Link>
      </div>
    );
  }

  const current = session.questions[session.index];
  const progress = ((session.index + 1) / 20) * 100;
  const allAnswered = session.index >= 20;

  return (
    <div className="max-w-2xl mx-auto px-6 py-10">
      <div className="flex justify-between text-sm mb-2">
        <span className="capitalize">{pack ?? session.pack}</span>
        <span>{formatTime(remaining)} left</span>
      </div>
      <div
        className="h-2 rounded-full mb-6 overflow-hidden"
        style={{ background: "var(--bg-2)" }}
      >
        <div
          className="h-full"
          style={{ width: `${progress}%`, background: "var(--green-600)" }}
        />
      </div>

      {!allAnswered && current && (
        <>
          <p className="text-xs mb-2" style={{ color: "var(--muted)" }}>
            Question {session.index + 1} of 20
          </p>
          <h2 className="text-lg mb-4">{current.question_text}</h2>
          <div className="space-y-2">
            {current.options.map((opt) => (
              <button
                key={opt.value}
                type="button"
                className="w-full text-left rounded-lg border px-4 py-3 text-sm hover:border-[var(--green-600)]"
                style={{
                  borderColor:
                    session.answers[current.id] === opt.value
                      ? "var(--green-600)"
                      : "var(--line)",
                }}
                onClick={() => selectOption(opt.value)}
              >
                <span className="font-medium mr-2">{opt.label}</span>
                {opt.value !== opt.label ? opt.value : ""}
              </button>
            ))}
          </div>
        </>
      )}

      <div className="flex flex-wrap gap-3 mt-8">
        <Button type="button" variant="ghost" onClick={pauseSession}>
          Submit and exit
        </Button>
        <Button
          type="button"
          variant="primary"
          disabled={busy || session.index < 20}
          onClick={() => void submitPack()}
        >
          Submit pack
        </Button>
      </div>
    </div>
  );
}
