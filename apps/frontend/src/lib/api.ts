/**
 * API client for ZedApply backend.
 * All requests go through this client for consistent auth + error handling.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

interface FetchOptions extends RequestInit {
  token?: string;
}

export class ApiError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { token, ...fetchOptions } = options;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, { ...fetchOptions, headers });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || body.title || "Unknown error");
  }

  return res.json() as Promise<T>;
}

/** Helper to get stored auth token */
function getToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("zed_cv_token") || "";
}

// ── Auth ──
export interface OTPResponse {
  message: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  user_id: string;
}

export const auth = {
  requestOTP: (phone: string) =>
    apiFetch<OTPResponse>("/auth/otp/request", {
      method: "POST",
      body: JSON.stringify({ phone }),
    }),
  verifyOTP: (phone: string, code: string, consentAccepted?: boolean) =>
    apiFetch<AuthTokens>("/auth/otp/verify", {
      method: "POST",
      body: JSON.stringify({
        phone,
        code,
        ...(consentAccepted !== undefined && { consent_accepted: consentAccepted }),
      }),
    }),
};

// ── CV structured sections (task #59) ──
// Mirrors apps/backend/app/schemas/cv_sections.py exactly. Keep these in
// sync — they're the canonical wire shape for cvs.parsed_data.sections.

export type LanguageProficiency = "native" | "fluent" | "conversational" | "basic";

export interface CVHeader {
  linkedin_url?: string | null;
  portfolio_url?: string | null;
  github_url?: string | null;
}

export interface ProfessionalSummary {
  text: string;
}

export interface WorkExperience {
  title: string;
  company: string;
  location?: string;
  start_date?: string;
  end_date?: string | null;
  achievements: string[];
}

export interface Education {
  degree: string;
  institution: string;
  location?: string;
  start_date?: string;
  end_date?: string | null;
  gpa?: string | null;
  thesis?: string | null;
}

export interface Certification {
  name: string;
  issuer?: string;
  year?: string | null;
  expiry?: string | null;
}

export interface CVLanguage {
  name: string;
  proficiency: LanguageProficiency;
}

export interface CVProject {
  name: string;
  role?: string;
  technologies: string[];
  outcome?: string;
}

export interface CVAchievement {
  title: string;
  year?: string | null;
}

export interface Publication {
  title: string;
  venue?: string;
  year?: string | null;
  url?: string | null;
}

export interface Membership {
  organisation: string;
  role: string;
  year_started?: string | null;
  year_ended?: string | null;
}

export interface VolunteerWork {
  organisation: string;
  role?: string;
  start_date?: string;
  end_date?: string | null;
  description?: string;
}

export interface Reference {
  name: string;
  title?: string;
  organisation?: string;
  phone?: string | null;
  email?: string | null;
}

export interface CVSections {
  header?: CVHeader | null;
  professional_summary?: ProfessionalSummary | null;
  work_experience: WorkExperience[];
  education: Education[];
  certifications: Certification[];
  languages: CVLanguage[];
  projects: CVProject[];
  achievements: CVAchievement[];
  publications: Publication[];
  memberships: Membership[];
  volunteer_work: VolunteerWork[];
  references: Reference[];
}

// ── Profile ──
export interface UserProfile {
  id: string;
  phone: string;
  full_name: string | null;
  email: string | null;
  skills: string[];
  cv_uploaded: boolean;
  subscription_tier: string;
  role?: string;
  location?: string | null;
  years_experience?: number;
  /** Structured CV body from cv_parser (task #59). Null when no CV
   *  is uploaded or when the upload pre-dates structured parsing. */
  cv_sections?: CVSections | null;
}

export interface UserPreferences {
  whatsapp_alerts: boolean;
  email_notifications_enabled: boolean;
  language: "en" | "bem";
}

export interface NotificationChannels {
  whatsapp: boolean;
  email: boolean;
}

export interface AutoMatchPreferences {
  auto_match_enabled: boolean;
  notification_channels: NotificationChannels;
}

// ── Job-search preferences (Phase 2 Initiative #4) ─────────────────
// Distinct from UserPreferences above — that one is notification prefs
// (legacy /profile/preferences). These are job-search prefs and back
// the rewritten Preferences tab. Both endpoints live; they cover
// orthogonal concerns.

export type PreferenceLanguageProficiency =
  | "native"
  | "fluent"
  | "intermediate"
  | "basic";

export type JobSalaryFrequency = "monthly" | "annual" | "hourly" | "daily";

export type PreferredWorkArrangement = "remote" | "hybrid" | "onsite" | "any";

export type TargetRolesSource = "user_provided" | "cv_inferred" | "mixed";

export interface PreferredLanguage {
  language: string;
  proficiency: PreferenceLanguageProficiency;
}

export interface IndustryExperience {
  industry: string;
  years_experience: number;
}

// @openapi JobPreferences
export interface JobPreferences {
  target_roles: string[];
  target_roles_source: TargetRolesSource;
  salary_min: number | null;
  salary_max: number | null;
  salary_currency: string;
  salary_frequency: JobSalaryFrequency | null;
  preferred_work_arrangement: PreferredWorkArrangement | null;
  willing_to_relocate: boolean;
  acceptable_regions: string[];
  languages: PreferredLanguage[];
  industries: IndustryExperience[];
  extras: Record<string, unknown>;
  auto_populated_at: string | null;
  manually_updated_at: string | null;
  /** Per-field hint computed by the API — which fields are still
   *  showing values from the CV auto-populate path. Empty once the
   *  user has manually edited the row at all. */
  auto_populated_fields: string[];
}

// @openapi JobPreferencesUpdate
export interface JobPreferencesUpdate {
  target_roles?: string[];
  salary_min?: number | null;
  salary_max?: number | null;
  salary_currency?: string;
  salary_frequency?: JobSalaryFrequency | null;
  preferred_work_arrangement?: PreferredWorkArrangement | null;
  willing_to_relocate?: boolean;
  acceptable_regions?: string[];
  languages?: PreferredLanguage[];
  industries?: IndustryExperience[];
  extras?: Record<string, unknown>;
}

export const preferencesApi = {
  get: (token: string) => apiFetch<JobPreferences>("/preferences", { token }),
  patch: (token: string, data: JobPreferencesUpdate) =>
    apiFetch<JobPreferences>("/preferences", {
      method: "PATCH",
      token,
      body: JSON.stringify(data),
    }),
};

export type SkillProficiency = "beginner" | "intermediate" | "advanced" | "expert";

export interface UserSkill {
  name: string;
  proficiency: SkillProficiency;
  source: "cv_parse" | "manual" | "assessment";
}

export interface UserSkillsList {
  skills: UserSkill[];
}

export const profile = {
  get: (token: string) => apiFetch<UserProfile>("/profile", { token }),
  update: (
    token: string,
    data: {
      full_name?: string | null;
      email?: string | null;
      location?: string | null;
      years_experience?: number;
    }
  ) =>
    apiFetch<UserProfile>("/profile", {
      method: "PATCH",
      token,
      body: JSON.stringify(data),
    }),
  remove: (token: string) =>
    apiFetch<{ deleted: boolean; user_id: string }>("/profile", {
      method: "DELETE",
      token,
    }),
  getPreferences: (token: string) =>
    apiFetch<UserPreferences>("/profile/preferences", { token }),
  updatePreferences: (token: string, data: Partial<UserPreferences>) =>
    apiFetch<UserPreferences>("/profile/preferences", {
      method: "PATCH",
      token,
      body: JSON.stringify(data),
    }),
  getSkills: (token: string) => apiFetch<UserSkillsList>("/profile/skills", { token }),
  addSkill: (token: string, data: { name: string; proficiency?: SkillProficiency }) =>
    apiFetch<UserSkillsList>("/profile/skills", {
      method: "POST",
      token,
      body: JSON.stringify(data),
    }),
  updateSkill: (token: string, name: string, proficiency: SkillProficiency) =>
    apiFetch<UserSkillsList>(`/profile/skills/${encodeURIComponent(name)}`, {
      method: "PATCH",
      token,
      body: JSON.stringify({ proficiency }),
    }),
  removeSkill: (token: string, name: string) =>
    apiFetch<UserSkillsList>(`/profile/skills/${encodeURIComponent(name)}`, {
      method: "DELETE",
      token,
    }),
};

export const autoMatchPreferences = {
  get: (token: string) =>
    apiFetch<AutoMatchPreferences>("/users/me/preferences/auto-match", { token }),
  patch: (token: string, data: Partial<AutoMatchPreferences>) =>
    apiFetch<AutoMatchPreferences>("/users/me/preferences/auto-match", {
      method: "PATCH",
      token,
      body: JSON.stringify(data),
    }),
};

// ── Admin ──
export interface AdminStats {
  users_total: number;
  users_active_30d: number;
  subscriptions_active: number;
  subscriptions_paid: number;
  jobs_total: number;
  jobs_active: number;
  jobs_expired: number;
  matches_24h: number;
  matches_total: number;
  revenue_ngwee_30d: number;
  revenue_ngwee_total: number;
  pending_review_count: number;
}

export interface AdminUserRow {
  id: string;
  phone: string;
  full_name: string | null;
  location: string | null;
  subscription_tier: string;
  role: string;
  matches_used: number;
  matches_limit: number;
  created_at: string | null;
}

export interface AdminUserList {
  users: AdminUserRow[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface AdminJobRow {
  id: string;
  title: string;
  company: string | null;
  location: string | null;
  source: string;
  quality_score: number;
  is_active: boolean;
  closing_date: string | null;
  posted_at: string | null;
}

export interface AdminJobList {
  jobs: AdminJobRow[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface AdminJobReviewRow {
  id: string;
  title: string;
  company: string | null;
  source: string;
  source_url: string | null;
  reasons: string[];
  created_at: string | null;
}

export interface AdminJobReviewQueue {
  jobs: AdminJobReviewRow[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface AdminJobReviewUpdate {
  apply_url?: string;
  apply_email?: string;
  application_instructions?: string;
}

export interface AdminPaymentRow {
  id: string;
  user_id: string;
  user_phone: string | null;
  amount: number;
  currency: string;
  payment_method: string;
  provider: string | null;
  status: string;
  created_at: string | null;
  completed_at: string | null;
}

export interface AdminPaymentList {
  payments: AdminPaymentRow[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
  total_completed_ngwee: number;
}

export interface AdminMatchRow {
  id: string;
  user_id: string;
  user_phone: string | null;
  job_id: string;
  job_title: string;
  job_company: string | null;
  score: number;
  status: string | null;
  created_at: string | null;
}

export interface AdminMatchList {
  matches: AdminMatchRow[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export type SubscriptionTier =
  | "free"
  | "starter"
  | "professional"
  | "super_standard";

export interface AdminTierBreakdown {
  free: number;
  starter: number;
  professional: number;
  super_standard: number;
  total_active: number;
}

export interface AdminSubscriptionRow {
  user_id: string;
  user_phone: string | null;
  full_name: string | null;
  tier: SubscriptionTier;
  status: string;
  matches_used: number;
  matches_limit: number;
  current_period_end: string | null;
  created_at: string | null;
}

export interface AdminSubscriptionList {
  breakdown: AdminTierBreakdown;
  subscriptions: AdminSubscriptionRow[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface AdminJobCreate {
  title: string;
  company?: string;
  location?: string;
  description: string;
  source: "manual" | "scraper" | "ocr" | "partner";
  apply_url?: string;
  apply_email?: string;
  closing_date?: string;
  salary_min?: number;
  salary_max?: number;
}

export const admin = {
  stats: (token: string) => apiFetch<AdminStats>("/admin/stats", { token }),
  users: (
    token: string,
    params?: { page?: number; per_page?: number; search?: string; tier?: string }
  ) => {
    const q = new URLSearchParams();
    if (params?.page) q.set("page", String(params.page));
    if (params?.per_page) q.set("per_page", String(params.per_page));
    if (params?.search) q.set("search", params.search);
    if (params?.tier) q.set("tier", params.tier);
    return apiFetch<AdminUserList>(`/admin/users?${q}`, { token });
  },
  jobs: (
    token: string,
    params?: { page?: number; per_page?: number; expired?: boolean; is_active?: boolean }
  ) => {
    const q = new URLSearchParams();
    if (params?.page) q.set("page", String(params.page));
    if (params?.per_page) q.set("per_page", String(params.per_page));
    if (params?.expired !== undefined) q.set("expired", String(params.expired));
    if (params?.is_active !== undefined) q.set("is_active", String(params.is_active));
    return apiFetch<AdminJobList>(`/admin/jobs?${q}`, { token });
  },
  reviewQueue: (
    token: string,
    params?: { page?: number; per_page?: number }
  ) => {
    const q = new URLSearchParams();
    if (params?.page) q.set("page", String(params.page));
    if (params?.per_page) q.set("per_page", String(params.per_page));
    return apiFetch<AdminJobReviewQueue>(`/admin/jobs/review-queue?${q}`, { token });
  },
  approveReviewJob: (token: string, jobId: string, data: AdminJobReviewUpdate) =>
    apiFetch<{ id: string; is_active: boolean; admin_reviewed_at: string }>(
      `/admin/jobs/${encodeURIComponent(jobId)}/approve`,
      { method: "POST", token, body: JSON.stringify(data) }
    ),
  dismissReviewJob: (token: string, jobId: string) =>
    apiFetch<{ id: string; is_active: boolean; admin_reviewed_at: string }>(
      `/admin/jobs/${encodeURIComponent(jobId)}/dismiss`,
      { method: "POST", token }
    ),
  bulkDeactivate: (
    token: string,
    body: { job_ids?: string[]; expired_only?: boolean }
  ) =>
    apiFetch<{ deactivated: number }>("/admin/jobs/bulk-deactivate", {
      method: "POST",
      token,
      body: JSON.stringify(body),
    }),
  payments: (
    token: string,
    params?: { page?: number; per_page?: number; status?: string }
  ) => {
    const q = new URLSearchParams();
    if (params?.page) q.set("page", String(params.page));
    if (params?.per_page) q.set("per_page", String(params.per_page));
    if (params?.status) q.set("status", params.status);
    return apiFetch<AdminPaymentList>(`/admin/payments?${q}`, { token });
  },
  matches: (
    token: string,
    params?: { page?: number; per_page?: number; min_score?: number }
  ) => {
    const q = new URLSearchParams();
    if (params?.page) q.set("page", String(params.page));
    if (params?.per_page) q.set("per_page", String(params.per_page));
    if (params?.min_score !== undefined) q.set("min_score", String(params.min_score));
    return apiFetch<AdminMatchList>(`/admin/matches?${q}`, { token });
  },
  subscriptions: (
    token: string,
    params?: { page?: number; per_page?: number; tier?: string; status?: string }
  ) => {
    const q = new URLSearchParams();
    if (params?.page) q.set("page", String(params.page));
    if (params?.per_page) q.set("per_page", String(params.per_page));
    if (params?.tier) q.set("tier", params.tier);
    if (params?.status) q.set("status", params.status);
    return apiFetch<AdminSubscriptionList>(`/admin/subscriptions?${q}`, { token });
  },
  updateSubscription: (
    token: string,
    userId: string,
    tier: SubscriptionTier
  ) =>
    apiFetch<AdminSubscriptionRow>(
      `/admin/subscriptions/${encodeURIComponent(userId)}`,
      {
        method: "PATCH",
        token,
        body: JSON.stringify({ tier }),
      }
    ),
  createJob: (token: string, data: AdminJobCreate) =>
    apiFetch<AdminJobRow>("/admin/jobs", {
      method: "POST",
      token,
      body: JSON.stringify(data),
    }),
  updateJob: (
    token: string,
    jobId: string,
    data: Partial<AdminJobCreate> & { is_active?: boolean }
  ) =>
    apiFetch<AdminJobRow>(`/admin/jobs/${encodeURIComponent(jobId)}`, {
      method: "PATCH",
      token,
      body: JSON.stringify(data),
    }),
  deleteJob: (token: string, jobId: string) =>
    apiFetch<{ deleted: boolean; id: string }>(
      `/admin/jobs/${encodeURIComponent(jobId)}`,
      { method: "DELETE", token }
    ),
};

// ── CV ──
// Matches docs/openapi.yaml:265 (CVUploadResponse).
// 200 path returns the parsed-sync fields; 202 path returns the queue fields.
export interface CVUploadResult {
  // Sync path (200 OK) — present when LLM parse succeeds inline:
  cv_id?: string;
  parsed_skills?: string[];
  experience_summary?: string;
  parsing_confidence?: number;

  // Queue path (202 Accepted) — present when parse is deferred:
  queued?: boolean;
  queue_id?: string;
  message?: string;
}

// @openapi CVAnalysisResponse
export interface CVAnalysis {
  overall: number;
  skills: number;
  format: number;
  impact: number;
  strengths: string[];
  improvements: string[];
  cached: boolean;
}

export interface CVGenerateResult {
  cv_generation_id: string;
  content: string;
  word_count: number;
  job_title: string;
  company: string | null;
  /** Structured CV from the LLM (task #59). Null on legacy responses or
   *  when /cv/generate falls through to the free-text path. Templates
   *  prefer this when present; the `content` field stays for clipboard
   *  copy and the legacy parseCv.ts fallback. */
  sections?: CVSections | null;
}

export interface CVGenerationSummary {
  id: string;
  job_title: string;
  company: string | null;
  word_count: number;
  created_at: string | null;
}

export interface CVGenerationDetail extends CVGenerationSummary {
  content: string;
  /** Structured CV re-loaded from cv_generations.metadata.sections.
   *  Null on rows created before structured generation shipped. */
  sections?: CVSections | null;
}

export const cv = {
  upload: async (token: string, file: File): Promise<CVUploadResult> => {
    const formData = new FormData();
    formData.append("file", file);
    const res = await fetch(`${API_BASE}/cv/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: formData,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new ApiError(
        res.status,
        (body as { detail?: string }).detail || "Upload failed"
      );
    }
    return res.json() as Promise<CVUploadResult>;
  },
  analyze: (token: string) =>
    apiFetch<CVAnalysis>("/cv/analyze", { method: "POST", token, body: "{}" }),
  generate: (
    token: string,
    data: { job_title: string; company?: string; job_description?: string; job_id?: string }
  ) =>
    apiFetch<CVGenerateResult>("/cv/generate", {
      method: "POST",
      token,
      body: JSON.stringify(data),
    }),
  listGenerations: (token: string) =>
    apiFetch<{ generations: CVGenerationSummary[] }>("/cv/generations", { token }),
  getGeneration: (token: string, id: string) =>
    apiFetch<CVGenerationDetail>(`/cv/generations/${encodeURIComponent(id)}`, { token }),
};

// ── Jobs ──

// Mirrors apps/backend/app/schemas/jobs.py::EmploymentType / WorkArrangement.
// Keep this in sync — they're the canonical wire-shape strings used by
// the filter query params and stored in jobs.employment_type / jobs.work_arrangement.
export type EmploymentType =
  | "full_time"
  | "part_time"
  | "contract"
  | "freelance"
  | "internship"
  | "temporary";

export type WorkArrangement = "remote" | "hybrid" | "on_site";

export type PayFrequency = "monthly" | "annual" | "hourly" | "daily";

export interface Job {
  id: string;
  title: string;
  company: string | null;
  location: string | null;
  closing_date: string | null;
  posted_at?: string | null;
  quality_score: number;
  skills: string[];
  description: string | null;
  salary_min?: number | null;
  salary_max?: number | null;
  source?: string | null;
  source_url?: string | null;
  apply_url?: string | null;
  apply_email?: string | null;

  // ── task #60: richer job ad shape ───────────────────────────────────
  // All optional + nullable so legacy rows (pre-migration 016) still
  // satisfy the type. Frontend renders fields only when truthy / non-empty.
  employment_type?: EmploymentType | null;
  work_arrangement?: WorkArrangement | null;
  hybrid_days_per_week?: number | null;
  benefits?: string[] | null;
  application_instructions?: string | null;
  reporting_structure?: string | null;
  manages_others?: number | null;
  interview_process?: string | null;
  tools_tech_stack?: string[] | null;
  success_metrics?: string | null;
  company_description?: string | null;
  reference_number?: string | null;
  currency?: string | null;
  pay_frequency?: PayFrequency | null;
  bonus_structure?: string | null;
  equity_offered?: boolean | null;
}

export interface JobListResponse {
  jobs: Job[];
  total: number;
  page: number;
  pages: number;
}

export const jobs = {
  list: (params?: {
    page?: number;
    search?: string;
    location?: string;
    sort?: "relevance" | "recent" | "closing";
    skills?: string[];
    source?: string[];
    employment_type?: EmploymentType[];
    work_arrangement?: WorkArrangement[];
  }) => {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", String(params.page));
    if (params?.search) query.set("search", params.search);
    if (params?.location) query.set("location", params.location);
    if (params?.sort) query.set("sort", params.sort);
    if (params?.skills?.length) query.set("skills", params.skills.join(","));
    if (params?.source?.length) query.set("source", params.source.join(","));
    if (params?.employment_type?.length)
      query.set("employment_type", params.employment_type.join(","));
    if (params?.work_arrangement?.length)
      query.set("work_arrangement", params.work_arrangement.join(","));
    const token = getToken();
    return apiFetch<JobListResponse>(`/jobs?${query}`, { token });
  },
  get: (jobId: string) => {
    const token = getToken();
    return apiFetch<Job>(`/jobs/${jobId}`, { token });
  },
};

// ── Matches ──
export interface MatchData {
  id: string;
  score: number;
  vector_score: number;
  skill_score: number;
  bonus_score: number;
  matched_skills: string[];
  missing_skills: string[];
  explanation: string | null;
  job: {
    id: string;
    title: string;
    company: string | null;
    location: string | null;
    closing_date: string | null;
    // Backend's Job pydantic model includes these — frontend type was
    // truncated, leaving the /matches Apply button dead. Restored here.
    apply_url?: string | null;
    apply_email?: string | null;
    source_url?: string | null;
  };
}

export interface MatchListResponse {
  matches: MatchData[];
  remaining_quota: number;
  credited_count?: number;
  matches_limit?: number;
}

export const matches = {
  get: (token: string, minScore?: number) =>
    apiFetch<MatchListResponse>(
      `/matches${minScore ? `?min_score=${minScore}` : ""}`,
      { token }
    ),
  trigger: (token: string) =>
    apiFetch<{ message: string; estimated_seconds?: number }>("/matches/trigger", {
      method: "POST",
      token,
    }),
};

// ── Subscription ──
export interface Subscription {
  tier: string;
  matches_used: number;
  matches_limit: number;
  active: boolean;
  expires_at: string | null;
}

export const subscription = {
  get: (token: string) => apiFetch<Subscription>("/subscription", { token }),
  pay: (
    token: string,
    data: { tier: string; payment_method: string; phone: string }
  ) =>
    apiFetch<{ message: string; transaction_id: string }>(
      "/subscription/pay",
      { method: "POST", token, body: JSON.stringify(data) }
    ),
};

// ── Health ──
export const health = {
  check: () => apiFetch<{ status: string }>("/health"),
};

// ── Cover letter ──
export const coverLetter = {
  generate: (token: string, jobId: string, tone?: "formal" | "friendly" | "confident") =>
    apiFetch<{ letter: string; word_count: number; tone: string; document_id: string }>(
      "/cover-letter/generate",
      {
        method: "POST",
        token,
        body: JSON.stringify({ job_id: jobId, tone: tone || "formal" }),
      }
    ),
};

// ── Interview prep ──
export interface InterviewPrepResult {
  content: string;
  word_count: number;
  job_title: string;
  company: string | null;
  cached: boolean;
}

export const interviewPrep = {
  generate: (token: string, jobId: string) =>
    apiFetch<InterviewPrepResult>("/interview-prep/generate", {
      method: "POST",
      token,
      body: JSON.stringify({ job_id: jobId }),
    }),
};

// ── Data-subject rights (task #63) ──
export interface AccountDeletionResult {
  deleted: boolean;
  already_deleted: boolean;
  user_id: string | null;
}

export const me = {
  /**
   * Triggers /api/v1/me/export. Bypasses the JSON helper because the
   * server streams an attachment — we want to surface it to the user
   * as a download rather than reading it into JS memory and stringifying
   * a second time. Uses the same auth + base URL as the rest of the
   * client.
   */
  export: async (token: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/me/export`, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      throw new ApiError(res.status, body.detail || "Could not export data");
    }
    const blob = await res.blob();
    // Pull the suggested filename from Content-Disposition; fall back to
    // a sensible default so the download still works if the header is
    // stripped by a proxy.
    const cd = res.headers.get("content-disposition") || "";
    const match = cd.match(/filename="?([^"]+)"?/i);
    const filename = match?.[1] || `zedcv-data-export-${new Date().toISOString().slice(0, 10)}.json`;

    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },

  /**
   * DELETE /api/v1/me with a phone confirmation in the body. The phone
   * is sent verbatim — the backend does a byte-exact compare against
   * the stored phone, so any whitespace or case difference is rejected.
   */
  deleteAccount: (token: string, confirmPhone: string) =>
    apiFetch<AccountDeletionResult>("/me", {
      method: "DELETE",
      token,
      body: JSON.stringify({ confirm_phone: confirmPhone }),
    }),
};

// ── Contact form (task #65) ──
export interface ContactSubmission {
  name: string;
  email: string;
  phone?: string;
  message: string;
}

export interface ContactResult {
  success: boolean;
  message: string;
}

export const contact = {
  submit: (data: ContactSubmission) =>
    apiFetch<ContactResult>("/contact", {
      method: "POST",
      body: JSON.stringify(data),
    }),
};

// ── Public stats (home-page social proof) ──
export interface PublicStats {
  jobs_active: number;
  avg_skills_matched: number;
  hours_saved_total: number;
}

export const publicStats = {
  get: () => apiFetch<PublicStats>("/stats/public"),
};

// ── Legal docs (task #62) ──
export type LegalSlug = "privacy" | "terms" | "cookies";

export interface AdminLegalDoc {
  slug: string;
  version: string;
  content_md: string;
  content_html: string;
  last_modified_by: string | null;
  last_modified_at: string | null;
}

export const adminLegal = {
  get: (token: string, slug: LegalSlug) =>
    apiFetch<AdminLegalDoc>(`/admin/legal/${slug}`, { token }),
  update: (
    token: string,
    slug: LegalSlug,
    data: { version: string; content_md: string },
  ) =>
    apiFetch<AdminLegalDoc>(`/admin/legal/${slug}`, {
      method: "PATCH",
      token,
      body: JSON.stringify(data),
    }),
};
