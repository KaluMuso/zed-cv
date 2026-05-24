import { describe, expect, it } from "vitest";
import { buildJobPostingJsonLd } from "@/lib/job-posting-jsonld";
import type { Job } from "@/lib/api";

const baseJob: Job = {
  id: "11111111-1111-1111-1111-111111111111",
  title: "Software Engineer",
  company: "Acme Zambia",
  location: "Lusaka",
  closing_date: "2026-12-31",
  posted_at: "2026-05-01T10:00:00Z",
  quality_score: 80,
  skills: ["python"],
  description: "<p>Build APIs</p>",
  salary_min: 1250000,
  salary_max: 2500000,
  employment_type: "full_time",
  pay_frequency: "monthly",
  currency: "ZMW",
  apply_url: "https://example.com/apply",
  apply_email: "hr@acme.zm",
};

describe("buildJobPostingJsonLd", () => {
  it("emits full JobPosting when job fields are present", () => {
    const ld = buildJobPostingJsonLd(baseJob);
    expect(ld["@type"]).toBe("JobPosting");
    expect(ld.title).toBe("Software Engineer");
    expect(ld.datePosted).toBe("2026-05-01T10:00:00Z");
    expect(ld.validThrough).toBe("2026-12-31");
    expect(ld.employmentType).toBe("FULL_TIME");
    expect(ld.directApply).toBe(true);
    expect(ld.hiringOrganization).toEqual({
      "@type": "Organization",
      name: "Acme Zambia",
    });
    expect(ld.jobLocation).toMatchObject({
      address: { addressLocality: "Lusaka", addressCountry: "ZM" },
    });
    const salary = ld.baseSalary as {
      currency: string;
      value: { minValue: number; maxValue: number; unitText: string };
    };
    expect(salary.currency).toBe("ZMW");
    expect(salary.value.minValue).toBe(12500);
    expect(salary.value.maxValue).toBe(25000);
    expect(salary.value.unitText).toBe("MONTH");
  });

  it("omits optional blocks when data is missing (no fabricated defaults)", () => {
    const sparse: Job = {
      ...baseJob,
      company: null,
      location: null,
      closing_date: null,
      posted_at: null,
      employment_type: null,
      salary_min: null,
      salary_max: null,
      apply_url: null,
      apply_email: null,
    };
    const ld = buildJobPostingJsonLd(sparse);
    expect(ld.hiringOrganization).toBeUndefined();
    expect(ld.jobLocation).toBeUndefined();
    expect(ld.validThrough).toBeUndefined();
    expect(ld.datePosted).toBeUndefined();
    expect(ld.employmentType).toBeUndefined();
    expect(ld.baseSalary).toBeUndefined();
    expect(ld.directApply).toBeUndefined();
    expect(ld.applicationContact).toBeUndefined();
  });

  it("strips HTML from description", () => {
    const ld = buildJobPostingJsonLd(baseJob);
    expect(ld.description).toBe("Build APIs");
  });
});
