import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { NearbyRequestsFeed } from "@/components/home/NearbyRequestsFeed";
import { requestsService } from "@/services/requests";
import type { NearbyRequestItem } from "@/types/request";

const sampleNearbyRequests: NearbyRequestItem[] = [
  {
    id: "req-1",
    user_id: "user-1",
    requester_name: "Rahul Sharma",
    raw_text: "Need PG in Koramangala under 15k",
    city: "Bengaluru",
    area: "Koramangala",
    budget_amount: 15000,
    budget_period: "monthly",
    distance_km: 1.5,
    needs: ["Housing"],
    match_reasons: ["Location proximity (1.5 km)", "Budget match"],
    status: "OPEN",
    is_time_flexible: true,
    created_at: new Date().toISOString(),
  },
];

import { refreshCoordinator } from "@/services/refreshCoordinator";

describe("NearbyRequestsFeed Data State Rules & Non-Destructive Refresh", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    refreshCoordinator.clearAllInFlight();
  });

  it("1. displays skeletons while loading", () => {
    vi.spyOn(requestsService, "getNearbyRequests").mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve([]), 5000))
    );

    const { container } = render(
      <BrowserRouter>
        <NearbyRequestsFeed />
      </BrowserRouter>
    );

    // Skeleton elements are rendered
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("2. displays SUCCESS WITH ZERO RESULTS when API succeeds with 0 items (never shows error card)", async () => {
    vi.spyOn(requestsService, "getNearbyRequests").mockResolvedValue([]);

    render(
      <BrowserRouter>
        <NearbyRequestsFeed />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("No Open Requests in Your Area Right Now")).toBeInTheDocument();
    });

    // Must NOT display API Failure card
    expect(screen.queryByText("Couldn't Load Requests")).toBeNull();
  });

  it("3. displays SUCCESS WITH DATA when API succeeds with items", async () => {
    vi.spyOn(requestsService, "getNearbyRequests").mockResolvedValue(sampleNearbyRequests);

    render(
      <BrowserRouter>
        <NearbyRequestsFeed />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Rahul Sharma")).toBeInTheDocument();
      expect(screen.getByText(/Need PG in Koramangala/i)).toBeInTheDocument();
    });

    // Neither error nor empty state is rendered
    expect(screen.queryByText("No Open Requests in Your Area Right Now")).toBeNull();
    expect(screen.queryByText("Couldn't Load Requests")).toBeNull();
  });

  it("4. displays API FAILURE state with Retry button on error and does NOT show 'No Open Requests'", async () => {
    vi.spyOn(requestsService, "getNearbyRequests").mockRejectedValue(
      new Error("Gateway connection timeout")
    );

    render(
      <BrowserRouter>
        <NearbyRequestsFeed />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Couldn't Load Requests")).toBeInTheDocument();
    });

    expect(screen.getByText(/Gateway connection timeout/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Retry Loading Requests/i })).toBeInTheDocument();

    // CRITICAL: An API failure must NOT be interpreted as zero requests!
    expect(screen.queryByText("No Open Requests in Your Area Right Now")).toBeNull();
  });

  it("5. non-destructive refresh: preserves existing request cards when subsequent background refresh fails", async () => {
    let callCount = 0;
    vi.spyOn(requestsService, "getNearbyRequests").mockImplementation(() => {
      callCount++;
      if (callCount === 1) {
        return Promise.resolve(sampleNearbyRequests);
      }
      return Promise.reject(new Error("Subsequent refresh network glitch"));
    });

    render(
      <BrowserRouter>
        <NearbyRequestsFeed />
      </BrowserRouter>
    );

    // Initial successful load
    await waitFor(() => {
      expect(screen.getByText("Rahul Sharma")).toBeInTheDocument();
    });

    // Trigger manual or background refresh via Refresh button in header
    const refreshBtn = screen.getByRole("button", { name: /Refresh/i });
    fireEvent.click(refreshBtn);

    // After failure, the existing card MUST STILL BE VISIBLE (non-destructive)
    await waitFor(() => {
      expect(screen.getByText("Rahul Sharma")).toBeInTheDocument();
    });

    // Non-destructive error indicator appears in header
    expect(screen.getByText("Couldn't refresh")).toBeInTheDocument();

    // Neither the full error card nor the empty state replaced the existing data
    expect(screen.queryByText("No Open Requests in Your Area Right Now")).toBeNull();
    expect(screen.queryByText("Couldn't Load Requests")).toBeNull();
  });
});
