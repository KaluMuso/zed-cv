/**
 * Shared types for Zed CV — matches OpenAPI spec.
 */

export type SubscriptionTier = "free" | "starter" | "professional";
export type JobSource = "manual" | "scraper" | "ocr" | "partner";
export type SubscriptionStatus = "active" | "expired" | "cancelled" | "past_due";
export type PaymentMethodType = "mtn_money" | "airtel_money";
export type CoverLetterTone = "formal" | "friendly" | "confident";
export type CVStyle = "professional" | "modern" | "simple";

export interface AuthTokens { access_token: string; refresh_token: string; user_id: string; }
export interface OTPRequest { phone: string; }
export interface OTPVerify { phone: string; code: string; }

export interface UserProfile {
  id: string; phone: string; full_name: string | null; email: string | null;
  location: string | null; years_experience: number; skills: string[];
  subscription_tier: SubscriptionTier; created_at: string;
}
export interface UserProfileUpdate { full_name?: string; email?: string; location?: string; years_experience?: number; }

export interface CVUploadResponse { cv_id: string; parsed_skills: string[]; experience_summary: string; parsing_confidence: number; }
export interface CVGenerateRequest { job_id: string; style?: CVStyle; }

export interface Job {
  id: string; title: string; company: string | null; location: string | null;
  description: string; requirements: string[]; skills_required: string[];
  salary_min: number | null; salary_max: number | null;
  apply_url: string | null; apply_email: string | null;
  source: JobSource; quality_score: number; closing_date: string | null;
  posted_at: string; is_active: boolean;
}
export interface JobCreate {
  title: string; company?: string; location?: string; description: string;
  requirements?: string[]; skills_required?: string[];
  salary_min?: number; salary_max?: number; apply_url?: string; apply_email?: string;
  source: JobSource; closing_date?: string;
}
export interface JobList { jobs: Job[]; total: number; page: number; per_page: number; }

export interface MatchResult {
  id: string; job: Job; score: number;
  semantic_score?: number; skills_score?: number;
  vector_score: number; skill_score: number; bonus_score: number;
  experience_score?: number; location_score?: number; recency_score?: number;
  matched_skills: string[]; missing_skills: string[]; explanation: string | null; created_at: string;
}
export interface MatchList { matches: MatchResult[]; remaining_quota: number; }

export interface Subscription {
  id: string; tier: SubscriptionTier; status: SubscriptionStatus;
  current_period_start: string; current_period_end: string | null;
  matches_used: number; matches_limit: number;
}
export interface PaymentInitiate { tier: Exclude<SubscriptionTier, "free">; payment_method: PaymentMethodType; phone: string; }
export interface PaymentInitiateResponse { transaction_token: string; payment_url: string; status: "pending" | "redirect"; }

export interface CoverLetterRequest { job_id: string; tone?: CoverLetterTone; }
export interface CoverLetterResponse { content: string; word_count: number; }

export interface HealthCheck { status: "healthy" | "degraded" | "unhealthy"; version: string; supabase: boolean; waha: boolean; }
export interface ProblemDetail {
  type: string;
  title: string;
  status: number;
  detail?: string;
  user_message?: string;
  instance?: string;
  request_id?: string;
}

/** Canonical tiers — mirrors app/schemas/subscription.py (ngwee + match quota). */
export const PRICING = {
  free: { price_zmw: 0, matches_limit: 3, label: "Free" },
  starter: { price_zmw: 12500, matches_limit: 50, label: "Starter" },
  professional: { price_zmw: 25000, matches_limit: 125, label: "Professional" },
  super_standard: {
    price_zmw: 50000,
    matches_limit: 99999,
    label: "Super Standard",
  },
} as const;
