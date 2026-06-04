"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
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
import { Counter } from "@/components/ui/Counter";
import { Pagination } from "@/components/ui/Pagination";
import {
  JobsSidebar,
  JobsSidebarMobile,
  type JobsListPreset,
} from "@/components/jobs/JobsSidebar";
import { MobileFilterShell } from "@/components/jobs/MobileFilterShell";
import { countActiveJobFilters } from "@/lib/jobsFilterCount";
import { authPath } from "@/lib/auth-paths";
import { EmptyState } from "@/components/shared/EmptyState";
import { useRecentSearches } from "@/hooks/useRecentSearches";
import { btnClass, tagClass } from "@/lib/cn-ui";
import { cn } from "@/lib/utils";
import { isGreyedClosedListing } from "@/lib/jobVisibility";

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

function parseTruthyParam(value: string | null): boolean {
  return value === "true" || value === "1";
}

function parseSkillsParam(value: string | null): string[] {
  if (!value) return [];
  return value
    .split(",")
    .map((skill) => skill.trim().toLowerCase())
    .filter(Boolean);
}

function isEmploymentType(value: string): value is EmploymentType {
  return (
    value === "full_time" ||
    value === "part_time" ||
    value === "contract" ||
    value === "freelance" ||
    value === "internship" ||
    value === "temporary"
  );
}

function isWorkArrangement(value: string): value is WorkArrangement {
  return value === "remote" || value === "hybrid" || value === "on_site";
}

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
  const [showClosed, setShowClosed] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [listPreset, setListPreset] = useState<JobsListPreset>("all");
  const urlHydratedRef = useRef(false);
  const lastUrlSyncRef = useRef("");
  const { recent: recentSearches, push: pushRecentSearch, clear: clearRecentSearches } =
    useRecentSearches();

  const syncFiltersToUrl = process.env.VITEST === undefined;

  // Hydrate filter state from URL (preserves shareable /jobs?q=… links).
  useEffect(() => {
    if (!syncFiltersToUrl || urlHydratedRef.current || !searchParams) return;
    const q = searchParams.get("q") ?? "";
    const loc = searchParams.get("location") ?? "";
    const sortParam = searchParams.get("sort");
    const pageParam = searchParams.get("page");
    const skillsParam = searchParams.get("skills");
    const employmentParam = searchParams.get("employment_type");
    const arrangementParam = searchParams.get("work_arrangement");
    const hasSalaryParam = searchParams.get("has_salary");
    const savedOnlyParam = searchParams.get("saved_only");

    setSearchInput(q);
    setSearchQuery(q);
    setLocation(loc);
    setSelectedSkills(parseSkillsParam(skillsParam));

    if (employmentParam && isEmploymentType(employmentParam)) {
      setEmploymentType(employmentParam);
    }
    if (arrangementParam && isWorkArrangement(arrangementParam)) {
      setWorkArrangement(arrangementParam);
    }

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

    if (parseTruthyParam(savedOnlyParam)) {
      setListPreset("saved");
    } else if (parseTruthyParam(hasSalaryParam)) {
      setListPreset("with_salary");
    } else if (sortParam === "closing") {
      setListPreset("closing");
    } else if (arrangementParam === "remote") {
      setListPreset("remote");
    } else if (employmentParam === "full_time") {
      setListPreset("full_time");
    }

    urlHydratedRef.current = true;
  }, [searchParams, syncFiltersToUrl]);

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
    if (selectedSkills.length > 0) sp.set("skills", selectedSkills.join(","));
    else sp.delete("skills");
    if (employmentType) sp.set("employment_type", employmentType);
    else sp.delete("employment_type");
    if (workArrangement) sp.set("work_arrangement", workArrangement);
    else sp.delete("work_arrangement");
    if (listPreset === "with_salary") sp.set("has_salary", "true");
    else sp.delete("has_salary");
    if (listPreset === "saved") sp.set("saved_only", "true");
    else sp.delete("saved_only");
    const next = sp.toString();
    if (next === lastUrlSyncRef.current) return;
    lastUrlSyncRef.current = next;
    router.replace(next ? `${pathname}?${next}` : pathname, { scroll: false });
  }, [
    searchQuery,
    location,
    sort,
    page,
    selectedSkills,
    employmentType,
    workArrangement,
    listPreset,
    pathname,
    router,
    searchParams,
    syncFiltersToUrl,
  ]);

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
      if (searchInput.trim()) pushRecentSearch(searchInput);
      setPage(1);
    }, 300);
    return () => clearTimeout(t);
  }, [searchInput, pushRecentSearch]);

  const effectiveSort =
    listPreset === "closing" ? "closing" : sort;
  const effectiveEmploymentType =
    listPreset === "full_time" ? "full_time" : employmentType;
  const effectiveWorkArrangement =
    listPreset === "remote" ? "remote" : workArrangement;

  const fetchJobs = useCallback(async () => {
    if (listPreset === "saved" && !token) {
      setJobsList([]);
      setTotalPages(1);
      setTotal(0);
      setLoading(false);
      return;
    }

    setLoading(true);
    try {
      const res = await jobsApi.list({
        page,
        search: searchQuery || undefined,
        location: location || undefined,
        sort: effectiveSort,
        skills: selectedSkills.length > 0 ? selectedSkills : undefined,
        employment_type: effectiveEmploymentType ? [effectiveEmploymentType] : undefined,
        work_arrangement: effectiveWorkArrangement ? [effectiveWorkArrangement] : undefined,
        has_salary: listPreset === "with_salary" ? true : undefined,
        saved_only: listPreset === "saved" ? true : undefined,
        closed_only: showClosed || undefined,
      });
      setJobsList(res.jobs);
      setTotalPages(res.pages);
      setTotal(res.total);
    } catch {
      setJobsList([]);
      setTotalPages(1);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [
    page,
    searchQuery,
    location,
    effectiveSort,
    selectedSkills,
    effectiveEmploymentType,
    effectiveWorkArrangement,
    listPreset,
    token,
    showClosed,
  ]);

  useEffect(() => {
    fetchJobs();
  }, [fetchJobs]);

  // Legacy share links used ?j=<id> on /jobs — redirect to the standalone page.
  const legacyDrawerJobId = searchParams?.get("j") ?? null;
  useEffect(() => {
    if (!legacyDrawerJobId || !urlHydratedRef.current) return;
    router.replace(`/jobs/${legacyDrawerJobId}`);
  }, [legacyDrawerJobId, router]);

  const activeFilterCount = countActiveJobFilters({
    searchQuery,
    searchInput,
    location,
    sort,
    selectedSkills,
    employmentType,
    workArrangement,
    showClosed,
    listPreset,
  });

  const hasActiveFilters = activeFilterCount > 0;

  const hasFilterConstraints =
    Boolean(searchQuery || location || employmentType || workArrangement) ||
    selectedSkills.length > 0 ||
    showClosed ||
    listPreset !== "all";

  const resetFilters = () => {
    setSearchInput("");
    setSearchQuery("");
    setLocation("");
    setSort("recent");
    setSelectedSkills([]);
    setEmploymentType("");
    setWorkArrangement("");
    setShowClosed(false);
    setListPreset("all");
    setPage(1);
  };

  const onListPresetChange = (preset: JobsListPreset) => {
    setListPreset(preset);
    setPage(1);
    if (preset === "closing") {
      setSort("closing");
      return;
    }
    if (preset === "full_time") {
      setEmploymentType("full_time");
      setWorkArrangement("");
      setSort("recent");
      return;
    }
    if (preset === "remote") {
      setWorkArrangement("remote");
      setEmploymentType("");
      setSort("recent");
      return;
    }
    if (preset === "all") {
      setSort("recent");
      setEmploymentType("");
      setWorkArrangement("");
    }
  };

  const toggleSkill = (skill: string) => {
    setSelectedSkills((prev) =>
      prev.includes(skill) ? prev.filter((s) => s !== skill) : [...prev, skill]
    );
    setPage(1);
  };

  return (
    <div className="max-w-[1280px] mx-auto px-5 sm:px-6 py-8 md:py-12">
      {/* Header */}
      <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="eyebrow mb-2">All jobs across Zambia</div>
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
        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <button
            type="button"
            className={cn(btnClass("outline", "sm"), "gap-1.5")}
            onClick={() => onListPresetChange("saved")}
            aria-pressed={listPreset === "saved"}
          >
            <Icon name="bookmark" size={14} />
            Saved
            {savedJobIds.size > 0 ? (
              <span className={tagClass("green", "text-xs ml-0.5")}>{savedJobIds.size}</span>
            ) : null}
          </button>
          <Link href="/matches" className={cn(btnClass("primary", "sm"), "gap-1.5")}>
            My matches
            <Icon name="arrowRight" size={14} />
          </Link>
        </div>
      </div>

      {/* Filter bar */}
      {/* Filter bar — search is debounced (300ms); no submit button. */}
      <div
        className="sticky top-[65px] z-30 -mx-5 sm:-mx-6 px-5 sm:px-6 py-4 mb-6 flex flex-col md:flex-row gap-3 items-stretch md:items-center border-b border-border"
        style={{
          background: "color-mix(in srgb, var(--bg) 92%, transparent)",
          backdropFilter: "blur(12px)",
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
            className="field pl-10 min-h-11"
            aria-label="Search jobs"
            list="job-recent-searches"
          />
          {recentSearches.length > 0 ? (
            <datalist id="job-recent-searches">
              {recentSearches.map((term) => (
                <option key={term} value={term} />
              ))}
            </datalist>
          ) : null}
        </div>

        <select
          value={location}
          onChange={(e) => {
            setLocation(e.target.value);
            setPage(1);
          }}
          className="field min-h-11"
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
          className="field min-h-11"
          style={{ width: "auto", minWidth: 140 }}
          aria-label="Sort jobs"
        >
          {SORT_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        {recentSearches.length > 0 ? (
          <div className="flex flex-wrap items-center gap-1.5 w-full md:w-auto" aria-label="Recent searches">
            {recentSearches.slice(0, 4).map((term) => (
              <button
                key={term}
                type="button"
                className={tagClass("mono", "shrink-0 cursor-pointer")}
                onClick={() => {
                  setSearchInput(term);
                  setSearchQuery(term);
                  setPage(1);
                }}
              >
                {term}
              </button>
            ))}
            <button
              type="button"
              className="min-h-11 px-2 text-xs underline"
              style={{ color: "var(--muted)" }}
              onClick={clearRecentSearches}
            >
              Clear
            </button>
          </div>
        ) : null}

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
            className="field min-h-11"
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
            className="field min-h-11"
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

        <label
          className="hidden lg:flex items-center gap-2 text-xs min-h-11"
          style={{ color: "var(--ink-2)" }}
        >
          <input
            type="checkbox"
            className="h-4 w-4 rounded border-input"
            checked={showClosed}
            onChange={(e) => {
              setShowClosed(e.target.checked);
              setPage(1);
            }}
            aria-label="Show closed jobs"
          />
          Show closed
        </label>

        <button
          type="button"
          className={btnClass("ghost")}
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
        className="mb-6 flex gap-1.5 overflow-x-auto scroll-thin pb-1 overscroll-x-contain snap-x snap-mandatory"
        style={{ scrollbarWidth: "thin" }}
        role="group"
        aria-label="Filter by skill"
      >
        {selectedSkills.length > 0 && (
          <button
            onClick={() => {
              setSelectedSkills([]);
              setPage(1);
            }}
            className={tagClass("mono", "shrink-0 cursor-pointer border-accent text-accent-600")}
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
              className={cn(
                tagClass(active ? "green" : "mono", "shrink-0 cursor-pointer capitalize snap-start"),
              )}
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
      ) : listPreset === "saved" && !token ? (
        <div className="text-center py-20">
          <p className="text-sm mb-4" style={{ color: "var(--muted)" }}>
            Sign in to see jobs you have saved.
          </p>
          <a href="/auth?next=/jobs" className={btnClass("primary", "sm")}>
            Sign in
          </a>
        </div>
      ) : (
        <>
          <MobileFilterShell
            activeFilterCount={activeFilterCount}
            onClearAll={resetFilters}
            showClosed={showClosed}
            onShowClosedChange={(next) => {
              setShowClosed(next);
              setPage(1);
            }}
          >
            <JobsSidebarMobile
              active={listPreset}
              onChange={onListPresetChange}
              savedCount={savedJobIds.size}
              layout="stack"
            />
          </MobileFilterShell>
          {jobsList.length === 0 ? (
            <EmptyState
              title={
                hasFilterConstraints
                  ? "No jobs match your filters"
                  : "No jobs are open right now"
              }
              description={
                hasFilterConstraints
                  ? "Try a broader search or remove a filter. New listings arrive throughout the week."
                  : "Check back soon — new roles are scraped daily across Zambia."
              }
              ctaText="Get matches on WhatsApp"
              ctaHref={authPath("/matches")}
              secondaryCtaText={hasFilterConstraints ? "Reset filters" : undefined}
              onSecondaryCtaClick={hasFilterConstraints ? resetFilters : undefined}
              className="my-8"
            />
          ) : (
          <div className="grid grid-cols-1 lg:grid-cols-[220px_minmax(0,1fr)] gap-6 lg:gap-8">
            <JobsSidebar
              active={listPreset}
              onChange={onListPresetChange}
              savedCount={savedJobIds.size}
            />
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 min-w-0">
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
                listingClosed={isGreyedClosedListing(job)}
              />
            ))}
            </div>
          </div>
          )}

          {/* Pagination */}
          {jobsList.length > 0 && totalPages > 1 ? (
            <Pagination
              page={page}
              totalPages={totalPages}
              onChange={setPage}
            />
          ) : null}
        </>
      )}

    </div>
  );
}
