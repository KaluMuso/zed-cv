import Link from "next/link";
import { Icon } from "@/components/ui/Icon";
import { surfaceCardClass } from "@/lib/cn-ui";
import { cn } from "@/lib/utils";

const TRUST_ITEMS = [
  {
    icon: "shield" as const,
    title: "Encrypted & private",
    body: "CV data encrypted in transit and at rest. We never sell your CV to employers.",
  },
  {
    icon: "whatsapp" as const,
    title: "WhatsApp-native",
    body: "Daily match digests and OTP sign-in — built for how Zambia actually hires.",
  },
  {
    icon: "zap" as const,
    title: "Transparent scoring",
    body: "Every match shows skill overlap, semantic fit, and local signals — not a black box.",
  },
] as const;

const PLACEHOLDER_LOGOS = [
  "NGO partners",
  "Zambian employers",
  "Job boards",
  "Career centres",
] as const;

const TESTIMONIALS = [
  {
    quote:
      "I stopped scrolling five job sites. ZedApply surfaces roles that actually fit my CV.",
    name: "Placeholder — Lusaka",
    role: "Finance professional",
  },
  {
    quote:
      "The WhatsApp digest means I never miss a closing date. Worth upgrading for tailored CVs.",
    name: "Placeholder — Kitwe",
    role: "Engineering graduate",
  },
] as const;

/** Optional verified logo — pass `src` only for assets you are licensed to display. */
export type TrustLogo = {
  name: string;
  src?: string;
  href?: string;
};

export function TrustSection({
  className,
  logos,
}: {
  className?: string;
  /** Real logo URLs when marketing provides them; otherwise category placeholders */
  logos?: TrustLogo[];
}) {
  const logoItems: TrustLogo[] =
    logos ??
    PLACEHOLDER_LOGOS.map((name) => ({
      name,
    }));

  return (
    <section className={cn("py-12 sm:py-16 md:py-20", className)} aria-labelledby="trust-heading">
      <div className="max-w-[1280px] mx-auto px-5 sm:px-6">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <p className="eyebrow mb-2">Trust</p>
          <h2 id="trust-heading" className="type-h2 text-foreground">
            Built for Zambian professionals
          </h2>
          <p className="type-body mt-3 text-muted-foreground">
            Security, transparency, and local delivery — see our{" "}
            <Link href="/security" className="underline" style={{ color: "var(--green-700)" }}>
              security overview
            </Link>
            .
          </p>
        </div>

        <ul className="grid gap-4 sm:grid-cols-3 mb-12">
          {TRUST_ITEMS.map((item) => (
            <li key={item.title} className={cn(surfaceCardClass, "p-5 sm:p-6")}>
              <Icon name={item.icon} size={22} className="text-primary mb-3" />
              <h3 className="type-card-title mb-1 text-foreground">{item.title}</h3>
              <p className="type-caption m-0">{item.body}</p>
            </li>
          ))}
        </ul>

        <div
          className={cn(surfaceCardClass, "p-6 sm:p-8 mb-10")}
          aria-label="Organizations using ZedApply"
        >
          <p className="type-section-title text-center mb-4">Trusted by teams across Zambia</p>
          <div className="flex flex-wrap justify-center gap-3">
            {logoItems.map((logo) => {
              const inner = logo.src ? (
                // eslint-disable-next-line @next/next/no-img-element -- marketing URLs vary by deploy
                <img
                  src={logo.src}
                  alt={logo.name}
                  width={120}
                  height={40}
                  className="h-8 w-auto object-contain"
                  loading="lazy"
                  decoding="async"
                />
              ) : (
                <span className="text-xs font-medium text-muted-foreground">{logo.name}</span>
              );
              const className =
                "inline-flex min-h-11 items-center justify-center rounded-full border border-border px-4 py-2 bg-muted/30";
              if (logo.href && logo.src) {
                return (
                  <a
                    key={logo.name}
                    href={logo.href}
                    className={className}
                    rel="noopener noreferrer"
                    target="_blank"
                  >
                    {inner}
                  </a>
                );
              }
              return (
                <span key={logo.name} className={className}>
                  {inner}
                </span>
              );
            })}
          </div>
          {!logos?.some((l) => l.src) ? (
            <p className="text-center text-xs mt-4" style={{ color: "var(--muted)" }}>
              Replace with verified customer logos when available.
            </p>
          ) : null}
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          {TESTIMONIALS.map((t) => (
            <blockquote
              key={t.name}
              className={cn(surfaceCardClass, "p-5 sm:p-6")}
              style={{ borderLeft: "3px solid var(--copper-500)" }}
            >
              <p className="type-body italic" style={{ color: "var(--ink-2)" }}>
                &ldquo;{t.quote}&rdquo;
              </p>
              <footer className="mt-4 type-caption">
                <strong style={{ color: "var(--ink)" }}>{t.name}</strong>
                <span> · {t.role}</span>
              </footer>
            </blockquote>
          ))}
        </div>

        <div className="mt-10 text-center">
          <Link
            href="/employer"
            className="inline-flex min-h-11 items-center text-sm font-medium hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500/30 rounded-sm px-1"
            style={{ color: "var(--green-700)" }}
          >
            Hiring in Zambia? Explore the employer portal →
          </Link>
        </div>
      </div>
    </section>
  );
}
