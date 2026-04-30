"use client";

import { useEffect, useState, useCallback } from "react";
import { jobs as jobsApi, type Job } from "@/lib/api";
import { JobCard } from "@/components/JobCard";
import { Icon } from "@/components/ui/Icon";
import { Counter } from "@/components/ui/Counter";

const ZAMBIAN_LOCATIONS = [
  "All Locations",
  "Lusaka",
  "Kitwe",
  "Ndola",
  "Livingstone",
  "Kabwe",
  "Chipata",
  "Solwezi",
  "Kasama",
  "Remote",
];

const SORT_OPTIONS = [
  { value: "relevance", label: "Relevance" },
  { value: "recent", label: "Most Recent" },
  { value: "closing", label: "Closing Soon" },
];

export default function JobsPage() {
  const [jobsList, setJobsList] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [location, setLocation] = useState("");
  const [sort, setSort] = useState("relevance");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await jobsApi.list({
        page,
        search: search || undefined,
        location: location || undefined,
      });
      setJobsList(res.jobs);
      setTotalPages(res.pages);
      setTotal(res.total);
    } catch {
      setJobsList([]);
    } finally {
      setLoading(false);
    }
  }, [page, search, location]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchJobs();
  };

  return (
    <div className="max-w-[1280px] mx-auto px-6 py-8 md:py-12">
      {/* Header */}
      <div className="mb-8">
        <div className="eyebrow mb-2">Browse opportunities</div>
        <h1
          className="font-display"
          style={{
            fontSize: "clamp(36px, 5vw, 56px)",
            letterSpacing: "-0.025em",
            lineHeight: 1,
          }}
        >
          <Counter to={total} /> open{" "}
          <span className="italic" style={{ color: "var(--copper-500)" }}>
            roles
          </span>
        </h1>
      </div>

      {/* Filter bar */}
      <form
        onSubmit={handleSearch}
        className="sticky top-[65px] z-30 -mx-6 px-6 py-4 mb-6 flex flex-col md:flex-row gap-3 items-stretch md:items-center"
        style={{
          background: "rgba(250,247,242,0.9)",
          backdropFilter: "blur(12px)",
          borderBottom: "1px solid var(--line)",
        }}
      >
        <div className="relative flex-1">
          <Icon
            name="search"
            size={16}
            className="absolute left-3.5 top-1/2 -translate-y-1/2"
          />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search jobs, skills, companies..."
            className="field pl-10"
            style={{ height: 44 }}
          />
        </div>

        <select
          value={location}
          onChange={(e) => {
            setLocation(e.target.value);
            setPage(1);
          }}
          className="field"
          style={{ width: "auto", minWidth: 160 }}
        >
          {ZAMBIAN_LOCATIONS.map((loc) => (
            <option key={loc} value={loc === "All Locations" ? "" : loc}>
              {loc}
            </option>
          ))}
        </select>

        <select
          value={sort}
          onChange={(e) => setSort(e.target.value)}
          className="field"
          style={{ width: "auto", minWidth: 140 }}
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        <button type="submit" className="btn btn-primary">
          <Icon name="search" size={16} /> Search
        </button>
      </form>

      {/* Results */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="skeleton h-28 w-full" />
          ))}
        </div>
      ) : jobsList.length === 0 ? (
        <div className="text-center py-20">
          <div
            className="w-16 h-16 mx-auto mb-4 rounded-2xl flex items-center justify-center"
            style={{
              border: "2px dashed var(--line-2)",
              color: "var(--muted)",
            }}
          >
            <Icon name="search" size={24} />
          </div>
          <h3
            className="font-display text-2xl mb-2"
            style={{ letterSpacing: "-0.01em" }}
          >
            No jobs found
          </h3>
          <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
            Try a different search or location filter.
          </p>
          <button
            onClick={() => {
              setSearch("");
              setLocation("");
              setPage(1);
            }}
            className="btn btn-ghost btn-sm"
          >
            Reset filters
          </button>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {jobsList.map((job) => (
              <JobCard
                key={job.id}
                title={job.title}
                company={job.company}
                location={job.location}
                qualityScore={job.quality_score}
                skills={job.skills}
                closingDate={job.closing_date}
                onClick={() => setSelectedJob(job)}
              />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex justify-center items-center gap-2 mt-10">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="btn btn-ghost btn-sm"
              >
                <Icon name="arrowLeft" size={14} /> Previous
              </button>
              <div className="flex gap-1">
                {Array.from({ length: Math.min(totalPages, 7) }, (_, i) => {
                  const pageNum = i + 1;
                  return (
                    <button
                      key={pageNum}
                      onClick={() => setPage(pageNum)}
                      className="btn btn-sm"
                      style={{
                        width: 36,
                        padding: 0,
                        background:
                          page === pageNum
                            ? "var(--green-700)"
                            : "transparent",
                        color:
                          page === pageNum ? "#faf7f2" : "var(--ink-2)",
                        borderColor:
                          page === pageNum
                            ? "var(--green-700)"
                            : "var(--line)",
                      }}
                    >
                      {pageNum}
                    </button>
                  );
                })}
              </div>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="btn btn-ghost btn-sm"
              >
                Next <Icon name="arrowRight" size={14} />
              </button>
            </div>
          )}
        </>
      )}

      {/* Job Drawer */}
      {selectedJob && (
        <>
          <div
            className="fixed inset-0 z-40"
            style={{ background: "rgba(0,0,0,0.4)", backdropFilter: "blur(4px)" }}
            onClick={() => setSelectedJob(null)}
          />
          <div
            className="fixed top-0 right-0 bottom-0 z-50 w-full max-w-[560px] overflow-y-auto scroll-thin"
            style={{
              background: "var(--surface)",
              borderLeft: "1px solid var(--line)",
              boxShadow: "var(--shadow-lg)",
              animation: "slideRight 300ms ease both",
            }}
          >
            <div className="p-6 md:p-8">
              <button
                onClick={() => setSelectedJob(null)}
                className="btn btn-ghost btn-sm mb-6"
              >
                <Icon name="x" size={16} /> Close
              </button>

              <div className="eyebrow mb-3">Job Details</div>
              <h2
                className="font-display text-3xl mb-2"
                style={{ letterSpacing: "-0.01em" }}
              >
                {selectedJob.title}
              </h2>
              <p className="text-sm mb-6" style={{ color: "var(--muted)" }}>
                {selectedJob.company || "Company not listed"} &middot;{" "}
                {selectedJob.location || "Location not specified"}
              </p>

              {/* Skills */}
              {selectedJob.skills.length > 0 && (
                <div className="mb-6">
                  <div className="eyebrow mb-3">Required Skills</div>
                  <div className="flex flex-wrap gap-1.5">
                    {selectedJob.skills.map((s) => (
                      <span key={s} className="tag tag-mono">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Description */}
              {selectedJob.description && (
                <div className="mb-6">
                  <div className="eyebrow mb-3">Description</div>
                  <p
                    className="text-sm leading-relaxed"
                    style={{ color: "var(--ink-2)" }}
                  >
                    {selectedJob.description}
                  </p>
                </div>
              )}

              {selectedJob.closing_date && (
                <div className="mb-8">
                  <div className="eyebrow mb-2">Closing Date</div>
                  <p className="text-sm font-mono" style={{ color: "var(--ink-2)" }}>
                    {new Date(selectedJob.closing_date).toLocaleDateString(
                      "en-ZM",
                      { day: "numeric", month: "long", year: "numeric" }
                    )}
                  </p>
                </div>
              )}

              <div className="flex gap-3">
                <button className="btn btn-primary flex-1">
                  Apply Now <Icon name="external" size={14} />
                </button>
                <button className="btn btn-ghost">
                  <Icon name="bookmark" size={16} />
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
