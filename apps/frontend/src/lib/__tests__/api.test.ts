import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  API_UNAVAILABLE_MESSAGE,
  DEVICE_TOKEN_KEY,
  REFERRAL_STORAGE_KEY,
  apiFetch,
  auth,
  clearStoredReferralRef,
  admin,
  analytics,
  autoMatchPreferences,
  contact,
  coverLetter,
  cv,
  dataRights,
  health,
  jobs,
  matches,
  preferencesApi,
  profile,
  publicStats,
  push,
  readStoredReferralRef,
  savedJobs,
  subscription,
  tiers,
  userPreferences,
} from "../api";

const API_BASE = "http://localhost:8000/api/v1";

function jsonResponse(body: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(body), {
    status: init.status ?? 200,
    headers: { "Content-Type": "application/json", ...init.headers },
  });
}

describe("apiFetch", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns parsed JSON on success", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ ok: true }));
    const data = await apiFetch<{ ok: boolean }>("/health");
    expect(data).toEqual({ ok: true });
    expect(fetch).toHaveBeenCalledWith(
      `${API_BASE}/health`,
      expect.objectContaining({ headers: expect.objectContaining({ "Content-Type": "application/json" }) }),
    );
  });

  it("returns undefined for 204 No Content", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 204 }));
    const data = await apiFetch<void>("/resource", { method: "DELETE" });
    expect(data).toBeUndefined();
  });

  it("sends Authorization when token is provided", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ id: "u1" }));
    await apiFetch("/profile", { token: "tok-abc" });
    const [, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer tok-abc");
  });

  it("stringifies plain object bodies", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ ok: true }));
    await apiFetch("/analytics/events", {
      method: "POST",
      token: "t",
      body: { event: "click", properties: { page: "home" } },
    });
    const [, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit];
    expect(init.body).toBe(JSON.stringify({ event: "click", properties: { page: "home" } }));
  });

  it("passes FormData without re-stringifying", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ ok: true }));
    const form = new FormData();
    form.append("file", "x");
    await apiFetch("/cv/upload", { method: "POST", body: form });
    const [, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit];
    expect(init.body).toBe(form);
  });

  it("attaches X-Device-Token from localStorage", async () => {
    localStorage.setItem(DEVICE_TOKEN_KEY, "device-xyz");
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ message: "ok" }));
    await auth.requestOTP("+260971234567");
    const [, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>)["X-Device-Token"]).toBe("device-xyz");
  });

  it("throws ApiError with machine-readable code on 4xx", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ detail: "email_domain_unverified", user_message: "Verify domain" }, { status: 503 }),
    );
    await expect(apiFetch("/auth/otp/request", { method: "POST" })).rejects.toMatchObject({
      name: "ApiError",
      status: 503,
      code: "email_domain_unverified",
      detail: "Verify domain",
    });
  });

  it("maps 502 gateway errors to a friendly API-unavailable message", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response("upstream error", { status: 502, statusText: "Bad Gateway" }),
    );
    const err = await apiFetch("/broken").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({
      status: 502,
      detail: API_UNAVAILABLE_MESSAGE,
      code: "api_unreachable",
    });
  });

  it("maps fetch network failures to API-unavailable (not raw Failed to fetch)", async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError("Failed to fetch"));
    const err = await apiFetch("/auth/login", { method: "POST" }).catch(
      (e: unknown) => e
    );
    expect(err).toBeInstanceOf(ApiError);
    expect(err).toMatchObject({
      status: 0,
      detail: API_UNAVAILABLE_MESSAGE,
      code: "api_unreachable",
    });
  });

  it("maps machine code without user_message to friendly delivery copy", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ detail: "whatsapp_unavailable" }, { status: 503 }),
    );
    await expect(apiFetch("/auth/otp/request", { method: "POST" })).rejects.toMatchObject({
      status: 503,
      code: "whatsapp_unavailable",
      detail: "Delivery is temporarily unavailable. Please try again.",
    });
  });
});

describe("ApiError", () => {
  it("exposes status, detail, and optional code", () => {
    const err = new ApiError(422, "invalid_phone", "invalid_phone");
    expect(err).toBeInstanceOf(Error);
    expect(err.status).toBe(422);
    expect(err.detail).toBe("invalid_phone");
    expect(err.code).toBe("invalid_phone");
  });
});

describe("auth", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    localStorage.clear();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("POSTs phone to /auth/login", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ access_token: "a", refresh_token: "r", user_id: "u1" }),
    );
    const tokens = await auth.login("+260971234567");
    expect(tokens.user_id).toBe("u1");
    const [url, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit];
    expect(url).toBe(`${API_BASE}/auth/login`);
    expect(init.method).toBe("POST");
    expect(JSON.parse(String(init.body))).toEqual({ phone: "+260971234567" });
  });

  it("POSTs channel to /auth/otp/request when provided", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ message: "sent" }));
    await auth.requestOTP("+260971234567", "whatsapp");
    expect(JSON.parse(String(vi.mocked(fetch).mock.calls[0][1].body))).toEqual({
      phone: "+260971234567",
      channel: "whatsapp",
    });
  });

  it("POSTs verify payload with consent and referral", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ access_token: "a", refresh_token: "r", user_id: "u1" }),
    );
    await auth.verifyOTP("+260971234567", "123456", {
      consentAccepted: true,
      email: "a@b.com",
      rememberDevice: true,
      referralRef: "  ref123  ",
    });
    expect(JSON.parse(String(vi.mocked(fetch).mock.calls[0][1].body))).toEqual({
      phone: "+260971234567",
      code: "123456",
      consent_accepted: true,
      email: "a@b.com",
      remember_device: true,
      referral_ref: "ref123",
    });
  });
});

describe("profile & subscription", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("GETs /profile with bearer token", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        id: "u1",
        phone: "+260971234567",
        full_name: "A",
        email: null,
        skills: [],
        cv_uploaded: false,
        subscription_tier: "free",
      }),
    );
    const p = await profile.get("tok");
    expect(p.id).toBe("u1");
    expect(vi.mocked(fetch).mock.calls[0][0]).toBe(`${API_BASE}/profile`);
  });

  it("PATCHes profile fields", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        id: "u1",
        phone: "+260971234567",
        full_name: "New",
        email: null,
        skills: [],
        cv_uploaded: false,
        subscription_tier: "free",
      }),
    );
    await profile.update("tok", { full_name: "New" });
    expect(JSON.parse(String(vi.mocked(fetch).mock.calls[0][1].body))).toEqual({
      full_name: "New",
    });
  });

  it("GETs subscription", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        tier: "starter",
        matches_used: 1,
        matches_limit: 50,
        active: true,
        expires_at: null,
      }),
    );
    const sub = await subscription.get("tok");
    expect(sub.tier).toBe("starter");
  });
});

describe("health & tiers", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("health.check hits /health", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ status: "healthy" }));
    const h = await health.check();
    expect(h.status).toBe("healthy");
  });

  it("tiers.list works without token", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ tiers: [] }));
    const list = await tiers.list();
    expect(list.tiers).toEqual([]);
    const [, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit];
    expect((init.headers as Record<string, string>).Authorization).toBeUndefined();
  });
});

describe("additional API modules", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
    localStorage.setItem("zed_cv_token", "stored-jwt");
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
  });

  it("jobs.list forwards query params and auth token", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ jobs: [], total: 0, page: 1, pages: 0 }),
    );
    await jobs.list({
      page: 2,
      search: "engineer",
      employment_type: ["full_time"],
      has_salary: true,
      saved_only: true,
    });
    const [url] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit];
    expect(url).toContain("page=2");
    expect(url).toContain("search=engineer");
    expect(url).toContain("employment_type=full_time");
    expect(url).toContain("has_salary=true");
    expect(url).toContain("saved_only=true");
  });

  it("matches.refresh POSTs to /matches/refresh", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ matches: [], remaining_quota: 5 }),
    );
    await matches.refresh("tok", 40);
    const [url, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/matches/refresh?min_score=40");
    expect(init.method).toBe("POST");
  });

  it("matches.dismiss POSTs to /matches/{id}/dismiss with optional reason", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ match_id: "match-1", status: "dismissed", reason: "not_relevant" }),
    );
    await matches.dismiss("tok", "match-1", { reason: "not_relevant" });
    const [url, init] = vi.mocked(fetch).mock.calls[0] as [string, RequestInit];
    expect(url).toBe(`${API_BASE}/matches/match-1/dismiss`);
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ reason: "not_relevant" }));
  });

  it("preferencesApi.patch sends JSON body", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        target_roles: ["Dev"],
        target_roles_source: "user_provided",
        salary_min: null,
        salary_max: null,
        salary_currency: "ZMW",
        salary_frequency: null,
        preferred_work_arrangement: "remote",
        willing_to_relocate: false,
        acceptable_regions: [],
        languages: [],
        industries: [],
        extras: {},
        auto_populated_at: null,
        manually_updated_at: null,
        auto_populated_fields: [],
      }),
    );
    await preferencesApi.patch("tok", { target_roles: ["Dev"] });
    expect(JSON.parse(String(vi.mocked(fetch).mock.calls[0][1].body))).toEqual({
      target_roles: ["Dev"],
    });
  });

  it("savedJobs.save POSTs to /jobs/:id/save", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ saved: true }));
    await savedJobs.save("tok", "job-1");
    expect(vi.mocked(fetch).mock.calls[0][0]).toBe(`${API_BASE}/jobs/job-1/save`);
  });

  it("savedJobs.list GETs /users/me/saved-jobs with applications", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        jobs: [],
        applications: [
          {
            job: {
              id: "job-1",
              title: "Analyst",
              company: "ACME",
              location: "Lusaka",
              closing_date: null,
              quality_score: 80,
              skills: [],
              description: null,
            },
            application_status: "applied",
            status_updated_at: "2026-05-01T00:00:00Z",
            application_notes: null,
            interview_date: null,
          },
        ],
      }),
    );
    const res = await savedJobs.list("tok");
    expect(res.applications?.[0]?.application_status).toBe("applied");
    expect(vi.mocked(fetch).mock.calls[0][0]).toBe(`${API_BASE}/users/me/saved-jobs`);
  });

  it("savedJobs.updateStatus PATCHes kanban status", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        job_id: "job-1",
        application_status: "interviewing",
        status_updated_at: "2026-05-02T00:00:00Z",
        application_notes: "Phone screen",
        interview_date: "2026-05-10",
      }),
    );
    const res = await savedJobs.updateStatus("tok", "job-1", {
      status: "interviewing",
      notes: "Phone screen",
      interview_date: "2026-05-10",
    });
    expect(res.application_status).toBe("interviewing");
    expect(vi.mocked(fetch).mock.calls[0][0]).toBe(
      `${API_BASE}/users/me/saved-jobs/job-1/status`,
    );
  });

  it("cv.analyze POSTs empty JSON object", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        overall: 80,
        skills: 70,
        format: 90,
        impact: 75,
        strengths: [],
        improvements: [],
        cached: false,
      }),
    );
    await cv.analyze("tok");
    expect(vi.mocked(fetch).mock.calls[0][0]).toBe(`${API_BASE}/cv/analyze`);
  });

  it("contact.submit is unauthenticated POST", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ success: true, message: "Thanks" }),
    );
    const result = await contact.submit({
      name: "A",
      email: "a@b.com",
      message: "Hi",
    });
    expect(result.success).toBe(true);
  });

  it("publicStats.get hits /stats/public", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ jobs_active: 1, avg_skills_matched: 2, hours_saved_total: 3 }),
    );
    const stats = await publicStats.get();
    expect(stats.jobs_active).toBe(1);
  });

  it("userPreferences.get and patch", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse({
          whatsapp_number: null,
          location: null,
          currency: "ZMW",
          alert_frequency: "daily",
          whatsapp_verified: false,
          preferred_notification_channel: "email",
          whatsapp_digest_available: false,
          quiet_hours_start: "20:00",
          quiet_hours_end: "07:00",
          profile_visible_to_employers: true,
          hidden_employer_name: null,
          notify_product_updates: false,
          display_timezone: "Africa/Lusaka",
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          whatsapp_number: null,
          location: null,
          currency: "USD",
          alert_frequency: "daily",
          whatsapp_verified: false,
          preferred_notification_channel: "email",
          whatsapp_digest_available: false,
          quiet_hours_start: "20:00",
          quiet_hours_end: "07:00",
          profile_visible_to_employers: true,
          hidden_employer_name: null,
          notify_product_updates: true,
          display_timezone: "Africa/Lusaka",
        }),
      );
    const prefs = await userPreferences.get("tok");
    expect(prefs.currency).toBe("ZMW");
    const updated = await userPreferences.patch("tok", { currency: "USD" });
    expect(updated.currency).toBe("USD");
  });

  it("autoMatchPreferences.get", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({
        auto_match_enabled: true,
        notification_channels: { whatsapp: true, email: true },
      }),
    );
    const prefs = await autoMatchPreferences.get("tok");
    expect(prefs.auto_match_enabled).toBe(true);
  });

  it("dataRights.getConsentStatus", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      jsonResponse({ consents: { terms_of_service: true }, last_updated: {} }),
    );
    const status = await dataRights.getConsentStatus("tok");
    expect(status.consents.terms_of_service).toBe(true);
  });

  it("analytics.trackEvent POSTs event payload", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(new Response(null, { status: 204 }));
    await analytics.trackEvent("tok", "page_view", { path: "/jobs" });
    expect(JSON.parse(String(vi.mocked(fetch).mock.calls[0][1].body))).toEqual({
      event: "page_view",
      properties: { path: "/jobs" },
    });
  });

  it("push.subscribe POSTs keys", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ ok: true, message: "ok" }));
    await push.subscribe("tok", {
      endpoint: "https://push.example",
      keys: { p256dh: "a", auth: "b" },
    });
    expect(vi.mocked(fetch).mock.calls[0][0]).toBe(`${API_BASE}/push/subscribe`);
  });

  it("admin.stats and profile skill routes", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse({
          users_total: 1,
          users_active_30d: 1,
          subscriptions_active: 1,
          subscriptions_paid: 0,
          jobs_total: 1,
          jobs_active: 1,
          jobs_expired: 0,
          matches_24h: 0,
          matches_total: 0,
          revenue_ngwee_30d: 0,
          revenue_ngwee_total: 0,
          pending_review_count: 0,
          jobs_deactivated: 0,
          jobs_need_review: 0,
          jobs_active_public: 120,
        }),
      )
      .mockResolvedValueOnce(jsonResponse({ skills: [{ name: "Python", proficiency: "advanced", source: "manual" }] }));
    const stats = await admin.stats("tok");
    expect(stats.users_total).toBe(1);
    await profile.addSkill("tok", { name: "Python" });
    expect(vi.mocked(fetch).mock.calls[1][0]).toBe(`${API_BASE}/profile/skills`);
  });

  it("jobs.get and profile.getPreferences", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse({
          id: "j1",
          title: "Dev",
          company: "Co",
          location: null,
          closing_date: null,
          quality_score: 1,
          skills: [],
          description: null,
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({
          whatsapp_alerts: true,
          email_notifications_enabled: true,
          language: "en",
        }),
      );
    const job = await jobs.get("j1");
    expect(job.title).toBe("Dev");
    const prefs = await profile.getPreferences("tok");
    expect(prefs.language).toBe("en");
  });

  it("coverLetter.generateForMatch and matches.get", async () => {
    vi.mocked(fetch)
      .mockResolvedValueOnce(
        jsonResponse({
          content: "Dear",
          word_count: 1,
          version_id: "v1",
          version_number: 1,
        }),
      )
      .mockResolvedValueOnce(
        jsonResponse({ matches: [], remaining_quota: 3 }),
      );
    await coverLetter.generateForMatch("tok", "match-1");
    const list = await matches.get("tok");
    expect(list.remaining_quota).toBe(3);
  });
});

describe("referral storage helpers", () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it("readStoredReferralRef returns trimmed value", () => {
    sessionStorage.setItem(REFERRAL_STORAGE_KEY, "  abc  ");
    expect(readStoredReferralRef()).toBe("abc");
  });

  it("readStoredReferralRef returns null when empty", () => {
    sessionStorage.setItem(REFERRAL_STORAGE_KEY, "   ");
    expect(readStoredReferralRef()).toBeNull();
  });

  it("clearStoredReferralRef removes the key", () => {
    sessionStorage.setItem(REFERRAL_STORAGE_KEY, "x");
    clearStoredReferralRef();
    expect(sessionStorage.getItem(REFERRAL_STORAGE_KEY)).toBeNull();
  });
});

describe("admin API", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("admin.scrapeTargets.list calls correctly", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse([{ id: "1" }]));
    await admin.scrapeTargets.list("tok");
    expect(fetch).toHaveBeenCalledWith(`${API_BASE}/admin/scrape-targets/list`, expect.objectContaining({ method: "GET" }));
  });

  it("admin.scrapeTargets.add calls correctly", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ ok: true }));
    await admin.scrapeTargets.add({ url: "x", company_name: "y", cron_interval_hours: 24 }, "tok");
    expect(fetch).toHaveBeenCalledWith(`${API_BASE}/admin/scrape-targets/add`, expect.objectContaining({ method: "POST" }));
  });

  it("admin.scrapeTargets.toggle calls correctly", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ ok: true }));
    await admin.scrapeTargets.toggle("1", false, "tok");
    expect(fetch).toHaveBeenCalledWith(`${API_BASE}/admin/scrape-targets/toggle/1`, expect.objectContaining({ method: "PATCH" }));
  });

  it("admin.scrapeTargets.delete calls correctly", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ ok: true }));
    await admin.scrapeTargets.delete("1", "tok");
    expect(fetch).toHaveBeenCalledWith(`${API_BASE}/admin/scrape-targets/1`, expect.objectContaining({ method: "DELETE" }));
  });

  it("admin.scrapeTargets.trigger calls correctly", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ processed: 1 }));
    await admin.scrapeTargets.trigger("tok");
    expect(fetch).toHaveBeenCalledWith(`${API_BASE}/admin/scrape-targets/trigger`, expect.objectContaining({ method: "POST" }));
  });

  it("admin.scrapeTargets.force calls correctly", async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse({ jobs_found: 1 }));
    await admin.scrapeTargets.force("1", "tok");
    expect(fetch).toHaveBeenCalledWith(`${API_BASE}/admin/scrape-targets/force`, expect.objectContaining({ method: "POST" }));
  });
});
