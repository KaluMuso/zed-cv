import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ScrapeTargetsTab } from "../ScrapeTargetsTab";

// Mock the admin API
vi.mock("@/lib/api", () => ({
  admin: {
    scrapeTargets: {
      list: vi.fn().mockResolvedValue([
        { id: "1", company_name: "Test Co", url: "https://example.com", is_active: true, cron_interval_hours: 24 }
      ]),
      toggle: vi.fn().mockResolvedValue({}),
      delete: vi.fn().mockResolvedValue({}),
      add: vi.fn().mockResolvedValue({}),
      trigger: vi.fn().mockResolvedValue({ processed: 2 }),
      force: vi.fn().mockResolvedValue({ jobs_found: 5, new_inserted: 3 }),
    }
  }
}));

import { admin } from "@/lib/api";

describe("ScrapeTargetsTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders the table and add button", async () => {
    render(<ScrapeTargetsTab token="fake" />);
    
    expect(
      screen.getByRole("heading", { name: /Scrape Targets/i })
    ).toBeInTheDocument();
    
    expect(
      screen.getByRole("button", { name: /Add Target/i })
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("https://example.com")).toBeInTheDocument();
    });
  });

  it("can toggle a target status", async () => {
    const user = userEvent.setup();
    render(<ScrapeTargetsTab token="fake" />);
    
    await waitFor(() => {
      expect(screen.getByText("https://example.com")).toBeInTheDocument();
    });
    
    const disableButton = screen.getByRole("button", { name: /Disable/i });
    await user.click(disableButton);
    
    expect(admin.scrapeTargets.toggle).toHaveBeenCalledWith("1", false, "fake");
  });

  it("can open add dialog and submit", async () => {
    const user = userEvent.setup();
    render(<ScrapeTargetsTab token="fake" />);
    
    const companyInput = screen.getByPlaceholderText("e.g. Bank of Zambia");
    const urlInput = screen.getByPlaceholderText("https://...");
    
    await user.type(companyInput, "New Co");
    await user.type(urlInput, "https://test.com");
    
    const submitButton = screen.getByRole("button", { name: /Add Target/i });
    await user.click(submitButton);

    await waitFor(() => {
      expect(admin.scrapeTargets.add).toHaveBeenCalledWith(
        expect.objectContaining({ url: "https://test.com", company_name: "New Co" }),
        "fake"
      );
    });
  });

  it("can delete a target", async () => {
    // mock window.confirm
    vi.spyOn(window, "confirm").mockReturnValue(true);
    const user = userEvent.setup();
    render(<ScrapeTargetsTab token="fake" />);
    
    await waitFor(() => {
      expect(screen.getByText("https://example.com")).toBeInTheDocument();
    });
    
    const deleteButton = screen.getByRole("button", { name: /Delete/i });
    await user.click(deleteButton);
    
    expect(admin.scrapeTargets.delete).toHaveBeenCalledWith("1", "fake");
  });

  it("can trigger all due targets", async () => {
    const user = userEvent.setup();
    render(<ScrapeTargetsTab token="fake" />);
    
    const triggerButton = screen.getByRole("button", { name: /Trigger Due Targets/i });
    await user.click(triggerButton);
    
    expect(admin.scrapeTargets.trigger).toHaveBeenCalledWith("fake");
  });

  it("can force scrape a single target", async () => {
    const user = userEvent.setup();
    render(<ScrapeTargetsTab token="fake" />);
    
    await waitFor(() => {
      expect(screen.getByText("https://example.com")).toBeInTheDocument();
    });
    
    const forceButton = screen.getByRole("button", { name: /Force Scrape/i });
    await user.click(forceButton);
    
    expect(admin.scrapeTargets.force).toHaveBeenCalledWith("1", "fake");
  });
});
