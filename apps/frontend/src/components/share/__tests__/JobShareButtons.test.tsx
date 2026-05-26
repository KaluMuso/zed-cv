import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { JobShareButtons } from "../JobShareButtons";

const job = {
  id: "job-1",
  title: "Senior Accountant",
  company: "ZamBank",
  location: "Lusaka",
};

describe("JobShareButtons", () => {
  beforeEach(() => {
    vi.stubGlobal("open", vi.fn());
  });

  it("renders WhatsApp, LinkedIn, Facebook, X, and copy link", () => {
    render(<JobShareButtons job={job} />);
    expect(screen.getByLabelText("Share on WhatsApp")).toBeTruthy();
    expect(screen.getByLabelText("Share on LinkedIn")).toBeTruthy();
    expect(screen.getByLabelText("Share on Facebook")).toBeTruthy();
    expect(screen.getByLabelText("Share on X")).toBeTruthy();
    expect(screen.getByLabelText("Copy job link")).toBeTruthy();
  });

  it("WhatsApp link includes job title and permalink", () => {
    render(<JobShareButtons job={job} />);
    const wa = screen.getByLabelText("Share on WhatsApp");
    expect(wa.getAttribute("href")).toContain("wa.me");
    expect(wa.getAttribute("href")).toContain(encodeURIComponent("Senior Accountant"));
  });

  it("copies permalink on copy click", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    vi.spyOn(navigator.clipboard, "writeText").mockImplementation(writeText);

    render(<JobShareButtons job={job} />);
    await user.click(screen.getByLabelText("Copy job link"));
    expect(writeText).toHaveBeenCalledWith("https://www.zedapply.com/jobs/job-1");
  });
});
