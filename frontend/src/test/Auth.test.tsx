import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { BrowserRouter, MemoryRouter, Routes, Route } from "react-router-dom";
import { describe, it, expect, beforeEach } from "vitest";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { ProtectedRoute } from "@/routes";
import { useAuthStore } from "@/store/useAuthStore";

describe("Authentication & Route Guards", () => {
  beforeEach(() => {
    useAuthStore.setState({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      loading: false,
    });
  });

  it("validates login form requiring valid email and password", async () => {
    render(
      <BrowserRouter>
        <LoginPage />
      </BrowserRouter>
    );

    const submitBtn = screen.getByRole("button", { name: /Log In/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Please enter a valid email address/i)).toBeInTheDocument();
    });
  });

  it("validates registration password requirements", async () => {
    render(
      <BrowserRouter>
        <RegisterPage />
      </BrowserRouter>
    );

    const nameInput = screen.getByLabelText(/Full Name/i);
    const emailInput = screen.getByLabelText(/Email Address/i);
    const passwordInput = screen.getByPlaceholderText(/At least 8 characters with a number/i);
    const submitBtn = screen.getByRole("button", { name: /Create Account/i });

    fireEvent.change(nameInput, { target: { value: "Aarav Test" } });
    fireEvent.change(emailInput, { target: { value: "aarav@test.com" } });
    fireEvent.change(passwordInput, { target: { value: "short" } }); // too short, no number

    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Password must be at least 8 characters/i)).toBeInTheDocument();
    });
  });

  it("guards protected routes redirecting unauthenticated users to login", () => {
    useAuthStore.setState({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      loading: false,
    });

    render(
      <MemoryRouter initialEntries={["/home"]}>
        <Routes>
          <Route path="/login" element={<div>Login Page Guarded</div>} />
          <Route
            path="/home"
            element={
              <ProtectedRoute>
                <div>Protected Content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>
    );

    expect(screen.getByText("Login Page Guarded")).toBeInTheDocument();
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });

  it("renders protected content when user is authenticated", () => {
    useAuthStore.setState({
      user: {
        id: "123",
        name: "Verified User",
        email: "verified@test.com",
        role: "newcomer",
        is_active: true,
        is_verified: true,
        created_at: new Date().toISOString(),
      },
      accessToken: "mock_token",
      isAuthenticated: true,
      loading: false,
    });

    render(
      <MemoryRouter initialEntries={["/home"]}>
        <ProtectedRoute>
          <div>Protected Content</div>
        </ProtectedRoute>
      </MemoryRouter>
    );

    expect(screen.getByText("Protected Content")).toBeInTheDocument();
  });
});
