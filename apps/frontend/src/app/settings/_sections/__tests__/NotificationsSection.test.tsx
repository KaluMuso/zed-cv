import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { notify } from "@/lib/toast";

const mockUserPrefsGet = vi.fn();
const mockUserPrefsPatch = vi.fn();
const mockAutoMatchGet = vi.fn();
const mockAutoMatchPatch = vi.fn();

vi.mock("@/lib/auth", () => ({
  useAuth: () => ({ token: "test-token", isAuthenticated: true, isLoading: false }),
}));

const dashPrefs = {
  whatsapp_number: "+260971234567",
  location: "Lusaka",
  currency: "ZMW" as const,
  alert_frequency: "daily" as const,
  whatsapp_verified: true,
  preferred_notification_channel: "email" as const,
  whatsapp_digest_available: true,
  quiet_hours_start: "20:00:00",
  quiet_hours_end: "07:00:00",
  profile_visible_to_employers: true,
  hidden_employer_name: null,
  notify_product_updates: false,
  display_timezone: "Africa/Lusaka",
};

const autoPrefs = {
  auto_match_enabled: true,
  notification_channels: { whatsapp: true, email: true },
};

vi.mock("@/lib/api", () => ({
  userPreferences: {
    get: (...args: unknown[]) => mockUserPrefsGet(...args),
    patch: (...args: unknown[]) => mockUserPrefsPatch(...args),
  },
  autoMatchPreferences: {
    get: (...args: unknown[]) => mockAutoMatchGet(...args),
    patch: (...args: unknown[]) => mockAutoMatchPatch(...args),
  },
}));

vi.mock("@/lib/toast", () => ({
  notify: {
    error: vi.fn(),
    custom: { success: vi.fn() },
  },
}));

import { NotificationsSection } from "../NotificationsSection";

describe("NotificationsSection", () => {
  beforeEach(() => {
    mockUserPrefsGet.mockResolvedValue(dashPrefs);
    mockAutoMatchGet.mockResolvedValue(autoPrefs);
    mockUserPrefsPatch.mockImplementation(async (_token, data) => ({
      ...dashPrefs,
      ...data,
    }));
    mockAutoMatchPatch.mockResolvedValue({
      ...autoPrefs,
      auto_match_enabled: false,
    });
  });

  it("loads channel options after fetch", async () => {
    render(<NotificationsSection />);
    await waitFor(() => {
      expect(screen.getByText("Email only")).toBeInTheDocument();
    });
    expect(screen.getByText("WhatsApp only")).toBeInTheDocument();
  });

  it("saves WhatsApp channel when digest is available", async () => {
    const user = userEvent.setup();
    render(<NotificationsSection />);
    await waitFor(() => expect(screen.getByText("Email only")).toBeInTheDocument());

    const whatsappRadio = screen.getByRole("radio", { name: /whatsapp only/i });
    await user.click(whatsappRadio);

    await waitFor(() => {
      expect(mockUserPrefsPatch).toHaveBeenCalledWith("test-token", {
        preferred_notification_channel: "whatsapp",
      });
    });
    expect(notify.custom.success).toHaveBeenCalledWith("Notification preference saved.");
  });

  it("disables paid channels on free tier and shows upgrade hint", async () => {
    mockUserPrefsGet.mockResolvedValueOnce({
      ...dashPrefs,
      whatsapp_digest_available: false,
    });
    render(<NotificationsSection />);
    await waitFor(() => expect(screen.getByText(/upgrade to starter/i)).toBeInTheDocument());

    expect(screen.getByRole("radio", { name: /whatsapp only/i })).toBeDisabled();
    expect(screen.getByRole("radio", { name: /email and whatsapp/i })).toBeDisabled();
    expect(screen.getByRole("radio", { name: /email only/i })).not.toBeDisabled();
  });

  it("toggles auto-match", async () => {
    const user = userEvent.setup();
    render(<NotificationsSection />);
    await waitFor(() => expect(screen.getByText("Enable auto-match")).toBeInTheDocument());

    const toggles = screen.getAllByRole("checkbox");
    const autoMatchToggle = toggles[toggles.length - 1];
    await user.click(autoMatchToggle);

    await waitFor(() => {
      expect(mockAutoMatchPatch).toHaveBeenCalledWith("test-token", {
        auto_match_enabled: false,
      });
    });
  });

  it("updates weekly job alerts and quiet hours", async () => {
    const user = userEvent.setup();
    render(<NotificationsSection />);
    await waitFor(() => expect(screen.getByText("Weekly job alerts")).toBeInTheDocument());

    await user.click(screen.getByRole("checkbox", { name: /weekly job alerts/i }));
    await waitFor(() => {
      expect(mockUserPrefsPatch).toHaveBeenCalledWith("test-token", {
        alert_frequency: "weekly",
      });
    });

    const quietStart = screen.getByDisplayValue("20:00");
    await user.clear(quietStart);
    await user.type(quietStart, "21:30");
    await waitFor(() => {
      expect(mockUserPrefsPatch).toHaveBeenCalledWith("test-token", {
        quiet_hours_start: "21:30",
      });
    });
  });

  it("toggles product update notifications", async () => {
    const user = userEvent.setup();
    render(<NotificationsSection />);
    await waitFor(() => expect(screen.getByText("Product updates and offers")).toBeInTheDocument());

    await user.click(screen.getByRole("checkbox", { name: /product updates and offers/i }));
    await waitFor(() => {
      expect(mockUserPrefsPatch).toHaveBeenCalledWith("test-token", {
        notify_product_updates: true,
      });
    });
  });

  it("mutes alerts and disables weekly on the same view", async () => {
    mockUserPrefsGet.mockResolvedValueOnce({
      ...dashPrefs,
      alert_frequency: "weekly",
    });
    mockUserPrefsPatch.mockImplementation(async (_token, data) => ({
      ...dashPrefs,
      alert_frequency: "weekly",
      ...data,
    }));

    const user = userEvent.setup();
    render(<NotificationsSection />);
    await waitFor(() => expect(screen.getByText("Weekly job alerts")).toBeInTheDocument());

    expect(screen.getByRole("checkbox", { name: /weekly job alerts/i })).toBeChecked();

    await user.click(screen.getByRole("checkbox", { name: /new match notifications/i }));
    await waitFor(() => {
      expect(mockUserPrefsPatch).toHaveBeenCalledWith("test-token", {
        alert_frequency: "muted",
      });
    });
    await waitFor(() => {
      expect(screen.getByRole("checkbox", { name: /weekly job alerts/i })).toBeDisabled();
    });
    expect(screen.getByRole("checkbox", { name: /weekly job alerts/i })).not.toBeChecked();
  });

  it("restores daily alerts when re-enabling after mute", async () => {
    mockUserPrefsGet.mockResolvedValueOnce({
      ...dashPrefs,
      alert_frequency: "muted",
    });

    const user = userEvent.setup();
    render(<NotificationsSection />);
    await waitFor(() => expect(screen.getByText("New match notifications")).toBeInTheDocument());

    await user.click(screen.getByRole("checkbox", { name: /new match notifications/i }));
    await waitFor(() => {
      expect(mockUserPrefsPatch).toHaveBeenCalledWith("test-token", {
        alert_frequency: "daily",
      });
    });
  });
});
