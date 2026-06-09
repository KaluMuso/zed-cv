import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LoginPage } from "../LoginPage";

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) => <a href={href}>{children}</a>,
}));

describe("LoginPage", () => {
  const baseProps = {
    fullName: "",
    phoneDigits: "",
    email: "",
    consentChecked: false,
    loading: false,
    error: "",
    otpChannel: "email" as const,
    isFreeTier: true,
    onFullNameChange: vi.fn(),
    onPhoneChange: vi.fn(),
    onEmailChange: vi.fn(),
    onConsentChange: vi.fn(),
    onOtpChannelChange: vi.fn(),
    onSubmit: vi.fn((e: React.FormEvent) => e.preventDefault()),
  };

  it("disables submit until phone, email, and consent are valid", () => {
    render(<LoginPage {...baseProps} />);
    expect(screen.getByRole("button", { name: /send code/i })).toBeDisabled();
  });

  it("enables submit when phone has 9 digits, email, name, and consent", () => {
    render(
      <LoginPage
        {...baseProps}
        fullName="Test User"
        phoneDigits="971234567"
        email="user@example.com"
        consentChecked
      />,
    );
    expect(screen.getByRole("button", { name: /send code/i })).toBeEnabled();
  });

  it("shows phone validation error from parent", () => {
    render(
      <LoginPage
        {...baseProps}
        error="Enter a valid Zambian number (9 digits after +260)"
      />,
    );
    expect(
      screen.getByText(/enter a valid zambian number/i),
    ).toBeInTheDocument();
  });

  it("fires onSubmit when form is submitted with valid input", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn((e: React.FormEvent) => e.preventDefault());
    render(
      <LoginPage
        {...baseProps}
        fullName="Test User"
        phoneDigits="971234567"
        email="user@example.com"
        consentChecked
        onSubmit={onSubmit}
      />,
    );
    await user.click(screen.getByRole("button", { name: /send code/i }));
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });

  it("calls onPhoneChange when digits are entered", async () => {
    const user = userEvent.setup();
    const onPhoneChange = vi.fn();
    render(<LoginPage {...baseProps} onPhoneChange={onPhoneChange} />);
    const phoneInput = screen.getByLabelText(/phone/i);
    await user.type(phoneInput, "971234567");
    expect(onPhoneChange).toHaveBeenCalled();
  });

  it("disables submit while loading", () => {
    render(
      <LoginPage
        {...baseProps}
        fullName="Test User"
        phoneDigits="971234567"
        email="user@example.com"
        consentChecked
        loading
      />,
    );
    expect(screen.getByRole("button", { name: /send code/i })).toBeDisabled();
  });

  it("calls onOtpChannelChange when WhatsApp is selected on free tier", async () => {
    const user = userEvent.setup();
    const onOtpChannelChange = vi.fn();
    render(
      <LoginPage
        {...baseProps}
        isFreeTier
        onOtpChannelChange={onOtpChannelChange}
      />,
    );
    const whatsapp = screen.getByRole("radio", { name: /whatsapp/i });
    await user.click(whatsapp);
    expect(onOtpChannelChange).toHaveBeenCalledWith("whatsapp");
  });

  it("requires consent checkbox before submit is enabled", async () => {
    const user = userEvent.setup();
    const onConsentChange = vi.fn();
    render(
      <LoginPage
        {...baseProps}
        fullName="Test User"
        phoneDigits="971234567"
        email="user@example.com"
        onConsentChange={onConsentChange}
      />,
    );
    expect(screen.getByRole("button", { name: /send code/i })).toBeDisabled();
    await user.click(screen.getByRole("checkbox"));
    expect(onConsentChange).toHaveBeenCalledWith(true);
  });

  it("disables submit when full name is less than 2 characters", () => {
    render(
      <LoginPage
        {...baseProps}
        fullName="A"
        phoneDigits="971234567"
        email="user@example.com"
        consentChecked
      />,
    );
    expect(screen.getByRole("button", { name: /send code/i })).toBeDisabled();
  });
});
