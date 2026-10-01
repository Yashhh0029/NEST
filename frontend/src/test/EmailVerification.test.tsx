import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import { describe, it, expect, beforeEach, vi } from "vitest";
import { VerifyEmailPage } from "@/pages/VerifyEmailPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { LoginPage } from "@/pages/LoginPage";
import { authService } from "@/services/auth";
import { useAuthStore } from "@/store/useAuthStore";

describe("Email Verification UX & Protection", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useAuthStore.setState({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      loading: false,
    });
  });

  it("VerifyEmailPage verifies valid token and renders success state", async () => {
    vi.spyOn(authService, "verifyEmail").mockResolvedValueOnce({
      message: "Email verified successfully.",
      email_verified: true,
    });

    render(
      <MemoryRouter initialEntries={["/verify-email?token=valid_test_token_123"]}>
        <Routes>
          <Route path="/verify-email" element={<VerifyEmailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Your NEST account is ready/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Continue to Login/i })).toBeInTheDocument();
    });
  });

  it("VerifyEmailPage shows expired state and resend form when token is expired", async () => {
    vi.spyOn(authService, "verifyEmail").mockRejectedValueOnce({
      response: {
        data: {
          detail: "Verification link has expired. Please request a new verification link.",
        },
      },
    });

    render(
      <MemoryRouter initialEntries={["/verify-email?token=expired_test_token_123"]}>
        <Routes>
          <Route path="/verify-email" element={<VerifyEmailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Verification Link Expired/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Send me a new link/i })).toBeInTheDocument();
    });
  });

  it("VerifyEmailPage shows invalid state when token is invalid or already used", async () => {
    vi.spyOn(authService, "verifyEmail").mockRejectedValueOnce({
      response: {
        data: {
          detail: "Invalid or already used verification link.",
        },
      },
    });

    render(
      <MemoryRouter initialEntries={["/verify-email?token=invalid_or_used_token"]}>
        <Routes>
          <Route path="/verify-email" element={<VerifyEmailPage />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText(/Invalid or Used Link/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Sign In to NEST/i })).toBeInTheDocument();
    });
  });

  it("RegisterPage renders Check your email screen after successful registration without auto-login", async () => {
    vi.spyOn(authService, "register").mockResolvedValueOnce({
      id: "test-uuid",
      name: "New Registrant",
      email: "newregistrant@example.com",
      role: "newcomer",
      is_active: true,
      is_verified: false,
      email_verified: false,
      created_at: new Date().toISOString(),
    });

    render(
      <MemoryRouter>
        <RegisterPage />
      </MemoryRouter>
    );

    const nameInput = screen.getByLabelText(/Full Name/i);
    const emailInput = screen.getByLabelText(/Email Address/i);
    const passwordInput = screen.getByPlaceholderText(/At least 8 characters with a number/i);
    const submitBtn = screen.getByRole("button", { name: /Create Account/i });

    fireEvent.change(nameInput, { target: { value: "New Registrant" } });
    fireEvent.change(emailInput, { target: { value: "newregistrant@example.com" } });
    fireEvent.change(passwordInput, { target: { value: "SecurePass123!" } });

    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Verify your email to continue/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Open Email Inbox/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Resend/i })).toBeInTheDocument();
    });
  });

  it("LoginPage renders Verify your email first card when unverified account attempts login", async () => {
    vi.spyOn(authService, "login").mockRejectedValueOnce({
      response: {
        data: {
          detail: "EMAIL_NOT_VERIFIED",
        },
      },
    });

    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    const emailInput = screen.getByLabelText(/Email Address/i);
    const passwordInput = screen.getByPlaceholderText(/Your password/i);
    const submitBtn = screen.getByRole("button", { name: /Log In/i });

    fireEvent.change(emailInput, { target: { value: "unverified.user@gmail.com" } });
    fireEvent.change(passwordInput, { target: { value: "Password123!" } });

    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Verify your email first/i)).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /Resend/i })).toBeInTheDocument();
    });
  });
});
