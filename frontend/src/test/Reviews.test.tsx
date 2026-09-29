import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { ReviewModal } from "@/components/review/ReviewModal";
import { HelperCard } from "@/components/match/HelperCard";
import { ConnectionsPage } from "@/pages/ConnectionsPage";
import * as reviewService from "@/services/reviews";
import * as connectionService from "@/services/connections";
import { useAuthStore } from "@/store/useAuthStore";
import type { ConnectionItem } from "@/types/connection";
import type { HelperMatchItem } from "@/types/match";

describe("Phase 9: Real Reputation, Completion & Reviews", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: {
        id: "user-me",
        name: "Test User",
        email: "test@example.com",
        is_verified: true,
        created_at: "2026-01-01T00:00:00Z",
      },
      isAuthenticated: true,
    });
  });

  describe("ReviewModal", () => {
    it("renders modal with partner name and star selector", () => {
      render(
        <ReviewModal
          isOpen={true}
          onClose={vi.fn()}
          connectionId="conn-100"
          partnerName="Dr. Priya Rao"
          onSuccess={vi.fn()}
        />
      );

      expect(screen.getByText("Review Dr. Priya Rao")).toBeInTheDocument();
      expect(
        screen.getByText(/How was your experience collaborating with/i)
      ).toBeInTheDocument();
      expect(screen.getByText("Select 1 to 5 stars")).toBeInTheDocument();
    });

    it("prevents submitting without selecting a rating", async () => {
      render(
        <ReviewModal
          isOpen={true}
          onClose={vi.fn()}
          connectionId="conn-100"
          partnerName="Dr. Priya Rao"
          onSuccess={vi.fn()}
        />
      );

      const submitBtn = screen.getByRole("button", { name: /submit review/i });
      expect(submitBtn).toBeDisabled();
    });

    it("submits review when rating and optional feedback are provided", async () => {
      const mockCreateReview = vi
        .spyOn(reviewService, "createReview")
        .mockResolvedValueOnce({
          id: "rev-1",
          connection_id: "conn-100",
          reviewer_id: "user-me",
          reviewee_id: "user-helper",
          rating: 5,
          comment: "Super helpful guidance on Pune localities!",
          created_at: "2026-03-30T10:00:00Z",
        });

      const handleSuccess = vi.fn();
      const handleClose = vi.fn();

      render(
        <ReviewModal
          isOpen={true}
          onClose={handleClose}
          connectionId="conn-100"
          partnerName="Dr. Priya Rao"
          onSuccess={handleSuccess}
        />
      );

      // Click 5 stars
      const star5 = screen.getByRole("button", { name: "5 stars" });
      fireEvent.click(star5);

      expect(screen.getByText("Exceptional Help")).toBeInTheDocument();

      // Enter comment
      const commentInput = screen.getByPlaceholderText(/share constructive feedback/i);
      fireEvent.change(commentInput, {
        target: { value: "Super helpful guidance on Pune localities!" },
      });

      const submitBtn = screen.getByRole("button", { name: /submit review/i });
      expect(submitBtn).not.toBeDisabled();
      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(mockCreateReview).toHaveBeenCalledWith("conn-100", {
          rating: 5,
          comment: "Super helpful guidance on Pune localities!",
        });
        expect(handleSuccess).toHaveBeenCalled();
        expect(handleClose).toHaveBeenCalled();
      });
    });
  });

  describe("HelperCard Reputation Display", () => {
    it("displays 'No reviews yet' when reputation is UNAVAILABLE", () => {
      const helperWithoutReviews: HelperMatchItem = {
        user_id: "user-helper-1",
        name: "Aarav Sharma",
        skills: ["Transit", "Budget"],
        scores: {
          semantic_score: 0.8,
          location_score: 0.9,
          experience_score: 0.7,
          reputation_score: null,
          availability_score: null,
          final_score: 0.82,
        },
        dimension_statuses: {
          semantic: "ACTIVE",
          location: "ACTIVE",
          experience: "ACTIVE",
          reputation: "UNAVAILABLE",
          availability: "UNAVAILABLE",
        },
      };

      render(<HelperCard helper={helperWithoutReviews} />);
      expect(screen.getByText("No reviews yet")).toBeInTheDocument();
    });

    it("displays real rating when reputation is ACTIVE with a score", () => {
      const helperWithReviews: HelperMatchItem = {
        user_id: "user-helper-2",
        name: "Sunita Patel",
        skills: ["Schools", "Groceries"],
        scores: {
          semantic_score: 0.85,
          location_score: 0.88,
          experience_score: 0.9,
          reputation_score: 1.0, // 5.0 stars normalized
          availability_score: null,
          final_score: 0.89,
        },
        dimension_statuses: {
          semantic: "ACTIVE",
          location: "ACTIVE",
          experience: "ACTIVE",
          reputation: "ACTIVE",
          availability: "UNAVAILABLE",
        },
      };

      render(<HelperCard helper={helperWithReviews} />);
      expect(screen.getByText("5.0")).toBeInTheDocument();
      expect(screen.getByText("rating")).toBeInTheDocument();
    });
  });

  describe("ConnectionsPage Completion & Review Flow", () => {
    const acceptedConn: ConnectionItem = {
      id: "conn-accepted",
      request_id: "req-1",
      requester_id: "user-me",
      helper_id: "user-helper",
      status: "ACCEPTED",
      created_at: "2026-03-01T10:00:00Z",
      updated_at: "2026-03-01T11:00:00Z",
      accepted_at: "2026-03-01T11:00:00Z",
      helper: {
        id: "user-helper",
        name: "Vikram Malhotra",
        headline: "Local Guide",
        city: "Bengaluru",
        area: "Indiranagar",
      },
    };

    it("allows completing an accepted connection", async () => {
      vi.spyOn(connectionService, "listConnections").mockResolvedValueOnce({
        total: 1,
        connections: [acceptedConn],
      });

      const completedConn: ConnectionItem = {
        ...acceptedConn,
        status: "COMPLETED",
        completed_at: "2026-03-02T10:00:00Z",
      };

      const completeSpy = vi
        .spyOn(reviewService, "completeConnection")
        .mockResolvedValueOnce(completedConn);

      vi.spyOn(reviewService, "getConnectionReviews").mockResolvedValue({
        total: 0,
        reviews: [],
      });

      render(
        <BrowserRouter>
          <ConnectionsPage />
        </BrowserRouter>
      );

      // Switch to Active tab
      await waitFor(() => {
        expect(screen.getByText("Active")).toBeInTheDocument();
      });
      fireEvent.click(screen.getByText("Active"));

      // Check Complete Interaction button exists
      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /complete interaction/i })
        ).toBeInTheDocument();
      });

      // Click Complete Interaction
      fireEvent.click(screen.getByRole("button", { name: /complete interaction/i }));

      await waitFor(() => {
        expect(completeSpy).toHaveBeenCalledWith("conn-accepted");
        // Check that review modal opened for the completed connection
        expect(screen.getByText("Review Vikram Malhotra")).toBeInTheDocument();
      });
    });

    it("displays Completed badge and allows leaving review when completed", async () => {
      const completedConn: ConnectionItem = {
        ...acceptedConn,
        status: "COMPLETED",
        completed_at: "2026-03-02T10:00:00Z",
      };

      vi.spyOn(connectionService, "listConnections").mockResolvedValueOnce({
        total: 1,
        connections: [completedConn],
      });

      vi.spyOn(reviewService, "getConnectionReviews").mockResolvedValue({
        total: 0,
        reviews: [],
      });

      render(
        <BrowserRouter>
          <ConnectionsPage />
        </BrowserRouter>
      );

      fireEvent.click(screen.getByText("Active"));

      await waitFor(() => {
        expect(screen.getByText("Completed")).toBeInTheDocument();
        expect(
          screen.getByRole("button", { name: /review helper/i })
        ).toBeInTheDocument();
      });
    });

    it("displays 'Review Submitted' when user has already reviewed the connection", async () => {
      const completedConn: ConnectionItem = {
        ...acceptedConn,
        status: "COMPLETED",
        completed_at: "2026-03-02T10:00:00Z",
      };

      vi.spyOn(connectionService, "listConnections").mockResolvedValueOnce({
        total: 1,
        connections: [completedConn],
      });

      vi.spyOn(reviewService, "getConnectionReviews").mockResolvedValue({
        total: 1,
        reviews: [
          {
            id: "rev-99",
            connection_id: completedConn.id,
            reviewer_id: "user-me",
            reviewee_id: "user-helper",
            rating: 5,
            comment: "Great experience!",
            created_at: "2026-03-02T12:00:00Z",
          },
        ],
      });

      render(
        <BrowserRouter>
          <ConnectionsPage />
        </BrowserRouter>
      );

      fireEvent.click(screen.getByText("Active"));

      await waitFor(() => {
        expect(screen.getByText("Review Submitted")).toBeInTheDocument();
      });
    });
  });
});
