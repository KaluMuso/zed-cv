import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { JobCreateWizard } from "../JobCreateWizard";
import { DRAFT_STORAGE_KEY } from "../useDraftPersistence";

// Each test starts with a clean localStorage so a draft from a prior
// test doesn't leak in via rehydration on mount.
beforeEach(() => {
  window.localStorage.clear();
});

afterEach(() => {
  cleanup();
  window.localStorage.clear();
  vi.useRealTimers();
});

// Role-based queries throughout — getByLabelText with a substring regex
// like /company/i was matching the progress indicator's aria-label
// "Step 5: Company context". Scoping by role ('textbox', 'combobox',
// 'spinbutton') makes the intent unambiguous.

const titleField = () => screen.getByRole("textbox", { name: "Title" });
const companyField = () => screen.getByRole("textbox", { name: "Company" });
const locationField = () => screen.getByRole("textbox", { name: "Location" });
const employmentSelect = () =>
  screen.getByRole("combobox", { name: "Employment type" });
const arrangementSelect = () =>
  screen.getByRole("combobox", { name: "Work arrangement" });
const hybridField = () =>
  screen.getByRole("spinbutton", { name: "Hybrid days per week" });
const salaryMinField = () =>
  screen.getByRole("spinbutton", { name: "Salary minimum" });
const salaryMaxField = () =>
  screen.getByRole("spinbutton", { name: "Salary maximum" });
const nextButton = () => screen.getByRole("button", { name: /^next$/i });
const backButton = () => screen.getByRole("button", { name: /^back$/i });

// Fill the five required step 1 fields with valid values.
async function fillStep1(user: ReturnType<typeof userEvent.setup>) {
  await user.type(titleField(), "Senior accountant");
  await user.type(companyField(), "Zambia Ltd");
  await user.type(locationField(), "Lusaka");
  await user.selectOptions(employmentSelect(), "full_time");
  await user.selectOptions(arrangementSelect(), "on_site");
}

describe("JobCreateWizard", () => {
  it("renders step 1 by default", () => {
    render(<JobCreateWizard />);
    expect(
      screen.getByRole("heading", { name: /step 1 of 5/i }),
    ).toBeInTheDocument();
    expect(titleField()).toBeInTheDocument();
    expect(arrangementSelect()).toBeInTheDocument();
  });

  it("keeps Next disabled until step 1 is valid", async () => {
    const user = userEvent.setup();
    render(<JobCreateWizard />);

    expect(nextButton()).toBeDisabled();

    await user.type(titleField(), "Senior accountant");
    expect(nextButton()).toBeDisabled();

    await user.type(companyField(), "Zambia Ltd");
    await user.type(locationField(), "Lusaka");
    await user.selectOptions(employmentSelect(), "full_time");
    await user.selectOptions(arrangementSelect(), "on_site");

    expect(nextButton()).toBeEnabled();
  });

  it("advances to step 2 when Next is clicked on valid step 1", async () => {
    const user = userEvent.setup();
    render(<JobCreateWizard />);

    await fillStep1(user);
    await user.click(nextButton());

    expect(
      screen.getByRole("heading", { name: /step 2 of 5/i }),
    ).toBeInTheDocument();
    expect(salaryMinField()).toBeInTheDocument();
  });

  it("Back returns to step 1 with previously entered values", async () => {
    const user = userEvent.setup();
    render(<JobCreateWizard />);

    await fillStep1(user);
    await user.click(nextButton());
    expect(
      screen.getByRole("heading", { name: /step 2 of 5/i }),
    ).toBeInTheDocument();

    await user.click(backButton());

    expect(
      screen.getByRole("heading", { name: /step 1 of 5/i }),
    ).toBeInTheDocument();
    expect(titleField()).toHaveValue("Senior accountant");
    expect(locationField()).toHaveValue("Lusaka");
  });

  it("disables Next on step 2 with help text", async () => {
    const user = userEvent.setup();
    render(<JobCreateWizard />);

    await fillStep1(user);
    await user.click(nextButton());

    expect(nextButton()).toBeDisabled();
    expect(
      screen.getByText(/continue building in the next pr/i),
    ).toBeInTheDocument();
  });

  it("reveals hybrid_days_per_week only when work_arrangement is hybrid", async () => {
    const user = userEvent.setup();
    render(<JobCreateWizard />);

    expect(
      screen.queryByRole("spinbutton", { name: "Hybrid days per week" }),
    ).not.toBeInTheDocument();

    await user.selectOptions(arrangementSelect(), "hybrid");

    expect(hybridField()).toBeInTheDocument();
  });

  it("shows inline error when salary_max < salary_min", async () => {
    const user = userEvent.setup();
    render(<JobCreateWizard />);

    await fillStep1(user);
    await user.click(nextButton());

    await user.type(salaryMinField(), "1000");
    await user.type(salaryMaxField(), "500");
    await user.click(nextButton());

    expect(
      await screen.findByText(/maximum must be greater than or equal/i),
    ).toBeInTheDocument();
    expect(salaryMaxField()).toHaveAttribute("aria-invalid", "true");
  });

  it("progress indicator: clicking a reachable step navigates; locked steps don't", async () => {
    const user = userEvent.setup();
    render(<JobCreateWizard />);

    await fillStep1(user);
    await user.click(nextButton());
    expect(
      screen.getByRole("heading", { name: /step 2 of 5/i }),
    ).toBeInTheDocument();

    // Step 1 dot is a button — clicking jumps back.
    const step1Dot = screen.getByRole("button", {
      name: "Step 1: Basic info",
    });
    await user.click(step1Dot);
    expect(
      screen.getByRole("heading", { name: /step 1 of 5/i }),
    ).toBeInTheDocument();

    // Step 5 is not a button at all — it renders as a disabled span.
    expect(
      screen.queryByRole("button", { name: /step 5: company context/i }),
    ).not.toBeInTheDocument();
  });

  it("persists draft to localStorage after debounce window", async () => {
    // Real timers — fake timers tangle with React's internal scheduler
    // in jsdom and the test hangs. The debounce window is short (400ms)
    // so a real wait is tolerable and the assertion is deterministic.
    const user = userEvent.setup();
    render(<JobCreateWizard />);

    await user.type(titleField(), "Driver");

    // Wait past the 400ms debounce window.
    await new Promise((resolve) => setTimeout(resolve, 500));

    const raw = window.localStorage.getItem(DRAFT_STORAGE_KEY);
    expect(raw).not.toBeNull();
    const parsed = JSON.parse(raw as string) as {
      data: { title?: string };
    };
    expect(parsed.data.title).toBe("Driver");
  });

  it("rehydrates from existing draft on mount", () => {
    window.localStorage.setItem(
      DRAFT_STORAGE_KEY,
      JSON.stringify({
        version: 1,
        savedAt: new Date().toISOString(),
        data: { title: "Pre-existing draft", company: "Old Co" },
      }),
    );

    render(<JobCreateWizard />);

    expect(titleField()).toHaveValue("Pre-existing draft");
    expect(companyField()).toHaveValue("Old Co");
  });

  it("discards drafts older than 7 days", () => {
    const eightDaysAgo = new Date(Date.now() - 8 * 24 * 60 * 60 * 1000);
    window.localStorage.setItem(
      DRAFT_STORAGE_KEY,
      JSON.stringify({
        version: 1,
        savedAt: eightDaysAgo.toISOString(),
        data: { title: "Stale", company: "Old Co" },
      }),
    );

    render(<JobCreateWizard />);

    expect(titleField()).toHaveValue("");
    expect(companyField()).toHaveValue("");
    // Stale draft is also removed so we don't re-read it next mount.
    expect(window.localStorage.getItem(DRAFT_STORAGE_KEY)).toBeNull();
  });

  it("clears hybrid_days when switching away from hybrid", async () => {
    const user = userEvent.setup();
    render(<JobCreateWizard />);

    await user.selectOptions(arrangementSelect(), "hybrid");
    await user.type(hybridField(), "3");
    expect(hybridField()).toHaveValue(3);

    await user.selectOptions(arrangementSelect(), "remote");
    expect(
      screen.queryByRole("spinbutton", { name: "Hybrid days per week" }),
    ).not.toBeInTheDocument();

    // Switching back shouldn't bring the stale value back.
    await user.selectOptions(arrangementSelect(), "hybrid");
    expect(hybridField()).toHaveValue(null);
  });

  it("benefits list grows and shrinks via Add and Remove buttons", async () => {
    const user = userEvent.setup();
    render(<JobCreateWizard />);

    await fillStep1(user);
    await user.click(nextButton());

    const benefitsFieldset = screen.getByRole("group", { name: /benefits/i });
    expect(
      within(benefitsFieldset).queryAllByRole("textbox"),
    ).toHaveLength(0);

    await user.click(
      within(benefitsFieldset).getByRole("button", { name: /add benefit/i }),
    );
    const firstBenefit = within(benefitsFieldset).getByRole("textbox", {
      name: /benefit 1/i,
    });
    await user.type(firstBenefit, "Medical insurance");
    expect(firstBenefit).toHaveValue("Medical insurance");

    await user.click(
      within(benefitsFieldset).getByRole("button", {
        name: /remove benefit 1/i,
      }),
    );
    expect(
      within(benefitsFieldset).queryAllByRole("textbox"),
    ).toHaveLength(0);
  });
});
