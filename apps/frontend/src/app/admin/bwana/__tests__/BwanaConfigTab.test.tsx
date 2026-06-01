import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { BwanaConfigTab } from "../BwanaConfigTab";
import { adminBwana } from "@/lib/api";

vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...actual,
    adminBwana: {
      getConfig: vi.fn(),
      patchConfig: vi.fn(),
      preview: vi.fn(),
      testEscalation: vi.fn(),
    },
  };
});

const mockConfig = {
  chatbot_display_name: "Bwana",
  operator_display_name: "ZedApply Support",
  support_email: "support@zedapply.com",
  support_phone: "+260971234567",
  escalation_whatsapp_phone: "+260971234567",
  escalation_sla_hours: 24,
  human_escalation_reply_template: "Human {email}",
  unsatisfied_reply_template: "Sorry {email}",
  contact_admin_reply_template: "Contact {email}",
  public_knowledge_extra: "",
  faq_intents_json: [],
  enable_email_escalation: true,
  enable_user_escalation_ack: true,
  user_escalation_ack_template: "Thanks {ticket_id}",
};

describe("BwanaConfigTab", () => {
  beforeEach(() => {
    vi.mocked(adminBwana.getConfig).mockResolvedValue(mockConfig);
    vi.mocked(adminBwana.preview).mockResolvedValue({
      system_prompt_preview: "You are Bwana, ZedApply's chatbot",
      char_count: 1200,
    });
    vi.mocked(adminBwana.patchConfig).mockResolvedValue(mockConfig);
    vi.mocked(adminBwana.testEscalation).mockResolvedValue({
      status: "sent",
      detail: "ok",
    });
  });

  it("loads config and shows support email field", async () => {
    render(<BwanaConfigTab token="test-token" />);
    await waitFor(() => {
      expect(screen.getByDisplayValue("support@zedapply.com")).toBeInTheDocument();
    });
  });

  it("rejects invalid email on save client-side via API error", async () => {
    vi.mocked(adminBwana.patchConfig).mockRejectedValue(new Error("Invalid email"));
    render(<BwanaConfigTab token="test-token" />);
    await waitFor(() => screen.getByDisplayValue("support@zedapply.com"));
    const emailInput = screen.getByDisplayValue("support@zedapply.com");
    await userEvent.clear(emailInput);
    await userEvent.type(emailInput, "not-an-email");
    await userEvent.click(screen.getByRole("button", { name: /save config/i }));
    await waitFor(() => {
      expect(adminBwana.patchConfig).toHaveBeenCalled();
    });
  });
});
