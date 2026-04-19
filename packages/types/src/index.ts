/**
 * Shared types for Zed CV — generated to match OpenAPI spec.
 * These types are used by both the Next.js frontend and shared packages.
 */

// ─── Auth ───

export interface OTPRequest {
  phone: string; // +260XXXXXXXXX
}

export interface OTPVerify {
  phone: string;
  code: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  user_id: string;
}

// ─── User ───

export type SubscriptionTier = "mwana" | "mwezi" | "bwino";

export interface UserProfile {
  id: string;
  phone: string;
  full_name: string | null;
  email: string | null;
  location: string | null;
  years_experience: number;
  skills: string[];
  subscription_tier: SubscriptionTier;
  created_at: string;
}

export interface UserProfileUpdate {
  full_name?: string;
  email?: string;
  location?: string;
  years_experience?: number;
}

// ─── CV ───

export interface CVUploadResponse {
  cv_id: string;
  parsed_skills: string[];
  experience_summary: string;
  parsing_confidence: number;
}

export type CVStyle = "professional" | "modern" | "simple";

export interface CVGenerateRequest {
  job_id: string;
  style?: CVStyle;
}

export interface CVGenerateResponse {
  cv_url: string;
  preview_html: string;
}

// ─── Jobs ───

export type JobSource = "manual" | "scraper" | "ocr" | "partner";

export interface Job {
  id: string;
  title: string;
  company: string | null;
  location: string | null;
  description: string;
  requirements: string[];
  skills_required: string[];
  salary_min: number | null;
  salary_max: number | null;
  apply_url: string | null;
  apply_email: string | null;
  source: JobSource;
  quality_score: number;
  closing_date: string | null;
  posted_at: string;
  is_active: boolean;
}

export interface JobCreate {
  title: string;
  company?: string;
  location?: string;
  description: string;
  requirements?: string[];
  skills_required?: string[];
  salary_min?: number;
  salary_max?: number;
  apply_url?: string;
  apply_email?: string;
  source: JobSource;
  closing_date?: string;
}

export interface JobList {
  jobs: Job[];
  total: number;
  page: number;
  per_page: number;
}

// ─── Matching ───

export interface MatchResult {
  id: string;
  job: Job;
  score: number;
  vector_score: number;
  skill_score: number;
  bonus_score: number;
  matched_skills: string[];
  missing_skills: string[];
  explanation: string | null;
  created_at: string;
}

export interface MatchList {
  matches: MatchResult[];
  remaining_quota: number;
}

// ─── Subscription ───

export type SubscriptionStatus = "active" | "expired" | "cancelled" | "past_due";
export type PaymentMethodType = "mtn_money" | "airtel_money";

export interface Subscription {
  id: string;
  tier: SubscriptionTier;
  status: SubscriptionStatus;
  current_period_start: string;
  current_period_end: string | null;
  matches_used: number;
  matches_limit: number;
}

export interface PaymentInitiate {
  tier: Exclude<SubscriptionTier, "mwana">;
  payment_method: PaymentMethodType;
  phone: string;
}

export interface PaymentInitiateResponse {
  transaction_token: string;
  payment_url: string;
  status: "pending" | "redirect";
}

// ─── Cover Letter ───

export type CoverLetterTone = "formal" | "friendly" | "confident";

export interface CoverLetterRequest {
  job_id: string;
  tone?: CoverLetterTone;
}

export interface CoverLetterResponse {
  content: string;
  word_count: number;
}

// ─── Health ───

export interface HealthCheck {
  status: "healthy" | "degraded" | "unhealthy";
  version: string;
  supabase: boolean;
  waha: boolean;
}

// ─── Error ───

export interface ProblemDetail {
  type: string;
  title: string;
  status: number;
  detail?: string;
  instance?: string;
}

// ─── Pricing Constants ───

export const PRICING = {
  mwana: { price_zmw: 0, matches_limit: 5, label: "Mwana (Free)" },
  mwezi: { price_zmw: 7900, matches_limit: 25, label: "Mwezi" },
  bwino: { price_zmw: 19900, matches_limit: 999999, label: "Bwino" },
} as const;
