import { describe, expect, it } from "vitest";
import { countWords, COVER_LETTER_WORD_SOFT_LIMIT } from "../countWords";

describe("countWords", () => {
  it("counts words in trimmed text", () => {
    expect(countWords("one two three")).toBe(3);
    expect(countWords("")).toBe(0);
  });

  it("exposes soft limit constant", () => {
    expect(COVER_LETTER_WORD_SOFT_LIMIT).toBe(600);
  });
});
