import { describe, expect, it } from "vitest";
import { stripDescriptionHtml, stripScraperMetadata } from "../jobDetailHtml";

describe("stripScraperMetadata", () => {
  it("removes scraper footer lines", () => {
    const raw = [
      "Key responsibilities",
      "• Sell products",
      "First Posted: 2024-01-01",
      "Scraped from LinkedIn",
    ].join("\n");
    expect(stripScraperMetadata(raw)).toBe(
      ["Key responsibilities", "• Sell products"].join("\n"),
    );
  });
});

describe("stripDescriptionHtml", () => {
  it("strips HTML then scraper lines", () => {
    const html = "<p>Role summary</p><p>Scraped from bestjobs.co</p>";
    expect(stripDescriptionHtml(html)).toBe("Role summary");
  });
});
