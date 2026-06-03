import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ProfileCompletenessChecklist } from "../ProfileCompletenessChecklist";
import type { ProfileCompletenessItem } from "@/lib/profileCompleteness";
import type { JobPreferences, UserProfile } from "@/lib/api";

vi.mock("@/components/ui/Icon", () => ({
  Icon: () => <span data-testid="icon" />,
}));

vi.mock("@/lib/toast", () => ({
  notify: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

const preferencesPatch = vi.fn();
const profilePatch = vi.fn();

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    preferencesApi: {
      ...actual.preferencesApi,
      get: vi.fn().mockResolvedValue(mockPreferences()),
      patch: (...args: unknown[]) => preferencesPatch(...args),
    },
    profile: {
      ...actual.profile,
      update: (...args: unknown[]) => profilePatch(...args),
    },
  };
});

function mockProfile(overrides: Partial<UserProfile> = {}): UserProfile {
  return {
    id: "user-1",
    phone: "+260971234567",
    full_name: "",
    email: "",
    skills: [],
    cv_uploaded: false,
    subscription_tier: "free",
    years_experience: 0,
    education: [],
    certifications: [],
    cv_sections: null,
    ...overrides,
  };
}

function mockPreferences(): JobPreferences {
  return {
    target_roles: [],
    target_roles_source: "user_provided",
    salary_min: null,
    salary_max: null,
    salary_currency: "ZMW",
    salary_frequency: null,
    preferred_work_arrangement: null,
    willing_to_relocate: false,
    acceptable_regions: [],
    languages: [],
    industries: [],
    extras: {},
    auto_populated_at: null,
    manually_updated_at: null,
    auto_populated_fields: [],
  };
}

const incompleteItems: ProfileCompletenessItem[] = [
  {
    id: "preferred_work_arrangements",
    label: "Work arrangement",
    weight: 1,
    complete: false,
    hint: "Choose remote, hybrid, on-site, or any",
    tab: "preferences",
  },
  {
    id: "notice_period",
    label: "Notice period",
    weight: 0.5,
    complete: false,
    hint: "Tell recruiters how soon you can start",
    tab: "preferences",
  },
];

describe("ProfileCompletenessChecklist", () => {
  beforeEach(() => {
    preferencesPatch.mockReset();
    profilePatch.mockReset();
    preferencesPatch.mockImplementation(async () => mockPreferences());
  });

  it("renders nothing when all items are complete", () => {
    const complete = incompleteItems.map((item) => ({ ...item, complete: true }));
    const { container } = render(
      <ProfileCompletenessChecklist
        items={complete}
        token="tok"
        profile={mockProfile()}
        preferences={mockPreferences()}
        onProfileSaved={vi.fn()}
        onPreferencesSaved={vi.fn()}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("lists incomplete fields and remaining count", () => {
    render(
      <ProfileCompletenessChecklist
        items={incompleteItems}
        token="tok"
        profile={mockProfile()}
        preferences={mockPreferences()}
        onProfileSaved={vi.fn()}
        onPreferencesSaved={vi.fn()}
      />,
    );
    expect(screen.getByText(/complete your profile \(2 remaining\)/i)).toBeInTheDocument();
    expect(screen.getByText("Work arrangement")).toBeInTheDocument();
  });

  it("opens the field modal when Add is clicked", async () => {
    const user = userEvent.setup();
    render(
      <ProfileCompletenessChecklist
        items={incompleteItems}
        token="tok"
        profile={mockProfile()}
        preferences={mockPreferences()}
        onProfileSaved={vi.fn()}
        onPreferencesSaved={vi.fn()}
      />,
    );
    await user.click(screen.getByRole("button", { name: /add work arrangement/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /work arrangement/i })).toBeInTheDocument();
  });

  it("saves work arrangement from the modal and notifies parent", async () => {
    const user = userEvent.setup();
    const onPreferencesSaved = vi.fn();
    const savedPrefs = mockPreferences();
    savedPrefs.preferred_work_arrangement = "remote";
    preferencesPatch.mockResolvedValue(savedPrefs);

    render(
      <ProfileCompletenessChecklist
        items={incompleteItems}
        token="tok"
        profile={mockProfile()}
        preferences={mockPreferences()}
        onProfileSaved={vi.fn()}
        onPreferencesSaved={onPreferencesSaved}
      />,
    );

    await user.click(screen.getByRole("button", { name: /add work arrangement/i }));
    const select = screen.getByLabelText(/preferred arrangement/i);
    await user.selectOptions(select, "remote");
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => {
      expect(preferencesPatch).toHaveBeenCalledWith("tok", {
        preferred_work_arrangement: "remote",
      });
    });
    expect(onPreferencesSaved).toHaveBeenCalledWith(savedPrefs);
    await waitFor(() => {
      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });
  });

  it("saves notice period from the modal", async () => {
    const user = userEvent.setup();
    const onPreferencesSaved = vi.fn();
    const savedPrefs = mockPreferences();
    savedPrefs.extras = { notice_period: "2 weeks" };
    preferencesPatch.mockResolvedValue(savedPrefs);

    render(
      <ProfileCompletenessChecklist
        items={incompleteItems}
        token="tok"
        profile={mockProfile()}
        preferences={mockPreferences()}
        onProfileSaved={vi.fn()}
        onPreferencesSaved={onPreferencesSaved}
      />,
    );

    await user.click(screen.getByRole("button", { name: /add notice period/i }));
    await user.selectOptions(screen.getByRole("combobox", { name: /notice period/i }), "2 weeks");
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => {
      expect(preferencesPatch).toHaveBeenCalledWith("tok", {
        extras: { notice_period: "2 weeks" },
      });
    });
    expect(onPreferencesSaved).toHaveBeenCalled();
  });

  it("saves full name via profile API from the modal", async () => {
    const user = userEvent.setup();
    const onProfileSaved = vi.fn();
    const updated = mockProfile({ full_name: "Jane Doe" });
    profilePatch.mockResolvedValue(updated);

    render(
      <ProfileCompletenessChecklist
        items={[
          {
            id: "full_name",
            label: "Full name",
            weight: 1,
            complete: false,
            hint: "Add in Account settings",
            tab: "cv",
          },
        ]}
        token="tok"
        profile={mockProfile()}
        preferences={mockPreferences()}
        onProfileSaved={onProfileSaved}
        onPreferencesSaved={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: /add full name/i }));
    const nameInput = screen.getByRole("textbox", { name: /full name/i });
    await user.clear(nameInput);
    await user.type(nameInput, "Jane Doe");
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => {
      expect(profilePatch).toHaveBeenCalledWith("tok", { full_name: "Jane Doe" });
    });
    expect(onProfileSaved).toHaveBeenCalledWith(updated);
  });

  it("saves education level from the modal", async () => {
    const user = userEvent.setup();
    const onPreferencesSaved = vi.fn();
    const savedPrefs = mockPreferences();
    savedPrefs.extras = { education_level: "Bachelor's degree" };
    preferencesPatch.mockResolvedValue(savedPrefs);

    render(
      <ProfileCompletenessChecklist
        items={[
          {
            id: "education_level",
            label: "Education level",
            weight: 1,
            complete: false,
            hint: "Select your highest qualification",
            tab: "preferences",
          },
        ]}
        token="tok"
        profile={mockProfile()}
        preferences={mockPreferences()}
        onProfileSaved={vi.fn()}
        onPreferencesSaved={onPreferencesSaved}
      />,
    );

    await user.click(screen.getByRole("button", { name: /add education level/i }));
    await user.selectOptions(
      screen.getByRole("combobox", { name: /highest qualification/i }),
      "Bachelor's degree",
    );
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    await waitFor(() => {
      expect(preferencesPatch).toHaveBeenCalledWith("tok", {
        extras: { education_level: "Bachelor's degree" },
      });
    });
    expect(onPreferencesSaved).toHaveBeenCalled();
  });
});
