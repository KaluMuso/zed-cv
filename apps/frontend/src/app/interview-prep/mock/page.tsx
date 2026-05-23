"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";

import { InterviewPrepGate } from "@/app/interview-prep/_components/InterviewPrepGate";
import { useAuth } from "@/lib/auth";
import {
  bwanaInterview,
  matches,
  type MockInterviewAnswerResult,
} from "@/lib/api";
import { Button } from "@/components/ui/button";
import { notify } from "@/lib/toast";

interface ChatTurn {
  role: "bwana" | "user";
  text: string;
  starScore?: number;
  feedback?: string;
}

export default function MockInterviewPage() {
  return (
    <InterviewPrepGate nextPath="/interview-prep/mock">
      <MockInterviewContent />
    </InterviewPrepGate>
  );
}

function MockInterviewContent() {
  const { token } = useAuth();
  const [roles, setRoles] = useState<string[]>([]);
  const [roleChoice, setRoleChoice] = useState("");
  const [customRole, setCustomRole] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [questionNumber, setQuestionNumber] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(7);
  const [currentQuestion, setCurrentQuestion] = useState("");
  const [draft, setDraft] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [summary, setSummary] = useState<
    MockInterviewAnswerResult["final_summary"] | null
  >(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!token) return;
    matches
      .get(token)
      .then((data) => {
        const titles = new Set<string>();
        for (const m of data.matches) {
          const t = m.job?.title?.trim();
          if (t) titles.add(t);
        }
        setRoles([...titles].sort());
      })
      .catch(() => setRoles([]));
  }, [token]);

  const resolvedRole =
    roleChoice === "__other__" ? customRole.trim() : roleChoice;

  const startSession = useCallback(async () => {
    if (!token || !resolvedRole) return;
    setBusy(true);
    try {
      const res = await bwanaInterview.mockStart(token, resolvedRole);
      setSessionId(res.session_id);
      setQuestionNumber(res.question_number);
      setTotalQuestions(res.total_questions);
      setCurrentQuestion(res.question);
      setTurns([{ role: "bwana", text: res.question }]);
      setSummary(null);
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Could not start interview.");
    } finally {
      setBusy(false);
    }
  }, [token, resolvedRole]);

  const submitAnswer = useCallback(async () => {
    if (!token || !sessionId || !draft.trim() || busy) return;
    const answer = draft.trim();
    setDraft("");
    setTurns((prev) => [...prev, { role: "user", text: answer }]);
    setBusy(true);
    try {
      const res = await bwanaInterview.mockAnswer(token, sessionId, answer);
      const progress = res.progress;
      if (progress) {
        setTurns((prev) => [
          ...prev,
          {
            role: "bwana",
            text: `STAR ${progress.star_score}/10 — ${progress.feedback}`,
            starScore: progress.star_score,
            feedback: progress.feedback,
          },
        ]);
        setQuestionNumber(progress.question_number);
      }
      if (res.final_summary) {
        setSummary(res.final_summary);
        setCurrentQuestion("");
      } else if (res.next_question) {
        setCurrentQuestion(res.next_question);
        setQuestionNumber((n) => n + 1);
        setTurns((prev) => [...prev, { role: "bwana", text: res.next_question! }]);
      }
    } catch (err) {
      notify.error(err instanceof Error ? err.message : "Could not submit answer.");
    } finally {
      setBusy(false);
    }
  }, [token, sessionId, draft, busy]);

  return (
    <div className="max-w-3xl mx-auto px-6 py-10 md:py-14">
      <div className="mb-8">
        <div className="eyebrow mb-2">Bwana Interview</div>
        <h1 className="font-display text-4xl mb-2">Mock interview</h1>
        <p className="text-sm" style={{ color: "var(--muted)" }}>
          Seven STAR-style questions with feedback after each answer.
        </p>
      </div>

      {!sessionId ? (
        <div className="card p-6 space-y-4">
          <label className="block text-sm font-medium">Role</label>
          <select
            className="w-full rounded-lg border px-3 py-2 text-sm"
            style={{ borderColor: "var(--line)", background: "var(--surface)" }}
            value={roleChoice}
            onChange={(e) => setRoleChoice(e.target.value)}
          >
            <option value="">Select from your matches…</option>
            {roles.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
            <option value="__other__">Other (type below)</option>
          </select>
          {roleChoice === "__other__" && (
            <input
              type="text"
              className="w-full rounded-lg border px-3 py-2 text-sm"
              style={{ borderColor: "var(--line)", background: "var(--surface)" }}
              placeholder="e.g. Finance Manager"
              value={customRole}
              onChange={(e) => setCustomRole(e.target.value)}
            />
          )}
          <Button
            type="button"
            variant="primary"
            disabled={!resolvedRole || busy}
            onClick={() => void startSession()}
          >
            Start interview
          </Button>
        </div>
      ) : (
        <>
          <div className="text-xs mb-3" style={{ color: "var(--muted)" }}>
            Question {Math.min(questionNumber, totalQuestions)} of {totalQuestions}
            {resolvedRole ? ` · ${resolvedRole}` : ""}
          </div>
          <div
            className="card p-4 mb-4 min-h-[280px] max-h-[50vh] overflow-y-auto space-y-3"
            aria-live="polite"
          >
            {turns.map((t, i) => (
              <div
                key={`${i}-${t.role}`}
                className={`text-sm rounded-lg px-3 py-2 max-w-[90%] ${
                  t.role === "user" ? "ml-auto" : "mr-auto"
                }`}
                style={{
                  background:
                    t.role === "user" ? "var(--green-100)" : "var(--bg-2)",
                  color: "var(--ink-2)",
                }}
              >
                <span className="font-medium block mb-1">
                  {t.role === "user" ? "You" : "Bwana"}
                  {t.starScore != null ? ` · STAR ${t.starScore}/10` : ""}
                </span>
                {t.text}
              </div>
            ))}
          </div>

          {!summary && currentQuestion && (
            <div className="flex gap-2">
              <textarea
                className="flex-1 rounded-lg border px-3 py-2 text-sm min-h-[80px]"
                style={{ borderColor: "var(--line)", background: "var(--surface)" }}
                placeholder="Your answer…"
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                disabled={busy}
              />
              <Button
                type="button"
                variant="primary"
                disabled={!draft.trim() || busy}
                onClick={() => void submitAnswer()}
              >
                Send
              </Button>
            </div>
          )}

          {summary && (
            <div className="card p-6 mt-4 space-y-4">
              <h2 className="font-display text-2xl">Session summary</h2>
              <p className="text-sm">
                Overall STAR score:{" "}
                <strong>{summary.overall_score.toFixed(0)}/100</strong>
              </p>
              <div className="grid md:grid-cols-3 gap-4 text-sm">
                <div>
                  <h3 className="font-medium mb-2">Strengths</h3>
                  <ul className="list-disc pl-4 space-y-1" style={{ color: "var(--ink-2)" }}>
                    {summary.strengths.map((s) => (
                      <li key={s}>{s}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="font-medium mb-2">Improve</h3>
                  <ul className="list-disc pl-4 space-y-1" style={{ color: "var(--ink-2)" }}>
                    {summary.improvements.map((s) => (
                      <li key={s}>{s}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h3 className="font-medium mb-2">Practice</h3>
                  <ul className="list-disc pl-4 space-y-1" style={{ color: "var(--ink-2)" }}>
                    {summary.practice_areas.map((s) => (
                      <li key={s}>{s}</li>
                    ))}
                  </ul>
                </div>
              </div>
              <Link href="/interview-prep/history" className="btn btn-accent btn-sm inline-flex">
                View history
              </Link>
            </div>
          )}
        </>
      )}

      <div className="mt-8">
        <Link href="/interview-prep" className="text-sm" style={{ color: "var(--muted)" }}>
          ← Interview Prep hub
        </Link>
      </div>
    </div>
  );
}
