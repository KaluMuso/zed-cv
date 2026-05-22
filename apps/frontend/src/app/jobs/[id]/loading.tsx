/**
 * Next.js convention: shown via Suspense while the server fetches the job in
 * page.tsx. Shape mirrors JobDetailBody (avatar + title + meta strip + skills
 * + description) so there's no layout shift when the real content renders.
 */
export default function JobDetailLoading() {
  return (
    <article className="max-w-6xl mx-auto px-2 sm:px-6 py-6 md:py-10">
      <div className="p-6 md:p-8">
        <div className="flex items-start gap-4 mb-4">
          <div className="skeleton rounded-full shrink-0" style={{ width: 56, height: 56 }} />
          <div className="min-w-0 flex-1">
            <div className="skeleton h-4 w-32 mb-2" />
            <div className="skeleton h-9 md:h-10 w-3/4" />
          </div>
        </div>

        <div className="flex flex-wrap gap-2 mb-8">
          <div className="skeleton h-7 w-28 rounded-full" />
          <div className="skeleton h-7 w-24 rounded-full" />
          <div className="skeleton h-7 w-20 rounded-full" />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_300px] gap-8">
          <div className="order-2 lg:order-1 space-y-6">
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="skeleton h-10 flex-1 rounded-md" />
              <div className="skeleton h-10 flex-1 rounded-md" />
              <div className="skeleton h-10 flex-1 rounded-md" />
            </div>
            <div className="space-y-2">
              <div className="skeleton h-3 w-28 mb-3" />
              <div className="skeleton h-4 w-full" />
              <div className="skeleton h-4 w-full" />
              <div className="skeleton h-4 w-10/12" />
            </div>
          </div>
          <div className="order-1 lg:order-2">
            <div className="skeleton h-80 w-full rounded-2xl" />
          </div>
        </div>
      </div>
    </article>
  );
}
