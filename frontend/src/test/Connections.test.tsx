import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { HelperCard } from "@/components/match/HelperCard";
import { ConnectionsPage } from "@/pages/ConnectionsPage";
import * as connectionsService from "@/services/connections";
import * as reviewService from "@/services/reviews";
import { useAuthStore } from "@/store/useAuthStore";
import type { HelperMatchItem } from "@/types/match";
import type { ConnectionItem } from "@/types/connection";

const sampleHelper: HelperMatchItem = {
  user_id: "helper-123",
  name: "Pooja Hegde",
  headline: "Whitefield Resident & Mentor",
  bio: "Happy to guide newcomers settling in Bangalore.",
  city: "Bengaluru",
  area: "Whitefield",
  distance_km: 2.1,
  skills: ["Accommodation", "Transport"],
  scores: {
    semantic_score: 0.85,
    location_score: 0.9,
    experience_score: 0.75,
    reputation_score: null,
    availability_score: null,
    final_score: 0.84,
  },
  dimension_statuses: {
    semantic: "ACTIVE",
    location: "ACTIVE",
    experience: "ACTIVE",
    reputation: "UNAVAILABLE",
    availability: "UNAVAILABLE",
  },
  reasons: [],
  is_available_for_help: true,
};

const sampleConnections: ConnectionItem[] = [
  {
    id: "conn-1",
    request_id: "req-1",
    requester_id: "user-current",
    helper_id: "helper-123",
    status: "PENDING",
    initial_message: "Hi, need help with PG hunt!",
    created_at: "2026-03-01T10:00:00Z",
    updated_at: "2026-03-01T10:00:00Z",
    helper: {
      id: "helper-123",
      name: "Pooja Hegde",
      headline: "Whitefield Mentor",
      city: "Bengaluru",
      area: "Whitefield",
    },
    request: {
      id: "req-1",
      raw_text: "Looking for 1BHK in Whitefield",
      city: "Bengaluru",
      area: "Whitefield",
    },
  },
  {
    id: "conn-2",
    request_id: "req-2",
    requester_id: "user-other",
    helper_id: "user-current",
    status: "PENDING",
    initial_message: "Can you help me with local food options?",
    created_at: "2026-03-02T11:00:00Z",
    updated_at: "2026-03-02T11:00:00Z",
    requester: {
      id: "user-other",
      name: "Rohan Verma",
      headline: "Newcomer Engineer",
      city: "Bengaluru",
      area: "Whitefield",
    },
    request: {
      id: "req-2",
      raw_text: "Best veg tiffin services nearby",
      city: "Bengaluru",
      area: "Whitefield",
    },
  },
  {
    id: "conn-3",
    request_id: "req-3",
    requester_id: "user-current",
    helper_id: "helper-456",
    status: "ACCEPTED",
    created_at: "2026-02-28T09:00:00Z",
    updated_at: "2026-02-28T12:00:00Z",
    accepted_at: "2026-02-28T12:00:00Z",
    helper: {
      id: "helper-456",
      name: "Vikram Sen",
      headline: "Community Guide",
      city: "Bengaluru",
      area: "Whitefield",
    },
    request: {
      id: "req-3",
      raw_text: "Need metro route advice",
      city: "Bengaluru",
      area: "Whitefield",
    },
  },
];

const sampleCompletedConnection: ConnectionItem = {
  id: "conn-4",
  request_id: "req-4",
  requester_id: "user-current",
  helper_id: "helper-789",
  status: "COMPLETED",
  created_at: "2026-02-25T09:00:00Z",
  updated_at: "2026-02-26T12:00:00Z",
  completed_at: "2026-02-26T12:00:00Z",
  helper: {
    id: "helper-789",
    name: "Ananya Roy",
    headline: "Local Guide",
    city: "Bengaluru",
    area: "Whitefield",
  },
  request: {
    id: "req-4",
    raw_text: "Need local recommendations",
    city: "Bengaluru",
    area: "Whitefield",
  },
};

describe("Phase 7 Connection System UI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: {
        id: "user-current",
        email: "test@example.com",
        name: "Test Current User",
        created_at: "2026-01-01T00:00:00Z",
      },
      isAuthenticated: true,
      loading: false,
    });
    vi.spyOn(reviewService, "getConnectionReviews").mockResolvedValue({ reviews: [] } as any);
  });

  describe("HelperCard Connection States", () => {
    it("renders Connect button when IDLE and handles click", async () => {
      const onConnectMock = vi.fn().mockResolvedValue(undefined);
      render(
        <HelperCard
          helper={sampleHelper}
          connectionStatus="IDLE"
          onConnect={onConnectMock}
        />
      );

      const connectBtn = screen.getByRole("button", { name: /Connect/i });
      expect(connectBtn).toBeInTheDocument();
      fireEvent.click(connectBtn);
      expect(onConnectMock).toHaveBeenCalledWith("helper-123");
    });

    it("renders Requested badge when status is PENDING", () => {
      render(
        <HelperCard helper={sampleHelper} connectionStatus="PENDING" />
      );

      expect(screen.getByText("Requested")).toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /Connect/i })).not.toBeInTheDocument();
    });

    it("renders Connected badge when status is ACCEPTED", () => {
      render(
        <HelperCard helper={sampleHelper} connectionStatus="ACCEPTED" />
      );

      expect(screen.getByText("Connected")).toBeInTheDocument();
    });

    it("renders Declined badge when status is DECLINED", () => {
      render(
        <HelperCard helper={sampleHelper} connectionStatus="DECLINED" />
      );

      expect(screen.getByText("Declined")).toBeInTheDocument();
    });
  });

  describe("ConnectionsPage Component", () => {
    it("renders incoming pending requests and handles accept action", async () => {
      vi.spyOn(connectionsService, "listConnections").mockResolvedValue({
        total: sampleConnections.length,
        connections: sampleConnections,
      });

      const updateSpy = vi.spyOn(connectionsService, "updateConnectionStatus").mockResolvedValue({
        ...sampleConnections[1],
        status: "ACCEPTED",
        accepted_at: "2026-03-02T12:00:00Z",
      });

      render(
        <BrowserRouter>
          <ConnectionsPage />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Rohan Verma")).toBeInTheDocument();
      });

      expect(screen.getByText(/Best veg tiffin services nearby/i)).toBeInTheDocument();
      expect(screen.getByText("Can you help me with local food options?")).toBeInTheDocument();

      const acceptBtn = screen.getByRole("button", { name: /Accept Connection/i });
      fireEvent.click(acceptBtn);

      await waitFor(() => {
        expect(updateSpy).toHaveBeenCalledWith("conn-2", "accept");
      });
    });

    it("switches to Sent tab and displays outgoing pending request with Cancel button", async () => {
      vi.spyOn(connectionsService, "listConnections").mockResolvedValue({
        total: sampleConnections.length,
        connections: sampleConnections,
      });

      const updateSpy = vi.spyOn(connectionsService, "updateConnectionStatus").mockResolvedValue({
        ...sampleConnections[0],
        status: "CANCELLED",
      });

      render(
        <BrowserRouter>
          <ConnectionsPage />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Connections")).toBeInTheDocument();
      });

      const sentTab = screen.getByRole("button", { name: /Sent/i });
      fireEvent.click(sentTab);

      await waitFor(() => {
        expect(screen.getByText("Pooja Hegde")).toBeInTheDocument();
      });

      expect(screen.getByText(/Looking for 1BHK in Whitefield/i)).toBeInTheDocument();

      const cancelBtn = screen.getByRole("button", { name: /Cancel Request/i });
      fireEvent.click(cancelBtn);

      await waitFor(() => {
        expect(updateSpy).toHaveBeenCalledWith("conn-1", "cancel");
      });
    });

    it("switches to Active tab and shows connected partner", async () => {
      vi.spyOn(connectionsService, "listConnections").mockResolvedValue({
        total: sampleConnections.length,
        connections: sampleConnections,
      });

      render(
        <BrowserRouter>
          <ConnectionsPage />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Connections")).toBeInTheDocument();
      });

      const activeTab = screen.getByRole("button", { name: /Active/i });
      fireEvent.click(activeTab);

      await waitFor(() => {
        expect(screen.getByText("Vikram Sen")).toBeInTheDocument();
        expect(screen.getByText("Helper")).toBeInTheDocument();
      });
    });

    it("displays Reactivate conversation button for completed connections and handles confirmation modal", async () => {
      const connsWithCompleted = [...sampleConnections, sampleCompletedConnection];
      vi.spyOn(connectionsService, "listConnections").mockResolvedValue({
        total: connsWithCompleted.length,
        connections: connsWithCompleted,
      });

      const reactivateSpy = vi.spyOn(connectionsService, "reactivateConnection").mockResolvedValue({
        ...sampleCompletedConnection,
        status: "ACCEPTED",
      });

      render(
        <BrowserRouter>
          <ConnectionsPage />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Connections")).toBeInTheDocument();
      });

      const activeTab = screen.getByRole("button", { name: /Active/i });
      fireEvent.click(activeTab);

      await waitFor(() => {
        expect(screen.getByText("Ananya Roy")).toBeInTheDocument();
      });

      const reactivateBtn = screen.getByRole("button", { name: /Reactivate conversation/i });
      expect(reactivateBtn).toBeInTheDocument();

      // Click to open confirmation modal
      fireEvent.click(reactivateBtn);

      expect(screen.getByRole("heading", { name: /Reactivate conversation\?/i })).toBeInTheDocument();
      expect(
        screen.getByText(/You and the other person will be able to message each other again\. Previous messages will remain available\./i)
      ).toBeInTheDocument();

      // Click Cancel - modal closes
      const cancelBtn = screen.getByRole("button", { name: "Cancel" });
      fireEvent.click(cancelBtn);
      expect(screen.queryByRole("heading", { name: /Reactivate conversation\?/i })).not.toBeInTheDocument();
      expect(reactivateSpy).not.toHaveBeenCalled();

      // Open again and confirm
      fireEvent.click(reactivateBtn);
      const confirmBtn = screen.getByRole("button", { name: "Reactivate" });
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(reactivateSpy).toHaveBeenCalledWith("conn-4");
      });
    });
  });
});
