import { describe, expect, it } from "vitest";
import { resolveApplyAction } from "@/lib/applyLink";

describe("resolveApplyAction", () => {
  it("apply_link_email_mode_opens_mailto", () => {
    const action = resolveApplyAction({
      title: "Supervisor",
      company: "Mika Meats",
      apply_email: "recruitments@mikameats.com",
      apply_source: "description_email",
    });
    expect(action.label).toBe("Apply via email");
    expect(action.href).toMatch(/^mailto:recruitments@mikameats\.com/);
    expect(action.href).toContain("subject=");
    expect(action.external).toBe(false);
  });

  it("apply_link_url_mode_opens_external", () => {
    const action = resolveApplyAction({
      title: "Analyst",
      apply_url: "https://jobs.example.com/apply",
    });
    expect(action.label).toBe("Apply now");
    expect(action.href).toBe("https://jobs.example.com/apply");
    expect(action.external).toBe(true);
  });

  it("prefers_url_with_email_secondary", () => {
    const action = resolveApplyAction({
      title: "Role",
      apply_url: "https://jobs.example.com/apply",
      apply_email: "hr@co.com",
    });
    expect(action.label).toBe("Apply now");
    expect(action.secondary?.label).toBe("Or email instead →");
    expect(action.secondary?.href).toMatch(/^mailto:hr@co\.com/);
  });
});
