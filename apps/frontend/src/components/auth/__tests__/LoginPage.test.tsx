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
    phoneDigits: "",
    email: "",
    consentChecked: false,
    loading: false,
    error: "",
    otpChannel: "email" as const,
    isFreeTier: true,
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

  it("enables submit when phone has 9 digits, email, and consent", () => {
    render(
      <LoginPage
        {...baseProps}
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
});
