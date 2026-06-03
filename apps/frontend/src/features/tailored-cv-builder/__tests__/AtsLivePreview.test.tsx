import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { AtsLivePreview } from "../AtsLivePreview";
import { DEFAULT_DRAFT } from "../store";
import { PDF_SKILLS_SEPARATOR, PREVIEW_MAX_VISIBLE_SKILLS } from "../skillsDisplay";

function makeSkillList(count: number): string[] {
  return Array.from({ length: count }, (_, i) => `Skill ${i + 1}`);
}

describe("AtsLivePreview", () => {
  it("caps screen tags at 18 and shows +N more when skills overflow", () => {
    const skills = makeSkillList(20);
    const draft = { ...DEFAULT_DRAFT, skills };

    render(<AtsLivePreview draft={draft} />);

    const skillsSection = screen.getByText("Skills").closest("details");
    expect(skillsSection).toHaveAttribute("open");

    const tagRow = skillsSection?.querySelector(".cv-skills-tags");
    expect(tagRow).not.toBeNull();
    const tagChips = tagRow?.querySelectorAll(".cv-skill-tag");
    expect(tagChips?.length).toBe(PREVIEW_MAX_VISIBLE_SKILLS + 1);
    expect(screen.getByText("+2 more")).toBeInTheDocument();
    expect(screen.queryByText("Skill 19")).not.toBeInTheDocument();
    expect(screen.queryByText("Skill 20")).not.toBeInTheDocument();

    const printLine = skillsSection?.querySelector(".cv-skills-line");
    expect(printLine?.textContent).toBe(skills.join(PDF_SKILLS_SEPARATOR));
  });

  it("renders draft skills in the Skills section (not collapsed empty)", () => {
    const draft = {
      ...DEFAULT_DRAFT,
      skills: ["IFRS", "Excel", "SAP", "Month-end Close"],
    };

    render(<AtsLivePreview draft={draft} />);

    const skillsSection = screen.getByText("Skills").closest("details");
    expect(skillsSection).toHaveAttribute("open");

    expect(screen.getByText("IFRS")).toBeInTheDocument();
    expect(screen.getByText("Excel")).toBeInTheDocument();
    expect(screen.getByText("SAP")).toBeInTheDocument();

    const printLine = document.querySelector(".cv-skills-line");
    expect(printLine?.textContent).toContain("IFRS");
    expect(printLine?.textContent).toContain("Excel");
    expect(printLine?.textContent).toContain("Month-end Close");
  });

  it("omits Skills section when draft has no skills", () => {
    const draft = { ...DEFAULT_DRAFT, skills: [] };
    render(<AtsLivePreview draft={draft} />);
    expect(screen.queryByText("Skills")).not.toBeInTheDocument();
  });
});
