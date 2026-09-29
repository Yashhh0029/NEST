import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import { describe, it, expect, vi } from "vitest";
import { RequestBox } from "@/components/request/RequestBox";
import { RequestCard } from "@/components/request/RequestCard";
import { UnderstandingChips } from "@/components/request/UnderstandingChips";
import type { NewcomerRequest } from "@/types/request";

describe("Request Box & Understanding Chips", () => {
  it("renders the request box with label and placeholder", () => {
    render(
      <BrowserRouter>
        <RequestBox />
      </BrowserRouter>
    );

    expect(screen.getByText(/What do you need help with\?/i)).toBeInTheDocument();
    expect(
      screen.getByPlaceholderText(/I'm moving to Whitefield for my first IT job/i)
    ).toBeInTheDocument();
  });

  it("renders instant local preview chips when typing location and budget", async () => {
    const user = userEvent.setup();
    render(
      <BrowserRouter>
        <RequestBox />
      </BrowserRouter>
    );

    const textarea = screen.getByPlaceholderText(/I'm moving to Whitefield/i);
    await user.type(textarea, "Need a PG in Whitefield under ₹10,000 with veg food");

    await waitFor(() => {
      expect(screen.getByText("Whitefield")).toBeInTheDocument();
      expect(screen.getByText("PG Accommodation")).toBeInTheDocument();
      expect(screen.getByText("₹10,000")).toBeInTheDocument();
      expect(screen.getByText("Vegetarian")).toBeInTheDocument();
    });
  });

  it("renders authoritative extracted request chips accurately", () => {
    render(
      <UnderstandingChips
        extracted={{
          raw_text: "Need PG in Whitefield under 10k",
          intent: "newcomer_assistance",
          location: { city: "Bengaluru", area: "Whitefield" },
          needs: [{ category: "housing", item: "PG accommodation", matched_text: "PG" }],
          budget: { amount: 10000, currency: "INR", operator: "<=", period: "monthly" },
          preferences: ["Vegetarian"],
          user_context: ["first job"],
          extraction_method: "deterministic_nlp_rule_based_v1",
        }}
      />
    );

    expect(screen.getByText("Whitefield")).toBeInTheDocument();
    expect(screen.getByText("Bengaluru")).toBeInTheDocument();
    expect(screen.getByText("PG accommodation")).toBeInTheDocument();
    expect(screen.getByText(/under ₹10,000/i)).toBeInTheDocument();
  });

  it("renders RequestCard with status, location, and action buttons", () => {
    const mockRequest: NewcomerRequest = {
      id: "req-123",
      user_id: "user-456",
      raw_text: "Looking for 1BHK in Baner under 15k",
      status: "OPEN",
      city: "Pune",
      area: "Baner",
      budget_amount: 15000,
      budget_operator: "<=",
      budget_period: "monthly",
      extraction_method: "deterministic_nlp_rule_based_v1",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    render(
      <BrowserRouter>
        <RequestCard request={mockRequest} onDelete={vi.fn()} onEdit={vi.fn()} />
      </BrowserRouter>
    );

    expect(screen.getByText("OPEN")).toBeInTheDocument();
    expect(screen.getByText(/Baner, Pune/i)).toBeInTheDocument();
    expect(screen.getByText(/under ₹15,000\/monthly/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /View Details/i })).toBeInTheDocument();
  });
});
