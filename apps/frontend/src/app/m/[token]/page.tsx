import type { Metadata } from "next";
import Link from "next/link";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ??
  "https://api.zedapply.com";

type PublicMatchCard = {
  title: string;
  company: string | null;
  location: string | null;
  score: number;
  matched_skills_count: number;
  top_matched_skills: string[];
  sender_first_name: string | null;
  sender_referral_code: string | null;
  created_at: string | null;
};

async function fetchCard(token: string): Promise<PublicMatchCard | null> {
  try {
    const res = await fetch(`${API_BASE}/api/v1/match-cards/${encodeURIComponent(token)}`, {
      // Cache briefly so WhatsApp/Facebook's preview crawlers don't get rate-limited.
      // 60s is short enough that share counts and view tracking stay close to live.
      next: { revalidate: 60 },
    });
    if (!res.ok) return null;
    return (await res.json()) as PublicMatchCard;
  } catch {
    return null;
  }
}

type Props = {
  params: Promise<{ token: string }>;
};

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { token } = await params;
  const card = await fetchCard(token);
  if (!card) {
    return {
      title: "Match card | ZedApply",
      description: "Personalized job matches for your CV on ZedApply.",
    };
  }
  const who = card.sender_first_name ? `${card.sender_first_name}'s` : "A";
  const titleLine = `${card.score}% match for ${card.title} via ZedApply`;
  const desc = card.sender_first_name
    ? `${card.sender_first_name} found this match on ZedApply. Upload your CV and AI will find roles like this for you in 30 seconds.`
    : `${who} match on ZedApply. Upload your CV and AI will find roles like this for you in 30 seconds.`;
  return {
    title: titleLine,
    description: desc,
    openGraph: {
      title: titleLine,
      description: desc,
      type: "website",
      siteName: "ZedApply",
    },
    twitter: {
      card: "summary_large_image",
      title: titleLine,
      description: desc,
    },
  };
}

export default async function MatchCardPage({ params }: Props) {
  const { token } = await params;
  const card = await fetchCard(token);

  if (!card) {
    return (
      <div
        className="min-h-screen flex items-center justify-center p-6"
        style={{ background: "var(--surface)", color: "var(--ink)" }}
      >
        <div className="max-w-md text-center space-y-4">
          <h1 className="font-display text-2xl">Match link no longer available</h1>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            This shared link may have expired or the match was removed.
          </p>
          <Link
            href="/"
            className="inline-flex items-center justify-center rounded-md px-4 py-2 text-sm font-medium"
            style={{
              background: "var(--ink)",
              color: "var(--surface)",
            }}
          >
            Get personal job matches on ZedApply
          </Link>
        </div>
      </div>
    );
  }

  const signupHref = card.sender_referral_code
    ? `/auth?ref=${encodeURIComponent(card.sender_referral_code)}&utm_source=match_share`
    : `/auth?utm_source=match_share`;

  const heroSubtitle = card.sender_first_name
    ? `${card.sender_first_name} matched this on ZedApply`
    : "Shared from ZedApply";

  return (
    <div
      className="min-h-screen flex items-center justify-center p-6"
      style={{ background: "var(--surface)", color: "var(--ink)" }}
    >
      <div className="max-w-md w-full">
        <div
          className="rounded-2xl border p-6 md:p-8 shadow-sm"
          style={{
            background: "linear-gradient(180deg, var(--copper-100, rgba(255,182,109,.12)) 0%, var(--surface) 60%)",
            borderColor: "var(--line, rgba(0,0,0,.08))",
          }}
        >
          <p
            className="text-[11px] font-medium uppercase tracking-[0.2em] mb-2"
            style={{ color: "var(--muted)" }}
          >
            {heroSubtitle}
          </p>
          <h1
            className="font-display"
            style={{ fontSize: "clamp(22px, 4vw, 28px)", lineHeight: 1.15, letterSpacing: "-0.01em" }}
          >
            {card.title}
          </h1>
          {card.company ? (
            <p
              className="text-sm mt-1"
              style={{ color: "var(--muted)" }}
            >
              {card.company}
              {card.location ? ` · ${card.location}` : ""}
            </p>
          ) : null}

          <div className="mt-6 mb-6 flex items-baseline gap-2">
            <span
              className="font-display"
              style={{
                fontSize: "clamp(48px, 9vw, 64px)",
                lineHeight: 1,
                color: "var(--copper-500, #C46B3D)",
              }}
            >
              {card.score}%
            </span>
            <span className="text-sm" style={{ color: "var(--muted)" }}>
              match score
            </span>
          </div>

          {card.top_matched_skills.length > 0 ? (
            <div className="mb-6">
              <p
                className="text-[11px] font-medium uppercase tracking-[0.15em] mb-2"
                style={{ color: "var(--muted)" }}
              >
                Top matched skills
              </p>
              <div className="flex flex-wrap gap-1.5">
                {card.top_matched_skills.map((skill) => (
                  <span
                    key={skill}
                    className="rounded-full px-2.5 py-0.5 text-xs font-medium"
                    style={{
                      background: "color-mix(in srgb, var(--green-500, #2F7D3A) 12%, transparent)",
                      color: "var(--green-700, #1F5C2A)",
                    }}
                  >
                    {skill}
                  </span>
                ))}
                {card.matched_skills_count > 3 ? (
                  <span
                    className="text-xs self-center"
                    style={{ color: "var(--muted)" }}
                  >
                    +{card.matched_skills_count - 3} more
                  </span>
                ) : null}
              </div>
            </div>
          ) : null}

          <Link
            href={signupHref}
            className="inline-flex w-full items-center justify-center rounded-md px-4 py-3 text-sm font-semibold transition-colors"
            style={{
              background: "var(--copper-500, #C46B3D)",
              color: "#fff",
            }}
          >
            Get matches like this for your CV
          </Link>
          <p
            className="text-xs text-center mt-3"
            style={{ color: "var(--muted)" }}
          >
            Free signup. AI matches you to Zambian jobs in 30 seconds.
          </p>
        </div>

        <p
          className="text-center text-xs mt-6"
          style={{ color: "var(--muted)" }}
        >
          ZedApply — personal job matches by AI, delivered on WhatsApp.
        </p>
      </div>
    </div>
  );
}
