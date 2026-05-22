import { describe, expect, it } from "vitest";
import { pageMetadata, siteDefaultMetadata } from "../site-metadata";

describe("siteDefaultMetadata", () => {
  it("sets the branded default title and OpenGraph tags", () => {
    expect(siteDefaultMetadata.title).toMatchObject({
      default: "ZedApply - Zambian AI Job Matching",
      template: "%s — ZedApply",
    });
    expect(siteDefaultMetadata.openGraph).toMatchObject({
      title: "ZedApply - Zambian AI Job Matching",
      siteName: "ZedApply",
      type: "website",
    });
  });
});

describe("pageMetadata", () => {
  it("returns a short tab title and matching social cards", () => {
    const meta = pageMetadata({
      title: "Jobs",
      description: "Browse open roles across Zambia.",
    });
    expect(meta.title).toBe("Jobs");
    expect(meta.openGraph?.title).toBe("Jobs — ZedApply");
    expect(meta.twitter?.title).toBe("Jobs — ZedApply");
  });
});
