import { describe, expect, it } from "vitest";

import {
  finalizeAdminJobPayload,
  validateAdminJobApplyContact,
} from "../adminJobValidation";

describe("validateAdminJobApplyContact", () => {
  it("requires at least one apply channel", () => {
    expect(validateAdminJobApplyContact("", "", "")).toMatch(/apply URL/i);
    expect(validateAdminJobApplyContact(undefined, undefined, undefined)).toMatch(
      /contact phone/i,
    );
  });

  it("rejects url and email together", () => {
    expect(
      validateAdminJobApplyContact("https://jobs.example/1", "hr@example.com", ""),
    ).toMatch(/not both/i);
  });

  it("allows phone only", () => {
    expect(validateAdminJobApplyContact("", "", "+260971234567")).toBeNull();
  });

  it("allows url only", () => {
    expect(validateAdminJobApplyContact("https://jobs.example/1", "", "")).toBeNull();
  });
});

describe("finalizeAdminJobPayload", () => {
  it("strips admin_published on create", () => {
    const out = finalizeAdminJobPayload(
      "create",
      { title: "Dev", admin_published: false },
      false,
    );
    expect(out).toEqual({ title: "Dev" });
    expect("admin_published" in out).toBe(false);
  });

  it("sets admin_published from forcePublish on edit", () => {
    const out = finalizeAdminJobPayload(
      "edit",
      { title: "Dev", admin_published: false },
      true,
    );
    expect(out.admin_published).toBe(true);
  });
});
