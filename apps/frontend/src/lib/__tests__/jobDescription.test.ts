import { describe, it, expect } from "vitest";
import {
  isHeadingLine,
  splitDescriptionChunks,
} from "../jobDescription";

describe("isHeadingLine", () => {
  it("accepts common job-description section headings", () => {
    expect(isHeadingLine("Job Purpose")).toBe(true);
    expect(isHeadingLine("Key Responsibilities")).toBe(true);
    expect(isHeadingLine("Qualifications")).toBe(true);
    expect(isHeadingLine("Required Skills")).toBe(true);
    expect(isHeadingLine("About the Role")).toBe(true);
    expect(isHeadingLine("How to Apply")).toBe(true);
  });

  it("accepts a heading with a trailing colon", () => {
    expect(isHeadingLine("Job Purpose:")).toBe(true);
  });

  it("accepts ALL CAPS headings (common in OCR'd WhatsApp flyers)", () => {
    expect(isHeadingLine("RESPONSIBILITIES")).toBe(true);
    expect(isHeadingLine("ABOUT THE COMPANY")).toBe(true);
  });

  it("rejects sentences ending in punctuation", () => {
    expect(isHeadingLine("This is a sentence.")).toBe(false);
    expect(isHeadingLine("Manage the team!")).toBe(false);
    expect(isHeadingLine("Manage the team,")).toBe(false);
  });

  it("rejects long lines that are clearly body paragraphs", () => {
    expect(
      isHeadingLine(
        "We are looking for a senior accountant to join our growing finance team in Lusaka",
      ),
    ).toBe(false);
  });

  it("rejects mixed-case body text", () => {
    expect(isHeadingLine("we offer a competitive package")).toBe(false);
    expect(isHeadingLine("Strong communication skills required")).toBe(false);
  });

  it("rejects empty and whitespace-only lines", () => {
    expect(isHeadingLine("")).toBe(false);
    expect(isHeadingLine("   ")).toBe(false);
  });
});

describe("splitDescriptionChunks", () => {
  it("returns an empty array for empty input", () => {
    expect(splitDescriptionChunks("")).toEqual([]);
  });

  it("splits headings out of body text", () => {
    const text =
      "Job Purpose\nLead the finance team and report to the CFO.\n\n" +
      "Key Responsibilities\nManage monthly close. Prepare board packs.";

    const chunks = splitDescriptionChunks(text);

    expect(chunks).toEqual([
      { type: "heading", text: "Job Purpose" },
      {
        type: "paragraph",
        text: "Lead the finance team and report to the CFO.",
      },
      { type: "heading", text: "Key Responsibilities" },
      {
        type: "paragraph",
        text: "Manage monthly close. Prepare board packs.",
      },
    ]);
  });

  it("preserves blank-line paragraph breaks within a section", () => {
    const text = "Qualifications\nDegree in finance.\n\nCIMA preferred.";
    const chunks = splitDescriptionChunks(text);
    expect(chunks).toEqual([
      { type: "heading", text: "Qualifications" },
      { type: "paragraph", text: "Degree in finance." },
      { type: "paragraph", text: "CIMA preferred." },
    ]);
  });

  it("returns the whole input as one paragraph when no headings exist", () => {
    const text =
      "We are looking for a driver to handle daily deliveries. Apply by Friday.";
    const chunks = splitDescriptionChunks(text);
    expect(chunks).toHaveLength(1);
    expect(chunks[0]).toEqual({ type: "paragraph", text });
  });

  it("strips trailing colons from heading text", () => {
    const chunks = splitDescriptionChunks("About Us:\nA growing fintech.");
    expect(chunks[0]).toEqual({ type: "heading", text: "About Us" });
  });
});
