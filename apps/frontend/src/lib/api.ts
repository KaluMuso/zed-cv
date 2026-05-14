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
  verifyOTP: (phone: string, code: string) =>
    apiFetch<AuthTokens>("/auth/otp/verify", {
      method: "POST",
      body: JSON.stringify({ phone, code }),
    }),
};

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
}

export interface UserPreferences {
  whatsapp_alerts: boolean;
  language: "en" | "bem";
}

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
export interface CVUploadResult {
  id?: string;
  skills_extracted?: string[];
  message: string;
  // Set by the backend (HTTP 202) when AI capacity is exhausted and the
  // upload was stored in the queue instead of processed inline.
  queued?: boolean;
  queue_id?: string;
}

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
  }) => {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", String(params.page));
    if (params?.search) query.set("search", params.search);
    if (params?.location) query.set("location", params.location);
    if (params?.sort) query.set("sort", params.sort);
    if (params?.skills?.length) query.set("skills", params.skills.join(","));
    if (params?.source?.length) query.set("source", params.source.join(","));
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
}

export const matches = {
  get: (token: string, minScore?: number) =>
    apiFetch<MatchListResponse>(
      `/matches${minScore ? `?min_score=${minScore}` : ""}`,
      { token }
    ),
  trigger: (token: string) =>
    apiFetch<{ message: string }>("/matches/trigger", {
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
