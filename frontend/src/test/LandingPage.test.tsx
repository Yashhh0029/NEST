import { render, screen } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";
import { describe, it, expect } from "vitest";
import { LandingPage } from "@/pages/LandingPage";

describe("LandingPage Component", () => {
  it("renders the hero headline and tagline accurately", () => {
    render(
      <BrowserRouter>
        <LandingPage />
      </BrowserRouter>
    );

    expect(screen.getByText(/Find Your People\./i)).toBeInTheDocument();
    expect(screen.getByText(/Find Your Place\./i)).toBeInTheDocument();
  });

  it("renders dual primary CTAs for newcomers and helpers", () => {
    render(
      <BrowserRouter>
        <LandingPage />
      </BrowserRouter>
    );

    const newcomerLink = screen.getByRole("link", { name: /I'm New Here/i });
    const helperLink = screen.getByRole("link", { name: /I Want to Help/i });

    expect(newcomerLink).toHaveAttribute("href", "/register?role=newcomer");
    expect(helperLink).toHaveAttribute("href", "/register?role=helper");
  });

  it("explains honest trust language and community problem-solving philosophy", () => {
    render(
      <BrowserRouter>
        <LandingPage />
      </BrowserRouter>
    );

    expect(screen.getByText(/Built for Community Problem-Solving/i)).toBeInTheDocument();
    expect(screen.getByText(/No fake vanity metrics/i)).toBeInTheDocument();
    expect(screen.getByText(/Honest trust language/i)).toBeInTheDocument();
  });
});
