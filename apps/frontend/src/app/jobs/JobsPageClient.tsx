"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import {
  jobs as jobsApi,
  savedJobs,
  type Job,
  type EmploymentType,
  type WorkArrangement,
} from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { JobCard } from "@/components/JobCard";
import { Icon } from "@/components/ui/Icon";
import { isJobHiddenFromUserFeed } from "@/lib/isJobHiddenFromUserFeed";
import { Counter } from "@/components/ui/Counter";
import { Pagination } from "@/components/ui/Pagination";

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

// task #60: new structural filters. Mirrors the EmploymentType /
// WorkArrangement enums on the backend (apps/backend/app/schemas/jobs.py).
// "All" maps to the empty string which the API client drops from the
// query string entirely.
const EMPLOYMENT_TYPE_OPTIONS: { value: "" | EmploymentType; label: string }[] = [
  { value: "", label: "Any type" },
  { value: "full_time", label: "Full time" },
  { value: "part_time", label: "Part time" },
  { value: "contract", label: "Contract" },
  { value: "freelance", label: "Freelance" },
  { value: "internship", label: "Internship" },
  { value: "temporary", label: "Temporary" },
];

const WORK_ARRANGEMENT_OPTIONS: { value: "" | WorkArrangement; label: string }[] = [
  { value: "", label: "Any setup" },
  { value: "remote", label: "Remote" },
  { value: "hybrid", label: "Hybrid" },
  { value: "on_site", label: "On-site" },
];

// Toggle for the structural-filter dropdowns. As of 2026-05-19 every
// active job in the DB has NULL for both employment_type and
// work_arrangement (310/310 rows), so the dropdowns just guarantee a
// zero-result page for any user who touches them. Flip these to `true`
// once Path B (scraper + admin-wizard backfill that populates the
// columns) ships, then this flag can be removed entirely.
const FILTERS_AVAILABLE = {
  employmentType: true,
  workArrangement: true,
} as const;

// Curated chip-row of skills most commonly tagged on Zambian listings.
// Picking from existing data rather than fetching a /skills/top endpoint
// keeps this slice contained — chips that resolve to nothing simply
// short-circuit on the backend (already handled in jobs.list filter
// logic). When we have analytics on which chips actually filter to
// usable results, replace this with a data-driven list. The backend
// `skills_aliases` table also covers fuzzy matches like "reactjs" →
// "react", so a single chip catches several spellings.
const POPULAR_SKILLS = [
  "accounting",
  "sales",
  "marketing",
  "administration",
  "finance",
  "human resources",
  "procurement",
  "logistics",
  "driving",
  "teaching",
  "nursing",
  "engineering",
  "it",
  "construction",
  "agriculture",
  "mining",
  "ngo",
  "customer service",
  "project management",
  "data analysis",
];

export default function JobsPageClient() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { token } = useAuth();

  const [savedJobIds, setSavedJobIds] = useState<Set<string>>(() => new Set());

  const [jobsList, setJobsList] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  // searchInput = what the user types; searchQuery = debounced version that
  // actually hits the API. This avoids spamming the backend on every keystroke.
  const [searchInput, setSearchInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [location, setLocation] = useState("");
  const [selectedSkills, setSelectedSkills] = useState<string[]>([]);
  const [sort, setSort] = useState<"relevance" | "recent" | "closing">("recent");
  // task #60: structural filters. Both default to "" (no filter); the
  // API client drops empty values from the query string entirely so the
  // /jobs response is unchanged for users who don't engage with them.
  const [employmentType, setEmploymentType] = useState<"" | EmploymentType>("");
  const [workArrangement, setWorkArrangement] = useState<"" | WorkArrangement>("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const urlHydratedRef = useRef(false);
  const lastUrlSyncRef = useRef("");

  const syncFiltersToUrl = process.env.VITEST === undefined;

  // Hydrate filter state from URL (preserves shareable /jobs?q=… links).
  useEffect(() => {
    if (!syncFiltersToUrl || urlHydratedRef.current || !searchParams) return;
    const q = searchParams.get("q") ?? "";
    const loc = searchParams.get("location") ?? "";
    const sortParam = searchParams.get("sort");
    const pageParam = searchParams.get("page");
    setSearchInput(q);
    setSearchQuery(q);
    setLocation(loc);
    if (
      sortParam === "relevance" ||
      sortParam === "recent" ||
      sortParam === "closing"
    ) {
      setSort(sortParam);
    }
    const parsedPage = pageParam ? Number.parseInt(pageParam, 10) : 1;
    if (Number.isFinite(parsedPage) && parsedPage > 0) {
      setPage(parsedPage);
    }
    urlHydratedRef.current = true;
  }, [searchParams]);

  // Sync filters → URL.
  useEffect(() => {
    if (!syncFiltersToUrl || !urlHydratedRef.current) return;
    const sp = new URLSearchParams(searchParams?.toString() ?? "");
    if (searchQuery) sp.set("q", searchQuery);
    else sp.delete("q");
    if (location) sp.set("location", location);
    else sp.delete("location");
    if (sort !== "recent") sp.set("sort", sort);
    else sp.delete("sort");
    if (page > 1) sp.set("page", String(page));
    else sp.delete("page");
    const next = sp.toString();
    if (next === lastUrlSyncRef.current) return;
    lastUrlSyncRef.current = next;
    router.replace(next ? `${pathname}?${next}` : pathname, { scroll: false });
  }, [searchQuery, location, sort, page, pathname, router, searchParams]);

  useEffect(() => {
    if (!token) {
      setSavedJobIds(new Set());
      return;
    }
    let cancelled = false;
    savedJobs
      .list(token)
      .then((res) => {
        if (!cancelled) setSavedJobIds(new Set(res.jobs.map((j) => j.id)));
      })
      .catch(() => {
        if (!cancelled) setSavedJobIds(new Set());
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  // Debounce searchInput → searchQuery (300ms). Page reset to 1 when the
  // committed query changes so the user doesn't get a confusing "page 5 of
  // 1" state after filtering down.
  useEffect(() => {
    const t = setTimeout(() => {
      setSearchQuery(searchInput);
      setPage(1);
    }, 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    try {
      const res = await jobsApi.list({
        page,
        search: searchQuery || undefined,
        location: location || undefined,
        sort,
        skills: selectedSkills.length > 0 ? selectedSkills : undefined,
        employment_type: employmentType ? [employmentType] : undefined,
        work_arrangement: workArrangement ? [workArrangement] : undefined,
      });
      setJobsList(res.jobs.filter((j) => !isJobHiddenFromUserFeed(j.closing_date)));
      setTotalPages(res.pages);
      setTotal(res.total);
    } catch {
      setJobsList([]);
    } finally {
      setLoading(false);
    }
  }, [page, searchQuery, location, sort, selectedSkills, employmentType, workArrangement]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  // Legacy share links used ?j=<id> on /jobs — redirect to the standalone page.
  const legacyDrawerJobId = searchParams?.get("j") ?? null;
  useEffect(() => {
    if (!legacyDrawerJobId || !urlHydratedRef.current) return;
    router.replace(`/jobs/${legacyDrawerJobId}`);
  }, [legacyDrawerJobId, router]);

  const hasActiveFilters =
    Boolean(searchQuery || searchInput || location) ||
    sort !== "recent" ||
    selectedSkills.length > 0 ||
    Boolean(employmentType || workArrangement);

  const resetFilters = () => {
    setSearchInput("");
    setSearchQuery("");
    setLocation("");
    setSort("recent");
    setSelectedSkills([]);
    setEmploymentType("");
    setWorkArrangement("");
    setPage(1);
  };

  const toggleSkill = (skill: string) => {
    setSelectedSkills((prev) =>
      prev.includes(skill) ? prev.filter((s) => s !== skill) : [...prev, skill]
    );
    setPage(1);
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
      {/* Filter bar — search is debounced (300ms); no submit button. */}
      <div
        className="sticky top-[65px] z-30 -mx-6 px-6 py-4 mb-6 flex flex-col md:flex-row gap-3 items-stretch md:items-center dark:bg-background/90 dark:border-border"
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
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                setSearchQuery(searchInput);
                setPage(1);
              }
            }}
            placeholder="Search jobs, skills, companies..."
            className="field pl-10"
            style={{ height: 44 }}
            aria-label="Search jobs"
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
          aria-label="Filter by location"
        >
          {ZAMBIAN_LOCATIONS.map((loc) => (
            <option key={loc} value={loc === "All Locations" ? "" : loc}>
              {loc}
            </option>
          ))}
        </select>

        <select
          value={sort}
          onChange={(e) => {
            setSort(e.target.value as "relevance" | "recent" | "closing");
            setPage(1);
          }}
          className="field"
          style={{ width: "auto", minWidth: 140 }}
          aria-label="Sort jobs"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        {/* task #60: employment type + work arrangement filters.
            Hidden today via FILTERS_AVAILABLE because the columns are
            100% NULL in the active-jobs corpus — selecting anything
            here would just give the user a zero-result page. State
            stays at the default empty string, so the API client drops
            the params from the request entirely. */}
        {FILTERS_AVAILABLE.employmentType && (
          <select
            value={employmentType}
            onChange={(e) => {
              setEmploymentType(e.target.value as "" | EmploymentType);
              setPage(1);
            }}
            className="field"
            style={{ width: "auto", minWidth: 140 }}
            aria-label="Filter by employment type"
          >
            {EMPLOYMENT_TYPE_OPTIONS.map((opt) => (
              <option key={opt.value || "any-type"} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        )}

        {FILTERS_AVAILABLE.workArrangement && (
          <select
            value={workArrangement}
            onChange={(e) => {
              setWorkArrangement(e.target.value as "" | WorkArrangement);
              setPage(1);
            }}
            className="field"
            style={{ width: "auto", minWidth: 140 }}
            aria-label="Filter by work arrangement"
          >
            {WORK_ARRANGEMENT_OPTIONS.map((opt) => (
              <option key={opt.value || "any-setup"} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        )}

        <button
          type="button"
          className="btn btn-ghost dark:text-foreground dark:border-border dark:hover:bg-muted"
          disabled={!hasActiveFilters}
          onClick={resetFilters}
        >
          <Icon name="x" size={14} /> Clear filters
        </button>
      </div>

      {/* Skills chip row — single-click filter by common Zambian job
          areas. Selected chips are echoed back to the backend's
          `?skills=csv` filter (skill_aliases handles fuzzy spellings).
          A horizontal scroll on mobile keeps the row inline rather
          than wrapping into a wall of chips on narrow viewports. */}
      <div
        className="mb-6 flex gap-1.5 overflow-x-auto scroll-thin pb-1"
        style={{ scrollbarWidth: "thin" }}
        aria-label="Filter by skill"
      >
        {selectedSkills.length > 0 && (
          <button
            onClick={() => {
              setSelectedSkills([]);
              setPage(1);
            }}
            className="tag tag-mono shrink-0"
            style={{
              cursor: "pointer",
              borderColor: "var(--copper-500)",
              color: "var(--copper-600)",
            }}
            type="button"
            aria-label="Clear all skill filters"
          >
            <Icon name="x" size={10} /> Clear ({selectedSkills.length})
          </button>
        )}
        {POPULAR_SKILLS.map((skill) => {
          const active = selectedSkills.includes(skill);
          return (
            <button
              key={skill}
              onClick={() => toggleSkill(skill)}
              className={`tag tag-mono shrink-0 ${active ? "tag-green" : ""}`}
              style={{ cursor: "pointer", textTransform: "capitalize" }}
              type="button"
              aria-pressed={active}
            >
              {active && <Icon name="check" size={10} />}
              {skill}
            </button>
          );
        })}
      </div>

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
            {searchQuery || location || employmentType || workArrangement
              ? "No jobs match your filters"
              : "No jobs are open right now"}
          </h3>
          <p className="text-sm mb-5 max-w-md mx-auto" style={{ color: "var(--muted)" }}>
            {searchQuery || location || employmentType || workArrangement
              ? "Try a broader search or remove a filter. New listings arrive throughout the week."
              : "Check back soon — new roles are scraped daily across Zambia."}
          </p>
          <div className="flex gap-3 justify-center">
            {(searchQuery || location || employmentType || workArrangement) && (
              <button onClick={resetFilters} className="btn btn-ghost btn-sm">
                Reset filters
              </button>
            )}
            <a href="/signin" className="btn btn-primary btn-sm">
              Get matches on WhatsApp
            </a>
          </div>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {jobsList.map((job) => (
              <JobCard
                key={job.id}
                id={job.id}
                title={job.title}
                company={job.company}
                location={job.location}
                skills={job.skills}
                closingDate={job.closing_date}
                postedAt={job.posted_at}
                salaryMin={job.salary_min}
                salaryMax={job.salary_max}
                employmentType={job.employment_type}
                workArrangement={job.work_arrangement}
                hybridDaysPerWeek={job.hybrid_days_per_week}
                payFrequency={job.pay_frequency}
                saveToken={token}
                jobSaved={savedJobIds.has(job.id)}
                onSaveChange={(jobId, next) => {
                  setSavedJobIds((prev) => {
                    const n = new Set(prev);
                    if (next) n.add(jobId);
                    else n.delete(jobId);
                    return n;
                  });
                }}
              />
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <Pagination
              page={page}
              totalPages={totalPages}
              onChange={setPage}
            />
          )}
        </>
      )}

    </div>
  );
}
