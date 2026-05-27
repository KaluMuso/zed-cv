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
      template: "%s - Zed Apply",
    });
    expect(siteDefaultMetadata.openGraph).toMatchObject({
      title: SITE_DEFAULT_TITLE,
      siteName: "Zed Apply",
      type: "website",
    });
    const images = siteDefaultMetadata.openGraph?.images;
    const firstImage = Array.isArray(images) ? images[0] : images;
    expect(firstImage).toMatchObject({
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
    expect(meta.openGraph?.title).toBe("Jobs - Zed Apply");
    expect(meta.twitter?.title).toBe("Jobs - Zed Apply");
  });
});
