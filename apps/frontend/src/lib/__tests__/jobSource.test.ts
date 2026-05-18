import { describe, it, expect } from "vitest";
import { formatJobSource } from "../jobSource";

describe("formatJobSource", () => {
  it("returns 'Posted by admin' for manual", () => {
    expect(formatJobSource("manual")).toBe("Posted by admin");
  });

  it("returns 'Scraped from {host}' for scraper with a source_url", () => {
    expect(formatJobSource("scraper", "https://linkedin.com/jobs/123")).toBe(
      "Scraped from linkedin.com",
    );
    expect(
      formatJobSource("scraper", "https://www.gozambiajobs.com/listing/abc"),
    ).toBe("Scraped from gozambiajobs.com");
  });

  it("returns bare 'Scraped' for scraper when source_url is missing or invalid", () => {
    expect(formatJobSource("scraper")).toBe("Scraped");
    expect(formatJobSource("scraper", null)).toBe("Scraped");
    expect(formatJobSource("scraper", "not-a-url")).toBe("Scraped");
  });

  it("returns 'Scraped from WhatsApp' for ocr regardless of source_url", () => {
    expect(formatJobSource("ocr")).toBe("Scraped from WhatsApp");
    expect(formatJobSource("ocr", "https://anything.example")).toBe(
      "Scraped from WhatsApp",
    );
  });

  it("returns 'Partner post' for partner", () => {
    expect(formatJobSource("partner")).toBe("Partner post");
  });

  it("returns 'Listed externally' when source is null/undefined", () => {
    expect(formatJobSource(null)).toBe("Listed externally");
    expect(formatJobSource(undefined)).toBe("Listed externally");
  });

  it("returns 'Listed externally' for unknown future source values", () => {
    expect(formatJobSource("rss")).toBe("Listed externally");
  });
});
