/**
 * API client for ZedApply backend.
 * All requests go through this client for consistent auth + error handling.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

/** Trusted-device token from POST /auth/otp/verify (remember_device). */
export const DEVICE_TOKEN_KEY = "zedapply_device_token";

function getDeviceToken(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem(DEVICE_TOKEN_KEY) || "";
}

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const headers: Record<string, string> = { ...extra };
  const device = getDeviceToken();
  if (device) {
    headers["X-Device-Token"] = device;
  }
  return headers;
}

/** JSON object bodies are stringified in apiFetch (analytics, admin bulk ops, etc.). */
type ApiJsonBody = Record<string, unknown>;

interface FetchOptions extends Omit<RequestInit, "body"> {
  token?: string;
  body?: BodyInit | null | ApiJsonBody;
}

function prepareRequestBody(
  body: FetchOptions["body"]
): BodyInit | null | undefined {
  if (body == null || typeof body !== "object") {
    return body ?? undefined;
  }
  if (
    body instanceof Blob ||
    body instanceof FormData ||
    body instanceof URLSearchParams ||
    ArrayBuffer.isView(body)
  ) {
    return body;
  }
  return JSON.stringify(body);
}

export class ApiError extends Error {
  status: number;
  detail: string;
  /** Machine-readable RFC 7807 detail when the API returns a problem code. */
  code?: string;
  /** Structured problem payload when the API returns an object detail (e.g. CV upload). */
  problem?: Record<string, unknown>;
  constructor(
    status: number,
    detail: string,
    code?: string,
    problem?: Record<string, unknown>
  ) {
    super(detail);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.code = code;
    this.problem = problem;
  }
}

const MACHINE_CODE_RE = /^[a-z][a-z0-9_]*$/;

function reportApi5xxToSentry(
  status: number,
  path: string,
  problem: Record<string, unknown>
): void {
  if (status < 500 || typeof window === "undefined") return;
  void import("@sentry/nextjs").then((Sentry) => {
    Sentry.captureMessage(`API ${status} ${path}`, {
      level: "error",
      extra: { problem },
      tags: {
        api_path: path,
        problem_code:
          typeof problem.detail === "string" ? problem.detail : "unknown",
      },
    });
  });
}

function parseProblemBody(
  body: Record<string, unknown>,
  fallbackStatusText: string
): { message: string; code?: string } {
  const rawDetail = body.detail;
  const detailStr =
    typeof rawDetail === "string" ? rawDetail : fallbackStatusText;
  const userMessage =
    typeof body.user_message === "string" ? body.user_message : undefined;
  const code = MACHINE_CODE_RE.test(detailStr) ? detailStr : undefined;
  const message =
    userMessage ||
    (code ? "Delivery is temporarily unavailable. Please try again." : detailStr) ||
    fallbackStatusText;
  return { message, code };
}

export async function apiFetch<T>(
  path: string,
  options: FetchOptions = {}
): Promise<T> {
  const { token, body, ...fetchOptions } = options;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_BASE}${path}`, {
    ...fetchOptions,
    headers,
    body: prepareRequestBody(body),
  });

  if (!res.ok) {
    const body = (await res.json().catch(() => ({
      detail: res.statusText,
    }))) as Record<string, unknown>;
    const { message, code } = parseProblemBody(body, res.statusText);
    reportApi5xxToSentry(res.status, path, body);
    throw new ApiError(res.status, message, code);
  }

  if (res.status === 204) {
    return undefined as T;
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
  tier?: string | null;
  default_channel?: "email" | "whatsapp" | "both" | null;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  user_id: string;
  device_token?: string | null;
  trusted_device_login?: boolean;
}

export type OtpChannel = "email" | "whatsapp";

export const auth = {
  login: (phone: string) =>
    apiFetch<AuthTokens>("/auth/login", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({ phone }),
    }),
  requestOTP: (phone: string, channel?: OtpChannel) =>
    apiFetch<OTPResponse>("/auth/otp/request", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        phone,
        ...(channel ? { channel } : {}),
      }),
    }),
  verifyOTP: (
    phone: string,
    code: string,
    options?: {
      consentAccepted?: boolean;
      email?: string;
      rememberDevice?: boolean;
      referralRef?: string | null;
    }
  ) =>
    apiFetch<AuthTokens>("/auth/otp/verify", {
      method: "POST",
      headers: authHeaders(),
      body: JSON.stringify({
        phone,
        code,
        ...(options?.consentAccepted !== undefined && {
          consent_accepted: options.consentAccepted,
        }),
        ...(options?.email && { email: options.email }),
        remember_device: options?.rememberDevice ?? false,
        ...(options?.referralRef?.trim()
          ? { referral_ref: options.referralRef.trim() }
          : {}),
      }),
    }),
};

export const REFERRAL_STORAGE_KEY = "zedapply_referral_ref";

export function readStoredReferralRef(): string | null {
  if (typeof window === "undefined") return null;
  try {
    const v = sessionStorage.getItem(REFERRAL_STORAGE_KEY);
    return v?.trim() || null;
  } catch {
    return null;
  }
}

export function clearStoredReferralRef(): void {
  if (typeof window === "undefined") return;
  try {
    sessionStorage.removeItem(REFERRAL_STORAGE_KEY);
  } catch {
    /* private mode */
  }
}

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
  referral_code?: string;
  referral_signups_count?: number;
  referral_qualified_count?: number;
  /** From users.education JSONB — used for profile completeness. */
  education?: Record<string, unknown>[];
  /** From users.certifications JSONB — used for profile completeness. */
  certifications?: Record<string, unknown>[];
}

// @openapi NotificationPreferences
export interface NotificationPreferences {
  whatsapp_alerts: boolean;
  email_notifications_enabled: boolean;
  language: "en" | "bem";
}

// @openapi UserPreferences
export type PreferredNotificationChannel = "email" | "whatsapp" | "both";

export interface UserPreferences {
  whatsapp_number: string | null;
  location: string | null;
  currency: "ZMW" | "USD";
  alert_frequency: "daily" | "weekly" | "muted";
  whatsapp_verified: boolean;
  preferred_notification_channel: PreferredNotificationChannel;
  whatsapp_digest_available: boolean;
  quiet_hours_start: string;
  quiet_hours_end: string;
  profile_visible_to_employers: boolean;
  hidden_employer_name: string | null;
  notify_product_updates: boolean;
  display_timezone: string;
}

// @openapi UserPreferencesUpdate
export interface UserPreferencesUpdate {
  whatsapp_number?: string;
  location?: string;
  currency?: "ZMW" | "USD";
  alert_frequency?: "daily" | "weekly" | "muted";
  preferred_notification_channel?: PreferredNotificationChannel;
  quiet_hours_start?: string;
  quiet_hours_end?: string;
  profile_visible_to_employers?: boolean;
  hidden_employer_name?: string | null;
  notify_product_updates?: boolean;
  display_timezone?: string;
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
// Distinct from NotificationPreferences (/profile/preferences) and
// UserPreferences (/users/me/preferences). These are job-search prefs and back
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
    apiFetch<NotificationPreferences>("/profile/preferences", { token }),
  updatePreferences: (token: string, data: Partial<NotificationPreferences>) =>
    apiFetch<NotificationPreferences>("/profile/preferences", {
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

export const userPreferences = {
  get: (token: string) =>
    apiFetch<UserPreferences>("/users/me/preferences", { token }),
  patch: (token: string, data: UserPreferencesUpdate) =>
    apiFetch<UserPreferences>("/users/me/preferences", {
      method: "PATCH",
      token,
      body: JSON.stringify(data),
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

export interface AdminLlmCostByModel {
  model: string;
  cost_usd: number;
  request_count: number;
  prompt_tokens: number;
  completion_tokens: number;
}

export interface AdminLlmCostByFeature {
  feature: string;
  cost_usd: number;
  request_count: number;
}

export interface AdminLlmCostDay {
  date: string;
  cost_usd: number;
}

export interface AdminLlmCostStats {
  days: number;
  total_cost_usd: number;
  total_requests: number;
  by_model: AdminLlmCostByModel[];
  by_feature: AdminLlmCostByFeature[];
  daily: AdminLlmCostDay[];
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
  welcome_match_bonus?: number | null;
  welcome_match_bonus_until?: string | null;
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
  closing_date?: string;
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
  provider_ref?: string | null;
  invoice_number?: string | null;
  status: string;
  created_at: string | null;
  completed_at: string | null;
}

export interface AdminPaymentDetail extends AdminPaymentRow {
  user_email: string | null;
  user_full_name: string | null;
  webhook_summary: Record<string, unknown> | null;
  tier_inferred: string | null;
}

export interface AdminBillingHealth {
  lenco_environment: string;
  lenco_api_url: string;
  lenco_api_key_set: boolean;
  lenco_public_key_set: boolean;
  lenco_webhook_secret_set: boolean;
  lenco_verify_signatures: boolean;
  lenco_production_ready: boolean;
  webhook_url_expected: string;
  payments_pending: number;
  payments_failed_24h: number;
  payments_completed_24h: number;
  lenco_completed_24h: number;
  subscriptions_cancelling: number;
  checked_at: string;
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
  cancelled_at?: string | null;
  lenco_subscription_ref?: string | null;
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

export interface AdminSubscriptionMetrics {
  mrr_kwacha: number;
  mrr_ngwee: number;
  active_subscriptions: number;
  cancelled_this_month: number;
  active_at_month_start: number;
  churn_rate: number;
  month_start: string;
}

export interface AdminContactFixJobRow {
  id: string;
  title: string;
  company: string | null;
  source_url: string | null;
  apply_url: string | null;
  apply_email: string | null;
  contact_phone: string | null;
  posted_at: string | null;
}

export interface AdminContactFixJobList {
  jobs: AdminContactFixJobRow[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
  fixed_count: number;
}

export interface AdminJobContactPatch {
  apply_url?: string;
  apply_email?: string;
  contact_phone?: string;
  mark_uncontactable?: boolean;
  reason?: string;
}

export interface ScrapingSourceEntry {
  url: string;
  source_type: string;
  scraped_at: string;
}

export interface AdminJobCreate {
  title: string;
  company?: string;
  location?: string;
  description: string;
  source: "manual" | "scraper" | "ocr" | "partner";
  apply_url?: string;
  apply_email?: string;
  contact_phone?: string;
  closing_date?: string;
  salary_min?: number;
  salary_max?: number;
  admin_published?: boolean;
}

export interface AdminEmailHealth {
  status: "ok" | "degraded" | "error";
  code?: string | null;
  message: string;
  api_key_configured: boolean;
  from_email: string;
  from_domain?: string | null;
  domain_verified?: boolean | null;
  domains_listed?: number | null;
}

export const admin = {
  emailHealth: (token: string) =>
    apiFetch<AdminEmailHealth>("/admin/email/health", { token }),
  stats: (token: string) => apiFetch<AdminStats>("/admin/stats", { token }),
  llmCostStats: (token: string, params?: { days?: number }) => {
    const q = new URLSearchParams();
    if (params?.days) q.set("days", String(params.days));
    const qs = q.toString();
    return apiFetch<AdminLlmCostStats>(
      `/admin/llm-cost-stats${qs ? `?${qs}` : ""}`,
      { token }
    );
  },
  /** GET /admin/export/companies.csv — authenticated CSV download */
  exportCompaniesCsv: async (token: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/admin/export/companies.csv`, {
      method: "GET",
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      throw new ApiError(res.status, body.detail || "Could not export companies");
    }
    const blob = await res.blob();
    const cd = res.headers.get("content-disposition") || "";
    const match = cd.match(/filename="?([^"]+)"?/i);
    const filename = match?.[1] || "companies.csv";
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
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
  jobsNeedsContactFix: (
    token: string,
    params?: { page?: number; per_page?: number }
  ) => {
    const q = new URLSearchParams();
    if (params?.page) q.set("page", String(params.page));
    if (params?.per_page) q.set("per_page", String(params.per_page));
    return apiFetch<AdminContactFixJobList>(
      `/admin/jobs/needs-contact-fix?${q}`,
      { token }
    );
  },
  patchJobContact: (token: string, jobId: string, data: AdminJobContactPatch) =>
    apiFetch<Record<string, unknown>>(
      `/admin/jobs/${encodeURIComponent(jobId)}/contact`,
      { method: "PATCH", token, body: JSON.stringify(data) }
    ),
  subscriptionMetrics: (token: string) =>
    apiFetch<AdminSubscriptionMetrics>("/admin/subscriptions/metrics", { token }),
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
  /** Track 4e queue: is_review_required jobs, newest first */
  track4eReviewQueue: (
    token: string,
    params?: { page?: number; per_page?: number }
  ) => {
    const q = new URLSearchParams();
    if (params?.page) q.set("page", String(params.page));
    if (params?.per_page) q.set("per_page", String(params.per_page));
    return apiFetch<AdminJobReviewQueue>(`/admin/review-jobs?${q}`, { token });
  },
  updateTrack4eReviewJob: (
    token: string,
    jobId: string,
    data: AdminJobReviewUpdate
  ) =>
    apiFetch<{ id: string; is_active: boolean; is_review_required: boolean }>(
      `/admin/review-jobs/${encodeURIComponent(jobId)}`,
      { method: "PATCH", token, body: JSON.stringify(data) }
    ),
  bulkMarkReviewDuplicate: (token: string, jobIds: string[]) =>
    apiFetch<{ updated: number }>("/admin/review-jobs/bulk-mark-duplicate", {
      method: "POST",
      token,
      body: JSON.stringify({ job_ids: jobIds }),
    }),
  bulkPermanentlyInactive: (token: string, jobIds: string[]) =>
    apiFetch<{ updated: number }>("/admin/review-jobs/bulk-permanently-inactive", {
      method: "POST",
      token,
      body: JSON.stringify({ job_ids: jobIds }),
    }),
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
    params?: { page?: number; per_page?: number; status?: string; provider?: string }
  ) => {
    const q = new URLSearchParams();
    if (params?.page) q.set("page", String(params.page));
    if (params?.per_page) q.set("per_page", String(params.per_page));
    if (params?.status) q.set("status", params.status);
    if (params?.provider) q.set("provider", params.provider);
    return apiFetch<AdminPaymentList>(`/admin/payments?${q}`, { token });
  },
  paymentDetail: (token: string, paymentId: string) =>
    apiFetch<AdminPaymentDetail>(`/admin/payments/${encodeURIComponent(paymentId)}`, {
      token,
    }),
  billingHealth: (token: string) =>
    apiFetch<AdminBillingHealth>("/admin/billing/health", { token }),
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
  updateWelcomeBonus: (
    token: string,
    userId: string,
    body: { welcome_match_bonus?: number; welcome_match_bonus_until?: string }
  ) =>
    apiFetch<AdminUserRow>(
      `/admin/users/${encodeURIComponent(userId)}/welcome-bonus`,
      {
        method: "PATCH",
        token,
        body: JSON.stringify(body),
      }
    ),
  createJob: (token: string, data: AdminJobCreate) =>
    apiFetch<Job>("/admin/jobs", {
      method: "POST",
      token,
      body: JSON.stringify(data),
    }),
  updateJob: (
    token: string,
    jobId: string,
    data: Partial<AdminJobCreate> & { is_active?: boolean; admin_published?: boolean }
  ) =>
    apiFetch<Job>(`/admin/jobs/${encodeURIComponent(jobId)}`, {
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

export interface TierConfigRow {
  tier: string;
  display_name: string;
  price_ngwee: number;
  checkout_price_ngwee?: number | null;
  promotion_active?: boolean | null;
  matches_limit: number;
  sort_order?: number;
  updated_at?: string | null;
}

export interface TierConfigList {
  tiers: TierConfigRow[];
  welcome_match_bonus?: number | null;
  welcome_match_bonus_until?: string | null;
  promo_until?: string | null;
}

/** Public pricing catalog; pass token for personalized checkout prices. */
export const tiers = {
  list: (token?: string | null) =>
    apiFetch<TierConfigList>("/tiers", token ? { token } : undefined),
};

/** Superadmin tier pricing editor (legacy bulk PUT). */
export const adminTierConfig = {
  get: (token: string) =>
    apiFetch<TierConfigList>("/admin/tier-config", { token }),
  update: (token: string, tiersPayload: TierConfigRow[]) =>
    apiFetch<TierConfigList>("/admin/tier-config", {
      method: "PUT",
      token,
      body: JSON.stringify({ tiers: tiersPayload }),
    }),
};

/** Admin tier config — GET list + PATCH per tier (superadmin JWT). */
export const adminTiers = {
  list: (token: string) => apiFetch<TierConfigList>("/admin/tiers", { token }),
  patch: (
    token: string,
    tierName: string,
    body: { price_ngwee: number; matches_limit: number },
  ) =>
    apiFetch<TierConfigRow>(`/admin/tiers/${encodeURIComponent(tierName)}`, {
      method: "PATCH",
      token,
      body: JSON.stringify(body),
    }),
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

export interface BuildFromScratchPayload {
  summary: string;
  basics: {
    full_name: string;
    phone: string;
    email: string;
    location: string;
    headline: string;
  };
  experience: Array<{
    title: string;
    company: string;
    location: string;
    start_date: string;
    end_date: string;
    achievements: string[];
  }>;
  education: Array<{
    degree: string;
    institution: string;
    location: string;
    start_date: string;
    end_date: string;
    gpa: string;
  }>;
  skills: string[];
  style: {
    template: "modern" | "classic" | "compact";
    accent_color: string;
    show_summary: boolean;
  };
}

export interface BuildFromScratchResult {
  cv_id: string;
  pdf_url: string;
  storage_path: string;
  render_time_ms: number;
}

function parseUploadProblemDetail(
  body: Record<string, unknown>,
  fallbackStatusText: string
): { message: string; code?: string; problem?: Record<string, unknown> } {
  const parsed = parseProblemBody(body, fallbackStatusText);
  return { ...parsed, problem: body };
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
      const body = (await res.json().catch(() => ({}))) as Record<string, unknown>;
      const { message, code, problem } = parseUploadProblemDetail(body, res.statusText);
      throw new ApiError(res.status, message, code, problem);
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
  buildFromScratch: (token: string, data: BuildFromScratchPayload) =>
    apiFetch<BuildFromScratchResult>("/cv/build-from-scratch", {
      method: "POST",
      token,
      body: JSON.stringify(data),
    }),
  suggestSummary: (
    token: string,
    data: { strengths: string[]; headline?: string; full_name?: string }
  ) =>
    apiFetch<{ summary: string }>("/cv/suggest-summary", {
      method: "POST",
      token,
      body: JSON.stringify(data),
    }),
  suggestBullets: (
    token: string,
    data: { title: string; company: string; context?: string }
  ) =>
    apiFetch<{ bullets: string[] }>("/cv/suggest-bullets", {
      method: "POST",
      token,
      body: JSON.stringify(data),
    }),
  suggestSkills: (token: string, q: string, limit = 12) =>
    apiFetch<{ skills: Array<{ name: string }> }>(
      `/cv/skills/suggest?q=${encodeURIComponent(q)}&limit=${limit}`,
      { token }
    ),
  tailorForMatch: (token: string, matchId: string) =>
    apiFetch<MatchTailorCvResult>(
      `/matches/${encodeURIComponent(matchId)}/tailor-cv`,
      { method: "POST", token, body: "{}" }
    ),
};

export interface MatchTailorCvResult {
  generation_id: string;
  markdown: string;
  word_count: number;
  job_title: string;
  company?: string | null;
  cached?: boolean;
  duration_ms?: number | null;
  estimated_cost_usd?: number | null;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
}

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
  contact_phone?: string | null;
  apply_source?: string | null;
  description_markdown?: string | null;
  description_html?: string | null;
  section_html?: Record<string, string> | null;
  section_responsibilities?: string | null;
  section_requirements?: string | null;
  section_benefits?: string | null;
  section_how_to_apply?: string | null;
  section_about?: string | null;
  is_active?: boolean;
  deactivation_reason?: string | null;
  closure_reason?: string | null;
  closed_at?: string | null;
  deep_enriched_at?: string | null;
  admin_published?: boolean | null;
  scraping_sources?: ScrapingSourceEntry[] | null;

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
    has_salary?: boolean;
    saved_only?: boolean;
    include_closed?: boolean;
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
    if (params?.has_salary) query.set("has_salary", "true");
    if (params?.saved_only) query.set("saved_only", "true");
    if (params?.include_closed) query.set("include_closed", "true");
    const token = getToken();
    return apiFetch<JobListResponse>(`/jobs?${query}`, { token });
  },
  get: (jobId: string) => {
    const token = getToken();
    return apiFetch<Job>(`/jobs/${jobId}`, { token });
  },
};

export const savedJobs = {
  list: (token: string) =>
    apiFetch<SavedJobsListResponse>("/users/me/saved-jobs", { token }),
  updateStatus: (
    token: string,
    jobId: string,
    body: ApplicationStatusUpdate,
  ) =>
    apiFetch<ApplicationStatusResponse>(
      `/users/me/saved-jobs/${jobId}/status`,
      {
        method: "PATCH",
        token,
        body: body as unknown as ApiJsonBody,
      },
    ),
  save: (token: string, jobId: string) =>
    apiFetch<{ saved: boolean }>(`/jobs/${jobId}/save`, {
      method: "POST",
      token,
    }),
  unsave: (token: string, jobId: string) =>
    apiFetch<void>(`/jobs/${jobId}/save`, { method: "DELETE", token }),
};

export type ApplicationStatus =
  | "saved"
  | "applied"
  | "interviewing"
  | "offered"
  | "closed_won"
  | "closed_lost";

export interface SavedJobApplication {
  job: Job;
  application_status: ApplicationStatus;
  status_updated_at: string | null;
  application_notes: string | null;
  interview_date: string | null;
}

export interface SavedJobsListResponse {
  jobs: Job[];
  applications?: SavedJobApplication[];
}

export interface ApplicationStatusUpdate {
  status: ApplicationStatus;
  notes?: string | null;
  interview_date?: string | null;
}

export interface ApplicationStatusResponse {
  job_id: string;
  application_status: ApplicationStatus;
  status_updated_at: string | null;
  application_notes: string | null;
  interview_date: string | null;
}

// ── Matches ──
export interface MatchData {
  id: string;
  /** When this match row was created / last refreshed for the user. */
  created_at: string | null;
  score: number;
  vector_score: number;
  skill_score: number;
  bonus_score: number;
  semantic_score?: number;
  skills_score?: number;
  /** Experience fit component (0–15 under v2 scoring). */
  experience_score?: number | null;
  location_score?: number | null;
  recency_score?: number | null;
  matched_skills: string[];
  missing_skills: string[];
  explanation: string | null;
  job: {
    id: string;
    title: string;
    company: string | null;
    location: string | null;
    closing_date: string | null;
    salary_min?: number | null;
    salary_max?: number | null;
    // Backend's Job pydantic model includes these — frontend type was
    // truncated, leaving the /matches Apply button dead. Restored here.
    apply_url?: string | null;
    apply_email?: string | null;
    source_url?: string | null;
    apply_source?: string | null;
  };
}

export const analytics = {
  trackEvent: (
    token: string,
    event: string,
    properties: Record<string, unknown>
  ) =>
    apiFetch<void>("/analytics/events", {
      method: "POST",
      token,
      body: { event, properties },
    }),
};

export interface MatchListResponse {
  matches: MatchData[];
  remaining_quota: number;
  matches_used?: number;
  credited_count?: number;
  matches_limit?: number;
  matches_unlimited?: boolean;
  last_batch_run_at?: string | null;
  from_cache?: boolean;
}

/** POST /matches/refresh — MatchList plus optional onboarding message. */
export interface MatchRefreshResponse extends MatchListResponse {
  message?: string | null;
  /** True during first-time on-demand matching — show progress until next refresh. */
  refresh_computing?: boolean;
}

export const matches = {
  get: (
    token: string,
    opts?: { minScore?: number; includeClosed?: boolean },
  ) => {
    const query = new URLSearchParams();
    if (opts?.minScore != null) query.set("min_score", String(opts.minScore));
    if (opts?.includeClosed) query.set("include_closed", "true");
    const qs = query.toString();
    return apiFetch<MatchListResponse>(`/matches${qs ? `?${qs}` : ""}`, { token });
  },
  refresh: (token: string, minScore?: number) =>
    apiFetch<MatchRefreshResponse>(
      `/matches/refresh${minScore ? `?min_score=${minScore}` : ""}`,
      { method: "POST", token }
    ),
  trigger: (token: string) =>
    apiFetch<{ message: string; estimated_seconds?: number }>("/matches/trigger", {
      method: "POST",
      token,
    }),
};

export interface PushSubscribeBody {
  endpoint: string;
  keys: { p256dh: string; auth: string };
  expirationTime?: number | null;
}

export const push = {
  subscribe: (token: string, body: PushSubscribeBody) =>
    apiFetch<{ ok: boolean; message: string }>("/push/subscribe", {
      method: "POST",
      token,
      body: JSON.stringify(body),
    }),
};

// ── Subscription ──
export interface Subscription {
  tier: string;
  matches_used: number;
  matches_limit: number;
  matches_unlimited?: boolean;
  active: boolean;
  expires_at: string | null;
  welcome_match_bonus?: number | null;
  welcome_match_bonus_until?: string | null;
  promo_until?: string | null;
  welcome_bonus_active?: boolean | null;
}

export interface PaymentVerifyResult {
  status: string;
  tier: string;
  reference: string;
  payment_id?: string | null;
  message: string;
}

export interface PaymentHistoryRow {
  id: string;
  amount: number;
  currency: string;
  payment_method: string;
  provider?: string | null;
  status: string;
  created_at?: string | null;
  completed_at?: string | null;
}

export interface PaymentHistoryList {
  payments: PaymentHistoryRow[];
  total: number;
}

export interface InvoiceDetail {
  invoice_number: string;
  payment_id: string;
  reference: string;
  status: string;
  amount_ngwee: number;
  amount_kwacha: number;
  currency: string;
  tier: string;
  tier_label: string;
  payment_method: string;
  provider?: string | null;
  issued_at?: string | null;
  customer_name: string;
  customer_email?: string | null;
  customer_phone?: string | null;
}

export interface SubscriptionCancelResult {
  status: string;
  message: string;
  tier: string;
  active_until?: string | null;
  cancelled_at: string;
}

export const subscription = {
  get: (token: string) => apiFetch<Subscription>("/subscription", { token }),
  listPayments: (token: string, limit = 50) =>
    apiFetch<PaymentHistoryList>(`/subscription/payments?limit=${limit}`, { token }),
  /** @deprecated Use verifyPayment after Lenco widget onSuccess */
  pay: (
    token: string,
    data: { tier: string; payment_method: string; phone: string }
  ) =>
    apiFetch<{ message: string; transaction_id: string }>(
      "/subscription/pay",
      { method: "POST", token, body: JSON.stringify(data) }
    ),
  verifyPayment: (token: string, data: { reference: string; tier: string }) =>
    apiFetch<PaymentVerifyResult>("/subscription/verify-payment", {
      method: "POST",
      token,
      body: JSON.stringify(data),
    }),
  getInvoice: (token: string, paymentId: string) =>
    apiFetch<InvoiceDetail>(`/subscription/payments/${paymentId}/invoice`, { token }),
  emailInvoice: (token: string, paymentId: string) =>
    apiFetch<{ status: string; invoice_number: string }>(
      `/subscription/payments/${paymentId}/invoice/email`,
      { method: "POST", token },
    ),
  cancel: (token: string) =>
    apiFetch<SubscriptionCancelResult>("/subscription/cancel", {
      method: "POST",
      token,
    }),
};

// ── Health ──
export const health = {
  check: () => apiFetch<{ status: string }>("/health"),
};

// ── Data rights / consent (privacy settings) ──
export type ConsentType =
  | "terms_of_service"
  | "privacy_policy"
  | "marketing_email"
  | "marketing_whatsapp"
  | "analytics_cookies"
  | "third_party_data_sharing";

export interface ConsentRecordResponse {
  consent_type: ConsentType;
  granted: boolean;
  granted_at: string;
  legal_doc_version?: string | null;
}

export interface ConsentStatusResponse {
  consents: Partial<Record<ConsentType, boolean>>;
  last_updated: Partial<Record<ConsentType, string>>;
}

export const dataRights = {
  getConsentStatus: (token: string) =>
    apiFetch<ConsentStatusResponse>("/users/me/consent", { token }),
  recordConsent: (token: string, consentType: ConsentType, granted: boolean) =>
    apiFetch<{ consent: ConsentRecordResponse }>("/users/me/consent", {
      method: "POST",
      token,
      body: JSON.stringify({ consent_type: consentType, granted }),
    }),
};

// ── Cover letter ──
export interface CoverLetterVersionDetail {
  id: string;
  version_number: number;
  parent_version_id: string | null;
  generated_by: "ai" | "user_edit";
  created_at: string;
  label: string;
  content_md: string;
}

export interface CoverLetterVersionsResponse {
  versions: CoverLetterVersionDetail[];
  latest: CoverLetterVersionDetail | null;
}

export interface CoverLetterSaveResult {
  id: string;
  version_number: number;
  generated_by: "ai" | "user_edit";
  created_at: string;
  word_count: number;
}

export interface MatchCoverLetterGenerateResult {
  content: string;
  word_count: number;
  version_id: string;
  version_number: number;
}

export const coverLetter = {
  generate: (token: string, jobId: string) =>
    apiFetch<{ content: string; word_count: number; document_id: string }>(
      `/jobs/${jobId}/generate-cover-letter`,
      {
        method: "POST",
        token,
      }
    ),
  generateForMatch: (token: string, matchId: string) =>
    apiFetch<MatchCoverLetterGenerateResult>(
      `/matches/${encodeURIComponent(matchId)}/cover-letter/generate`,
      { method: "POST", token }
    ),
  listVersions: (token: string, matchId: string) =>
    apiFetch<CoverLetterVersionsResponse>(
      `/matches/${encodeURIComponent(matchId)}/cover-letter/versions`,
      { token }
    ),
  save: (
    token: string,
    matchId: string,
    body: {
      content_md: string;
      parent_version_id?: string | null;
      source?: "ai" | "user_edit";
    }
  ) =>
    apiFetch<CoverLetterSaveResult>(
      `/matches/${encodeURIComponent(matchId)}/cover-letter/save`,
      {
        method: "POST",
        token,
        body: JSON.stringify({
          content_md: body.content_md,
          parent_version_id: body.parent_version_id ?? null,
          source: body.source ?? "user_edit",
        }),
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

// ── Bwana Interview (mock + aptitude) ──
export type AptitudePack = "numerical" | "verbal" | "abstract";

export interface MockInterviewStartResult {
  session_id: string;
  question: string;
  question_number: number;
  total_questions: number;
}

export interface MockInterviewAnswerResult {
  session_id: string;
  progress: {
    star_score: number;
    feedback: string;
    question_number: number;
    total_questions: number;
  } | null;
  next_question: string | null;
  final_summary: {
    overall_score: number;
    strengths: string[];
    improvements: string[];
    practice_areas: string[];
  } | null;
}

export interface AptitudeQuestion {
  id: string;
  question_text: string;
  options: { label: string; value: string }[];
}

export interface AptitudePackResult {
  pack: AptitudePack;
  time_limit_seconds: number;
  questions: AptitudeQuestion[];
}

export interface AptitudeScoreResult {
  pack: AptitudePack;
  score: number;
  percentile: number;
  correct_count: number;
  total_questions: number;
}

export interface InterviewHistoryResult {
  mock_sessions: {
    id: string;
    role_label: string;
    overall_score: number | null;
    created_at: string | null;
  }[];
  aptitude_scores: {
    id: string;
    pack: string;
    score: number;
    percentile: number | null;
    elapsed_seconds: number | null;
    completed_at: string | null;
  }[];
}

export const bwanaInterview = {
  mockStart: (token: string, roleLabel: string) =>
    apiFetch<MockInterviewStartResult>("/interview/mock/start", {
      method: "POST",
      token,
      body: JSON.stringify({ role_label: roleLabel }),
    }),
  mockAnswer: (token: string, sessionId: string, answer: string) =>
    apiFetch<MockInterviewAnswerResult>("/interview/mock/answer", {
      method: "POST",
      token,
      body: JSON.stringify({ session_id: sessionId, answer }),
    }),
  aptitudePack: (token: string, pack: AptitudePack) =>
    apiFetch<AptitudePackResult>(`/interview/aptitude/pack/${pack}`, { token }),
  aptitudeScore: (
    token: string,
    pack: AptitudePack,
    answers: { question_id: string; value: string }[],
    elapsedSeconds: number,
  ) =>
    apiFetch<AptitudeScoreResult>("/interview/aptitude/score", {
      method: "POST",
      token,
      body: JSON.stringify({
        pack,
        answers,
        elapsed_seconds: elapsedSeconds,
      }),
    }),
  history: (token: string) =>
    apiFetch<InterviewHistoryResult>("/interview/history", { token }),
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
    const filename = match?.[1] || `zedapply-data-export-${new Date().toISOString().slice(0, 10)}.json`;

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

// ── Bwana chat assistant ──
export type BwanaChatSource = "faq" | "llm" | "escalated";

export interface BwanaChatResponse {
  response: string;
  source: BwanaChatSource;
  took_ms: number;
  session_id: string;
}

export const bwana = {
  chat: (message: string, sessionId?: string) =>
    apiFetch<BwanaChatResponse>("/bwana/chat", {
      method: "POST",
      token: getToken(),
      body: {
        message,
        ...(sessionId ? { session_id: sessionId } : {}),
      },
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
export type LegalSlug = "privacy" | "terms" | "cookies" | "refund";

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

// ── Employer portal (B2B) ──
export type EmployerTier = "lite" | "pro";
export type EmployerRole = "owner" | "admin" | "recruiter" | "viewer";

export interface EmployerSummary {
  id: string;
  company_name: string;
  industry?: string | null;
  size_band?: string | null;
  website?: string | null;
  verified: boolean;
}

// @openapi EmployerMeResponse
export interface EmployerMe {
  employer: EmployerSummary;
  seats: Array<{
    id: string;
    user_id: string;
    role: EmployerRole;
    invite_email?: string | null;
    accepted_at?: string | null;
  }>;
  my_role: EmployerRole;
}

export interface CandidatePreview {
  candidate_id: string;
  headline?: string | null;
  location?: string | null;
  years_experience?: number | null;
  skills: string[];
  match_hint?: string | null;
}

export interface ContactRequestRow {
  id: string;
  candidate_user_id: string;
  message_text: string;
  channel: string;
  status: string;
  candidate_consented?: boolean | null;
  candidate_phone?: string | null;
  candidate_email?: string | null;
  candidate_name?: string | null;
}

// @openapi EmployerSubscriptionResponse
export interface EmployerSubscription {
  tier: EmployerTier | null;
  status: string;
  active: boolean;
  contacts_used: number;
  contacts_limit: number;
  price_ngwee: number;
  current_period_end?: string | null;
}

// @openapi EmployerCheckoutResponse
export interface EmployerCheckout {
  reference: string;
  amount_ngwee: number;
  tier: EmployerTier;
  public_key: string;
  label: string;
}

export const employer = {
  register: (
    token: string,
    body: {
      company_name: string;
      industry?: string;
      size_band?: string;
      website?: string;
    },
  ) =>
    apiFetch<{ employer: EmployerSummary }>("/employers/register", {
      method: "POST",
      token,
      body,
    }),

  me: (token: string) => apiFetch<EmployerMe>("/employers/me", { token }),

  invite: (token: string, body: { email: string; role?: EmployerRole }) =>
    apiFetch<{ seat_id: string; message: string }>("/employers/me/invite", {
      method: "POST",
      token,
      body,
    }),

  search: (token: string, params?: { skills?: string; location?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.skills) q.set("skills", params.skills);
    if (params?.location) q.set("location", params.location);
    if (params?.limit) q.set("limit", String(params.limit));
    const qs = q.toString();
    return apiFetch<{ results: CandidatePreview[]; total: number }>(
      `/employers/candidates/search${qs ? `?${qs}` : ""}`,
      { token },
    );
  },

  requestContact: (
    token: string,
    candidateId: string,
    body: { message_text: string; channel?: "whatsapp" | "email" | "both" },
  ) =>
    apiFetch<ContactRequestRow>(`/employers/candidates/${candidateId}/contact`, {
      method: "POST",
      token,
      body,
    }),

  contacts: (token: string) =>
    apiFetch<{ contacts: ContactRequestRow[]; total: number }>("/employers/me/contacts", {
      token,
    }),

  subscription: (token: string) =>
    apiFetch<EmployerSubscription>("/employers/me/subscription", { token }),

  checkout: (token: string, tier: EmployerTier) =>
    apiFetch<EmployerCheckout>("/employers/me/subscription/checkout", {
      method: "POST",
      token,
      body: { tier },
    }),

  verifyPayment: (token: string, body: { reference: string; tier: EmployerTier }) =>
    apiFetch<{ status: string; tier: string; reference: string; message: string }>(
      "/employers/me/subscription/verify-payment",
      { method: "POST", token, body },
    ),
};
