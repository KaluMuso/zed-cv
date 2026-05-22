# ZedApply Design System (Bucket 0)

Foundation tokens and patterns for the Phase 3 visual refresh. All UI work in buckets 1–11 should consume these primitives — do not invent parallel color or motion systems.

## Color palette

| Token | Light | Dark class | Meaning |
| --- | --- | --- | --- |
| `primary-500` | `#0E5C3A` | — | Brand deep green — CTAs, links, focus rings |
| `primary-foreground` | `#FAFAF7` | — | Text on primary buttons |
| `accent-500` | `#D97706` | — | Highlights, deadlines, premium cues |
| `surface` | `#FAFAF7` | `surface-dark` `#0C0D0C` | Page background |
| `surface-elevated` | `#FFFFFF` | `surface-dark-elevated` `#161816` | Cards, inputs, toasts |
| `ink` | `#0F172A` | `ink-dark` `#F8FAFC` | Body text (≥4.5:1 on surface) |
| `ink-muted` | `#52525B` | `ink-dark-muted` `#A1A1AA` | Secondary text |
| `border` | `#E5E5DB` | `border-dark` `#1F2937` | Dividers, outlines |
| `success-500` | `#16A34A` | — | Saved, confirmed, positive state |
| `warning-500` | `#F59E0B` | — | Closing ≤7 days |
| `danger-500` | `#DC2626` | — | Closing ≤3 days, destructive actions |

**Do not** use `text-green-*`, `text-emerald-*`, or `bg-zinc-*` for semantic status — use `success`, `warning`, or `danger`.

## Typography

| Utility | Size | Use |
| --- | --- | --- |
| `text-body` | 15px mobile / 16px desktop | Default body (`globals.css` + `md:` breakpoint) |
| `text-display-sm` … `text-display-xl` | Serif display scale | Marketing headings |
| `font-serif` | Crimson Pro stack | Headlines |
| `font-sans` | Inter stack | UI chrome |
| `font-mono` | JetBrains Mono | Eyebrows, codes |

## Spacing

Use **Tailwind core spacing only** (`p-4`, `gap-6`, `mt-8`, etc.). No arbitrary values like `p-3.5` or `text-[15px]`.

Mobile-first layout at **380px** minimum width. Interactive targets: **`min-h-11 min-w-11`** (44px) on touch breakpoints.

## Motion

| Token | Value | Use |
| --- | --- | --- |
| `duration-fast` | 150ms | Micro feedback |
| `duration-base` | 200ms | Buttons, hovers |
| `duration-slow` | 320ms | Page enter, fade-up |
| `ease-out-soft` | cubic-bezier(0.22, 0.61, 0.36, 1) | Entrances |
| `ease-spring` | cubic-bezier(0.34, 1.56, 0.64, 1) | Scale-in |
| `animate-fade-up` | 320ms | Empty states, reveals |
| `animate-shimmer` | 2s | Skeleton loading |
| `animate-float` | 6s | Hero `FloatingCard` |

**Page transitions:** `PageTransition` via `RouteTransitionShell` on all routes except `/admin/*`.

**Framer Motion:** route orchestration only — not for static styled boxes.

## Shadows & radius

- Shadows: `shadow-soft`, `shadow-card`, `shadow-raised`, `shadow-ring`
- Radius: `rounded-sm` (6px), `rounded-md` (10px), `rounded-lg` (16px), `rounded-xl` (24px)

## When to use what

```tsx
// Primary CTA
<Button variant="primary">Get matched</Button>

// Destructive
<Button variant="destructive">Delete account</Button>

// Status pill — job closing soon
<Pill variant="warning">Closes in 5 days</Pill>

// Toast — always via notify (see docs/toast_system.md)
notify.saved();
notify.error("Something went wrong");

// Hero float
<FloatingCard delay>{children}</FloatingCard>
```

## Forbidden patterns

- Literal hex/rgb in components (only in `tailwind.config.ts`)
- `style={{ color: '#...' }}` for static colors
- `transition-[200ms]` — use `duration-base`
- Hover-only affordances without a tap/keyboard equivalent
- `text-emerald-500` / `bg-green-600` for status — use semantic tokens
- Second toast library or ad-hoc `alert()`

## Source of truth

- Tokens: `apps/frontend/tailwind.config.ts`
- Global body: `apps/frontend/src/app/globals.css`
- Primitives: `apps/frontend/src/components/ui/*`, `apps/frontend/src/components/shared/*`
