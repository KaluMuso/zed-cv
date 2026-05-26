import { describe, expect, it } from "vitest";
import {
  pageMetadata,
  SITE_DEFAULT_TITLE,
  siteDefaultMetadata,
} from "../site-metadata";

describe("siteDefaultMetadata", () => {
  it("sets the branded default title and OpenGraph tags", () => {
    expect(siteDefaultMetadata.title).toMatchObject({
      default: SITE_DEFAULT_TITLE,
      template: "%s | ZedApply",
    });
    expect(siteDefaultMetadata.openGraph).toMatchObject({
      title: SITE_DEFAULT_TITLE,
      siteName: "ZedApply",
      type: "website",
    });
    expect(siteDefaultMetadata.openGraph?.images?.[0]).toMatchObject({
      url: "/api/og",
      width: 1200,
      height: 630,
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
    expect(meta.openGraph?.title).toBe("Jobs | ZedApply");
    expect(meta.twitter?.title).toBe("Jobs | ZedApply");
  });
});
