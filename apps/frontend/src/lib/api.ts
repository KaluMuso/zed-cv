/**
 * API client for Zed CV backend.
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

export interface AdminTierBreakdown {
  free: number;
  starter: number;
  professional: number;
  total_active: number;
}

export interface AdminSubscriptionRow {
  user_id: string;
  user_phone: string | null;
  full_name: string | null;
  tier: "free" | "starter" | "professional";
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
    tier: "free" | "starter" | "professional"
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
  id: string;
  skills_extracted: string[];
  message: string;
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
};

// ── Jobs ──
export interface Job {
  id: string;
  title: string;
  company: string | null;
  location: string | null;
  closing_date: string | null;
  quality_score: number;
  skills: string[];
  description: string | null;
}

export interface JobListResponse {
  jobs: Job[];
  total: number;
  page: number;
  pages: number;
}

export const jobs = {
  list: (params?: { page?: number; search?: string; location?: string }) => {
    const query = new URLSearchParams();
    if (params?.page) query.set("page", String(params.page));
    if (params?.search) query.set("search", params.search);
    if (params?.location) query.set("location", params.location);
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
