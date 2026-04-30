"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { matches as matchesApi, type MatchData } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { MatchScore } from "@/components/MatchScore";
import { SkillBadge } from "@/components/SkillBadge";
import { Icon } from "@/components/ui/Icon";
import { Avatar } from "@/components/ui/Avatar";
import { Counter } from "@/components/ui/Counter";
import Link from "next/link";

export default function MatchesPage() {
  const router = useRouter();
  const { token, isAuthenticated, isLoading: authLoading } = useAuth();
  const [data, setData] = useState<{
    matches: MatchData[];
    remaining_quota: number;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [scoreFilter, setScoreFilter] = useState(0);
  const [sort, setSort] = useState<"score" | "closing">("score");

  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated || !token) {
      router.push("/auth");
      return;
    }
    matchesApi
      .get(token)
      .then((d) => setData(d))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [token, isAuthenticated, authLoading, router]);

  if (loading || authLoading) {
    return (
      <div className="max-w-[1280px] mx-auto px-6 py-12">
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton h-32 w-full" />
          ))}
        </div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="max-w-[1280px] mx-auto px-6 py-20 text-center">
        <p style={{ color: "var(--muted)" }}>Could not load matches.</p>
      </div>
    );
  }

  // Apply filters
  let filtered = data.matches.filter((m) => m.score >= scoreFilter);
  if (sort === "score") {
    filtered = [...filtered].sort((a, b) => b.score - a.score);
  }

  const totalMatches = 25; // max for tier
  const used = totalMatches - data.remaining_quota;
  const usagePct = (used / totalMatches) * 100;

  return (
    <div className="max-w-[1280px] mx-auto px-6 py-8 md:py-12">
      {/* Header */}
      <div
        className="matches-header grid gap-8 items-start mb-10"
        style={{ gridTemplateColumns: "1.4fr 1fr" }}
      >
        <div>
          <div className="eyebrow mb-2">
            {new Date().toLocaleDateString("en-ZM", {
              weekday: "long",
              day: "numeric",
              month: "long",
              year: "numeric",
            })}
          </div>
          <h1
            className="font-display mb-4"
            style={{
              fontSize: "clamp(40px, 5.5vw, 72px)",
              letterSpacing: "-0.025em",
              lineHeight: 1,
            }}
          >
            Here are your{" "}
            <span className="italic" style={{ color: "var(--copper-500)" }}>
              top matches
            </span>
            .
          </h1>
          <p className="text-base" style={{ color: "var(--muted)" }}>
            <Counter to={filtered.length} /> roles scored against your CV.
            Tap any card to expand the breakdown.
          </p>
        </div>

        {/* Quota card */}
        <div className="card p-6">
          <div className="flex justify-between items-start">
            <div>
              <div className="eyebrow">This month</div>
              <div className="mt-2 font-display text-4xl leading-none">
                {used}
                <span
                  className="text-2xl"
                  style={{ color: "var(--muted)" }}
                >
                  {" "}
                  / {totalMatches}
                </span>
              </div>
              <div
                className="text-xs mt-1"
                style={{ color: "var(--muted)" }}
              >
                matches delivered
              </div>
            </div>
            <span className="tag tag-copper">
              <Icon name="zap" size={11} /> Starter
            </span>
          </div>
          <div
            className="mt-5 h-2 rounded-full overflow-hidden"
            style={{ background: "var(--bg-2)" }}
          >
            <div
              className="h-full rounded-full"
              style={{
                width: `${usagePct}%`,
                background:
                  "linear-gradient(90deg, var(--green-500), var(--copper-500))",
                transition: "width 1.4s cubic-bezier(0.2,0.7,0.2,1)",
              }}
            />
          </div>
          <div
            className="mt-3 flex justify-between text-xs"
            style={{ color: "var(--muted)" }}
          >
            <span>Resets next month</span>
            <Link
              href="/pricing"
              className="font-medium"
              style={{ color: "var(--green-700)" }}
            >
              Upgrade for K125/mo &rarr;
            </Link>
          </div>
        </div>
      </div>

      {/* Filter bar */}
      <div
        className="flex items-center justify-between flex-wrap gap-3 pb-4 mb-6"
        style={{ borderBottom: "1px solid var(--line)" }}
      >
        <div className="flex gap-2 flex-wrap">
          {[
            [0, "All"],
            [70, "70+"],
            [85, "85+ Strong"],
          ].map(([v, l]) => (
            <button
              key={String(v)}
              onClick={() => setScoreFilter(v as number)}
              className="btn btn-sm"
              style={{
                background:
                  scoreFilter === v ? "var(--green-700)" : "transparent",
                color: scoreFilter === v ? "#faf7f2" : "var(--ink-2)",
                border:
                  scoreFilter === v
                    ? "none"
                    : "1px solid var(--line-2)",
              }}
            >
              {l as string}
            </button>
          ))}
        </div>
        <div className="flex gap-2 items-center">
          <span
            className="font-mono text-[11px]"
            style={{ color: "var(--muted)" }}
          >
            SORT
          </span>
          {[
            ["score", "Score"],
            ["closing", "Closing soon"],
          ].map(([v, l]) => (
            <button
              key={v}
              onClick={() => setSort(v as "score" | "closing")}
              className="btn btn-sm"
              style={{
                background: sort === v ? "var(--bg-2)" : "transparent",
                color: "var(--ink-2)",
                border: "1px solid var(--line)",
                fontWeight: sort === v ? 600 : 400,
              }}
            >
              {l}
            </button>
          ))}
        </div>
      </div>

      {/* Match cards */}
      {data.matches.length === 0 ? (
        <div className="text-center py-20">
          <div
            className="w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center"
            style={{
              border: "2px dashed var(--line-2)",
              color: "var(--muted)",
            }}
          >
            <Icon name="target" size={24} />
          </div>
          <h3 className="font-display text-2xl mb-2">No matches yet</h3>
          <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
            Upload your CV to get started!
          </p>
          <Link href="/profile" className="btn btn-primary">
            Upload CV <Icon name="upload" size={14} />
          </Link>
        </div>
      ) : (
        <div className="flex flex-col gap-3.5">
          {filtered.map((match) => (
            <article key={match.id} className="card overflow-hidden">
              <div
                className="match-row p-5 sm:p-6 grid gap-6 items-center"
                style={{ gridTemplateColumns: "auto 1fr auto" }}
              >
                <MatchScore
                  score={match.score}
                  breakdown={{
                    vector: match.vector_score,
                    skill: match.skill_score,
                    bonus: match.bonus_score,
                  }}
                  size="lg"
                />

                <div className="min-w-0">
                  <div className="flex items-center gap-2.5 mb-2">
                    <Avatar name={match.job.company || "ZC"} size={28} />
                    <span
                      className="text-sm"
                      style={{ color: "var(--muted)" }}
                    >
                      {match.job.company || "Company"} &middot;{" "}
                      {match.job.location || "Zambia"}
                    </span>
                  </div>
                  <h3
                    className="font-display text-2xl md:text-3xl"
                    style={{ letterSpacing: "-0.01em", lineHeight: 1.1 }}
                  >
                    {match.job.title}
                  </h3>

                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {match.matched_skills.map((s) => (
                      <SkillBadge key={s} skill={s} matched />
                    ))}
                    {match.missing_skills.slice(0, 3).map((s) => (
                      <SkillBadge key={s} skill={s} matched={false} />
                    ))}
                  </div>
                </div>

                <div className="match-actions flex flex-col gap-2 items-end">
                  <button className="btn btn-primary btn-sm w-40">
                    Apply now <Icon name="external" size={13} />
                  </button>
                  <button
                    onClick={() =>
                      setExpanded(expanded === match.id ? null : match.id)
                    }
                    className="btn btn-ghost btn-sm w-40"
                  >
                    {expanded === match.id ? "Hide details" : "Why this match?"}{" "}
                    <Icon
                      name={
                        expanded === match.id
                          ? "chevronDown"
                          : "chevronRight"
                      }
                      size={13}
                    />
                  </button>
                </div>
              </div>

              {/* Expanded breakdown */}
              <div
                className="overflow-hidden transition-all duration-300"
                style={{
                  maxHeight: expanded === match.id ? 480 : 0,
                  borderTop:
                    expanded === match.id
                      ? "1px solid var(--line)"
                      : "none",
                  background: "var(--bg-2)",
                }}
              >
                <div
                  className="breakdown-grid p-6 grid gap-6"
                  style={{ gridTemplateColumns: "1fr 1fr" }}
                >
                  <div>
                    <div className="eyebrow mb-4">Score breakdown</div>
                    {[
                      ["Relevance", match.vector_score, "green"],
                      ["Skills overlap", match.skill_score, "copper"],
                      ["Bonus fit", match.bonus_score, "green"],
                    ].map(([label, val, tone]) => (
                      <div key={label as string} className="mb-3.5">
                        <div className="flex justify-between items-baseline mb-1">
                          <span className="text-sm font-medium">
                            {label as string}
                          </span>
                          <span
                            className="font-mono text-xs"
                            style={{ color: "var(--muted)" }}
                          >
                            {Math.round(val as number)}/100
                          </span>
                        </div>
                        <div
                          className="h-1.5 rounded-full overflow-hidden"
                          style={{ background: "var(--bg)" }}
                        >
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${val}%`,
                              background:
                                tone === "green"
                                  ? "var(--green-500)"
                                  : "var(--copper-500)",
                              transition: "width 800ms ease",
                            }}
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                  <div>
                    <div className="eyebrow mb-4">AI explanation</div>
                    {match.explanation && (
                      <p
                        className="text-sm leading-relaxed mb-4"
                        style={{ color: "var(--ink-2)" }}
                      >
                        {match.explanation}
                      </p>
                    )}
                    {match.missing_skills.length > 0 && (
                      <div
                        className="p-3.5 rounded-lg"
                        style={{
                          background: "var(--surface)",
                          border: "1px dashed var(--line-2)",
                        }}
                      >
                        <div
                          className="eyebrow mb-1.5"
                          style={{ color: "var(--copper-600)" }}
                        >
                          Skill gap
                        </div>
                        <div
                          className="text-sm font-mono"
                          style={{ color: "var(--ink-2)" }}
                        >
                          Missing: {match.missing_skills.join(", ")}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}

      {/* Upgrade CTA */}
      {data.matches.length > 0 && (
        <div
          className="upgrade-cta mt-12 p-8 rounded-xl grid gap-6 items-center"
          style={{
            gridTemplateColumns: "1fr auto",
            background: "var(--bg-2)",
            border: "1px solid var(--line)",
          }}
        >
          <div>
            <div className="eyebrow mb-1">Pro tip</div>
            <h3
              className="font-display text-2xl mb-1.5"
              style={{ letterSpacing: "-0.01em" }}
            >
              Want{" "}
              <span
                className="italic"
                style={{ color: "var(--copper-500)" }}
              >
                tailored CVs
              </span>{" "}
              per role?
            </h3>
            <p className="text-sm" style={{ color: "var(--muted)" }}>
              Professional tier rewrites your CV for each match — typically
              lifts callback rates by 2-3x.
            </p>
          </div>
          <Link href="/pricing" className="btn btn-accent">
            See pricing <Icon name="arrowRight" size={14} />
          </Link>
        </div>
      )}
    </div>
  );
}
