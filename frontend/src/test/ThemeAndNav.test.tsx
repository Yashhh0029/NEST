import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import { describe, it, expect, beforeEach } from "vitest";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { BottomNav } from "@/components/layout/BottomNav";
import { EmptyState } from "@/components/ui/EmptyState";
import { useThemeStore } from "@/store/useThemeStore";

describe("Theme Toggle & Navigation UI", () => {
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.classList.remove("dark");
  });

  it("toggles theme between light and dark modes", async () => {
    const user = userEvent.setup();
    useThemeStore.setState({ theme: "light" });

    render(<ThemeToggle />);

    const toggleBtn = screen.getByRole("button", { name: /Switch to dark mode/i });
    await user.click(toggleBtn);

    expect(useThemeStore.getState().theme).toBe("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
  });

  it("renders mobile bottom navigation with touch-friendly links", () => {
    render(
      <BrowserRouter>
        <BottomNav />
      </BrowserRouter>
    );

    const homeLink = screen.getByRole("link", { name: /Home/i });
    const requestsLink = screen.getByRole("link", { name: /Requests/i });
    const profileLink = screen.getByRole("link", { name: /Profile/i });

    expect(homeLink).toHaveAttribute("href", "/home");
    expect(requestsLink).toHaveAttribute("href", "/requests");
    expect(profileLink).toHaveAttribute("href", "/profile");
  });

  it("renders friendly empty states with descriptive action", async () => {
    const user = userEvent.setup();
    let clicked = false;

    render(
      <EmptyState
        title="No matches found"
        description="Try adjusting your search criteria."
        actionLabel="Retry Search"
        onAction={() => {
          clicked = true;
        }}
      />
    );

    expect(screen.getByText("No matches found")).toBeInTheDocument();
    expect(screen.getByText("Try adjusting your search criteria.")).toBeInTheDocument();

    const actionBtn = screen.getByRole("button", { name: /Retry Search/i });
    await user.click(actionBtn);
    expect(clicked).toBe(true);
  });
});
