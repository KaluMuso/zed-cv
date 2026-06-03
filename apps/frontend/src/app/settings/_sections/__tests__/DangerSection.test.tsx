import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { notify } from "@/lib/toast";

const {
  mockProfileGet,
  mockAutoMatchGet,
  mockAutoMatchPatch,
  mockDeleteAccount,
  mockLogout,
  mockPush,
  mockSetZust,
  MockApiError,
} = vi.hoisted(() => {
  class MockApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
    }
  }
  return {
    mockProfileGet: vi.fn(),
    mockAutoMatchGet: vi.fn(),
    mockAutoMatchPatch: vi.fn(),
    mockDeleteAccount: vi.fn(),
    mockLogout: vi.fn(),
    mockPush: vi.fn(),
    mockSetZust: vi.fn(),
    MockApiError,
  };
});

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}));

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({
    token: "test-token",
    logout: mockLogout,
    isAuthenticated: true,
    isLoading: false,
  }),
}));

vi.mock("@/lib/zustand-store", () => ({
  useAppStore: () => ({ setProfile: mockSetZust }),
}));

vi.mock("@/lib/api", () => ({
  profile: {
    get: (...args: unknown[]) => mockProfileGet(...args),
  },
  autoMatchPreferences: {
    get: (...args: unknown[]) => mockAutoMatchGet(...args),
    patch: (...args: unknown[]) => mockAutoMatchPatch(...args),
  },
  me: {
    deleteAccount: (...args: unknown[]) => mockDeleteAccount(...args),
  },
  ApiError: MockApiError,
}));

vi.mock("@/lib/toast", () => ({
  notify: {
    error: vi.fn(),
    custom: { success: vi.fn() },
  },
}));

import { DangerSection } from "../DangerSection";

describe("DangerSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockProfileGet.mockResolvedValue({
      id: "u1",
      phone: "+260971234567",
      full_name: "Jane",
      email: "j@x.com",
      skills: [],
      cv_uploaded: true,
      subscription_tier: "free",
    });
    mockAutoMatchGet.mockResolvedValue({ auto_match_enabled: true });
    mockAutoMatchPatch.mockResolvedValue({ auto_match_enabled: false });
    mockDeleteAccount.mockResolvedValue({ deleted: true, already_deleted: false, user_id: "u1" });
  });

  it("requires exact phone confirmation before delete", async () => {
    const user = userEvent.setup();
    render(<DangerSection />);
    await waitFor(() => expect(screen.getByRole("button", { name: /delete account/i })).toBeEnabled());

    await user.click(screen.getByRole("button", { name: /delete account/i }));
    const deleteBtn = screen.getByRole("button", { name: /delete forever/i });
    expect(deleteBtn).toBeDisabled();

    await user.type(screen.getByRole("textbox"), "+260971234567");
    expect(deleteBtn).toBeEnabled();

    await user.click(deleteBtn);
    await waitFor(() => {
      expect(mockDeleteAccount).toHaveBeenCalledWith("test-token", "+260971234567");
    });
    expect(mockLogout).toHaveBeenCalled();
    expect(mockPush).toHaveBeenCalledWith("/");
  });

  it("shows error when phone confirmation does not match", async () => {
    mockDeleteAccount.mockRejectedValueOnce(new MockApiError(400, "bad phone"));

    const user = userEvent.setup();
    render(<DangerSection />);
    await waitFor(() => expect(screen.getByRole("button", { name: /delete account/i })).toBeEnabled());
    await user.click(screen.getByRole("button", { name: /delete account/i }));
    await user.type(screen.getByRole("textbox"), "+260971234567");
    await user.click(screen.getByRole("button", { name: /delete forever/i }));

    await waitFor(() => {
      expect(screen.getByText(/doesn't match the phone number/i)).toBeInTheDocument();
    });
    expect(mockLogout).not.toHaveBeenCalled();
  });

  it("pauses auto-match", async () => {
    const user = userEvent.setup();
    render(<DangerSection />);
    await waitFor(() => expect(screen.getByRole("button", { name: /^pause$/i })).toBeEnabled());

    await user.click(screen.getByRole("button", { name: /^pause$/i }));
    await waitFor(() => {
      expect(mockAutoMatchPatch).toHaveBeenCalledWith("test-token", { auto_match_enabled: false });
    });
    expect(notify.custom.success).toHaveBeenCalled();
  });
});
