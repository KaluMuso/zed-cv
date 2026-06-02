import { describe, expect, it } from "vitest";
import {
  buildEmailIntroduction,
  isAggregatorApplyUrl,
  resolveApplyAction,
  resolveApplyActionOrSupport,
  resolveApplyContactMethods,
  resolveApplyUrl,
} from "@/lib/applyLink";

describe("resolveApplyAction", () => {
  it("apply_link_email_mode_opens_modal_not_mailto", () => {
    const action = resolveApplyAction({
      title: "Supervisor",
      company: "Mika Meats",
      apply_email: "recruitments@mikameats.com",
      apply_source: "description_email",
    });
    expect(action?.label).toBe("Apply");
    expect(action?.href).toBe("#");
    expect(action?.external).toBe(false);
  });

  it("apply_link_url_mode_opens_external", () => {
    const action = resolveApplyAction({
      title: "Analyst",
      apply_url: "https://jobs.example.com/apply",
    });
    expect(action?.label).toBe("Apply on company site");
    expect(action?.href).toBe("https://jobs.example.com/apply");
    expect(action?.external).toBe(true);
  });

  it("resolveApplyUrl_alias_matches_resolveApplyAction", () => {
    const job = {
      title: "Analyst",
      apply_url: "https://jobs.example.com/apply",
    };
    expect(resolveApplyUrl(job)).toEqual(resolveApplyAction(job));
  });

  it("skips_aggregator_apply_url_and_falls_through_to_email", () => {
    const action = resolveApplyAction({
      title: "Clerk",
      apply_url: "https://www.jobwebzambia.com/jobs/123",
      apply_email: "hr@employer.co.zm",
    });
    expect(action?.label).toBe("Apply");
    expect(action?.href).toBe("#");
    expect(isAggregatorApplyUrl("https://jobwebzambia.com/x")).toBe(true);
  });

  it("returns_null_when_no_structured_contact", () => {
    const action = resolveApplyAction({
      title: "Role",
      source_url: "https://aggregator.example/job/1",
    });
    expect(action).toBeNull();
  });

  it("prefers_url_over_email", () => {
    const action = resolveApplyAction({
      title: "Role",
      apply_url: "https://jobs.example.com/apply",
      apply_email: "hr@co.com",
    });
    expect(action?.label).toBe("Apply on company site");
    expect(action?.secondary).toBeUndefined();
  });

  it("phone_contact_uses_modal_apply_affordance", () => {
    const action = resolveApplyAction({
      title: "Driver",
      contact_phone: "0971234567",
    });
    expect(action?.label).toBe("Apply");
    expect(action?.href).toBe("#");
    expect(action?.secondary).toBeUndefined();
  });
});

describe("buildEmailIntroduction", () => {
  it("includes_role_and_company", () => {
    const intro = buildEmailIntroduction({
      title: "Analyst",
      company: "Acme",
    });
    expect(intro).toContain("Analyst");
    expect(intro).toContain("Acme");
    expect(intro).toContain("ZedApply");
  });
});

describe("resolveApplyContactMethods", () => {
  it("lists_url_email_and_phone_without_duplicating_primary", () => {
    const methods = resolveApplyContactMethods({
      title: "Role",
      apply_url: "https://careers.example.com/apply",
      apply_email: "hr@co.com",
      contact_phone: "0971234567",
    });
    expect(methods.map((m) => m.kind)).toEqual([
      "website",
      "email",
      "phone",
      "whatsapp",
    ]);
    expect(methods.find((m) => m.kind === "email")?.href).toBeUndefined();
    expect(methods.find((m) => m.kind === "email")?.copyValue).toBe("hr@co.com");
  });
});

describe("resolveApplyActionOrSupport", () => {
  it("falls_back_to_support_mail_when_no_contact", () => {
    const action = resolveApplyActionOrSupport({
      title: "Role",
      source_url: "https://aggregator.example/job/1",
    });
    expect(action.label).toBe("Contact Support");
    expect(action.applySource).toBe("source_fallback");
    expect(action.href).toMatch(/^mailto:support@zedapply\.com/);
  });
});
