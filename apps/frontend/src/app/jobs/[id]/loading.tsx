/**
 * Next.js convention: shown via Suspense while the server fetches the job in
 * page.tsx. Shape mirrors JobDetailBody (avatar + title + meta strip + skills
 * + description) so there's no layout shift when the real content renders.
 */
export default function JobDetailLoading() {
  return (
    <article className="max-w-[820px] mx-auto px-2 sm:px-6 py-6 md:py-10">
      <div className="p-6 md:p-8">
        <div className="eyebrow mb-3" style={{ color: "var(--muted)" }}>
          Job Details
        </div>

        <div className="flex items-start gap-4 mb-6">
          <div className="skeleton rounded-full" style={{ width: 48, height: 48 }} />
          <div className="min-w-0 flex-1">
            <div className="skeleton h-9 md:h-10 w-3/4 mb-2" />
            <div className="skeleton h-4 w-1/2" />
          </div>
        </div>

        <div className="flex flex-wrap gap-x-5 gap-y-2 mb-6">
          <div className="skeleton h-3 w-24" />
          <div className="skeleton h-3 w-20" />
          <div className="skeleton h-3 w-28" />
        </div>

        <div className="mb-6">
          <div className="skeleton h-3 w-28 mb-3" />
          <div className="flex flex-wrap gap-1.5">
            <div className="skeleton h-6 w-16 rounded-md" />
            <div className="skeleton h-6 w-20 rounded-md" />
            <div className="skeleton h-6 w-14 rounded-md" />
            <div className="skeleton h-6 w-24 rounded-md" />
            <div className="skeleton h-6 w-18 rounded-md" />
          </div>
        </div>

        <div className="mb-8">
          <div className="skeleton h-3 w-24 mb-3" />
          <div className="space-y-2">
            <div className="skeleton h-4 w-full" />
            <div className="skeleton h-4 w-full" />
            <div className="skeleton h-4 w-11/12" />
            <div className="skeleton h-4 w-full" />
            <div className="skeleton h-4 w-10/12" />
            <div className="skeleton h-4 w-full" />
            <div className="skeleton h-4 w-9/12" />
          </div>
        </div>

        <div className="flex gap-3 py-3">
          <div className="skeleton h-10 flex-1 rounded-md" />
          <div className="skeleton h-10 w-12 rounded-md" />
        </div>
      </div>
    </article>
  );
}
