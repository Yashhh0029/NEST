import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { NeedProgressTracker } from "@/components/intelligence/NeedProgressTracker";
import { NeedIntelligenceCard } from "@/components/intelligence/NeedIntelligenceCard";
import { SavedResourcesList } from "@/components/intelligence/SavedResourcesList";
import { ResolveRequestModal } from "@/components/intelligence/ResolveRequestModal";
import type {
  NeedIntelligenceBundle,
  SavedResource,
  SavedResourceCreate,
} from "@/types/intelligence";

describe("Phase 13: Request Intelligence Hub Components", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockBundle: NeedIntelligenceBundle = {
    category: "accommodation",
    item: "PG under 10000",
    status: "EXPLORING",
    resolved_via: null,
    resolved_entity_id: null,
    matched_helpers: [
      {
        user_id: "user-helper-1",
        name: "Rahul Verma",
        headline: "Resident in Hinjewadi Phase 1",
        city: "Pune",
        area: "Hinjewadi",
        distance_km: 1.2,
        skills: ["housing", "local advice"],
        scores: {
          semantic_score: 0.9,
          location_score: 0.85,
          experience_score: 0.8,
          reputation_score: 4.8,
          availability_score: 1.0,
          final_score: 0.88,
        },
        dimension_statuses: {
          semantic: "ACTIVE",
          location: "ACTIVE",
          experience: "ACTIVE",
          reputation: "ACTIVE",
          availability: "ACTIVE",
        },
      },
    ],
    community_questions: [
      {
        question: {
          id: "q-1",
          author_id: "user-bob",
          author_name: "Bob Patil",
          title: "Best single occupancy PGs near Phase 1 circle?",
          body: "Looking for recommendations with food included.",
          category: "HOUSING",
          city: "Pune",
          area: "Hinjewadi",
          status: "OPEN",
          answer_count: 1,
          has_accepted_answer: true,
          created_at: "2026-09-30T00:00:00Z",
          updated_at: "2026-09-30T00:00:00Z",
          author_trust_signals: {
            author_id: "user-bob",
            author_name: "Bob Patil",
            reputation_status: "AVAILABLE",
            average_rating: 4.8,
            review_count: 5,
            completed_interactions_count: 6,
          },
        },
        similarity_score: 0.85,
        top_answer: {
          id: "ans-1",
          question_id: "q-1",
          author_id: "user-carol",
          author_name: "Carol Joshi",
          body: "Check Zolo Stays near Blue Ridge.",
          is_accepted: true,
          helpful_count: 4,
          not_helpful_count: 0,
          score: 4,
          created_at: "2026-09-30T00:00:00Z",
          updated_at: "2026-09-30T00:00:00Z",
          author_trust_signals: {
            author_id: "user-carol",
            author_name: "Carol Joshi",
            reputation_status: "AVAILABLE",
            average_rating: 4.9,
            review_count: 8,
            completed_interactions_count: 10,
          },
        },
      },
    ],
    local_resources: [
      {
        id: "res-1",
        google_place_id: "place-zolo-1",
        name: "Zolo Coliving Hinjewadi",
        category: "accommodation",
        category_display_name: "Accommodation & PG",
        formatted_address: "Phase 1, Hinjewadi, Pune",
        distance_km: 1.5,
        rating: 4.3,
        review_count: 120,
        ranking_score: 0.82,
        ranking_reasons: ["Verified accommodation", "Near Hinjewadi"],
      },
    ],
  };

  const mockSavedResource: SavedResource = {
    id: "saved-1",
    request_id: "req-1",
    user_id: "user-me",
    place_id: "place-zolo-1",
    name: "Zolo Coliving Hinjewadi",
    category: "accommodation",
    formatted_address: "Phase 1, Hinjewadi, Pune",
    rating: 4.3,
    user_ratings_total: 120,
    created_at: "2026-09-30T00:00:00Z",
  };

  /* ========================================================================= */
  /* NeedProgressTracker Tests                                                 */
  /* ========================================================================= */
  describe("NeedProgressTracker", () => {
    it("renders progress percentage and need chips correctly", () => {
      const handleUpdate = vi.fn().mockResolvedValue(undefined);
      const handleResolveOverall = vi.fn();

      render(
        <NeedProgressTracker
          bundles={[mockBundle]}
          progressPercentage={50}
          resolvedNeeds={1}
          totalNeeds={2}
          onUpdateStatus={handleUpdate}
          onMarkOverallResolved={handleResolveOverall}
          isOverallResolved={false}
        />
      );

      expect(screen.getByText("Need Resolution Progress")).toBeInTheDocument();
      expect(screen.getByText("1 of 2 Resolved (50%)")).toBeInTheDocument();
      expect(screen.getByText("PG under 10000")).toBeInTheDocument();
      expect(screen.getByText("EXPLORING")).toBeInTheDocument();
      expect(screen.getByText("Mark Request Resolved")).toBeInTheDocument();
    });

    it("opens status modal and submits updated status", async () => {
      const handleUpdate = vi.fn().mockResolvedValue(undefined);
      const handleResolveOverall = vi.fn();

      render(
        <NeedProgressTracker
          bundles={[mockBundle]}
          progressPercentage={0}
          resolvedNeeds={0}
          totalNeeds={1}
          onUpdateStatus={handleUpdate}
          onMarkOverallResolved={handleResolveOverall}
          isOverallResolved={false}
        />
      );

      // Click the need chip to open modal
      fireEvent.click(screen.getByText("PG under 10000"));

      expect(screen.getByText("Update Status: PG under 10000")).toBeInTheDocument();

      // Click "Save Progress"
      const saveBtn = screen.getByText("Save Progress");
      fireEvent.click(saveBtn);

      await waitFor(() => {
        expect(handleUpdate).toHaveBeenCalledWith("accommodation", "RESOLVED", undefined);
      });
    });
  });

  /* ========================================================================= */
  /* NeedIntelligenceCard Tests                                                */
  /* ========================================================================= */
  describe("NeedIntelligenceCard", () => {
    it("renders recommendation tabs and pillars", () => {
      const handleSave = vi.fn().mockResolvedValue(undefined);
      const handleConnect = vi.fn();

      render(
        <BrowserRouter>
          <NeedIntelligenceCard
            bundle={mockBundle}
            requestId="req-1"
            savedPlaceIds={new Set()}
            onSaveResource={handleSave}
            onConnectHelper={handleConnect}
          />
        </BrowserRouter>
      );

      // Header info
      expect(screen.getByText("Requirement Category: accommodation")).toBeInTheDocument();
      expect(screen.getByText("PG under 10000")).toBeInTheDocument();

      // People pillar
      expect(screen.getByText("Rahul Verma")).toBeInTheDocument();
      expect(screen.getByText("88% Match")).toBeInTheDocument();
      expect(screen.getByText("1.2 km away")).toBeInTheDocument();

      // Community pillar
      expect(screen.getByText("Best single occupancy PGs near Phase 1 circle?")).toBeInTheDocument();
      expect(screen.getByText(/Check Zolo Stays near Blue Ridge/)).toBeInTheDocument();

      // Resources pillar
      expect(screen.getByText("Zolo Coliving Hinjewadi")).toBeInTheDocument();
      expect(screen.getByText("Phase 1, Hinjewadi, Pune")).toBeInTheDocument();
    });

    it("triggers onConnectHelper when connect button is clicked", () => {
      const handleSave = vi.fn().mockResolvedValue(undefined);
      const handleConnect = vi.fn();

      render(
        <BrowserRouter>
          <NeedIntelligenceCard
            bundle={mockBundle}
            requestId="req-1"
            savedPlaceIds={new Set()}
            onSaveResource={handleSave}
            onConnectHelper={handleConnect}
          />
        </BrowserRouter>
      );

      fireEvent.click(screen.getByText("Connect with Rahul"));
      expect(handleConnect).toHaveBeenCalledWith("user-helper-1", "Rahul Verma");
    });

    it("triggers onSaveResource when bookmark icon is clicked", async () => {
      const handleSave = vi.fn().mockResolvedValue(undefined);
      const handleConnect = vi.fn();

      render(
        <BrowserRouter>
          <NeedIntelligenceCard
            bundle={mockBundle}
            requestId="req-1"
            savedPlaceIds={new Set()}
            onSaveResource={handleSave}
            onConnectHelper={handleConnect}
          />
        </BrowserRouter>
      );

      const bookmarkBtn = screen.getByTitle("Bookmark to Request");
      fireEvent.click(bookmarkBtn);

      await waitFor(() => {
        expect(handleSave).toHaveBeenCalledWith(
          expect.objectContaining({
            place_id: "place-zolo-1",
            name: "Zolo Coliving Hinjewadi",
            category: "accommodation",
          })
        );
      });
    });
  });

  /* ========================================================================= */
  /* SavedResourcesList Tests                                                  */
  /* ========================================================================= */
  describe("SavedResourcesList", () => {
    it("renders empty state when no resources are bookmarked", () => {
      const handleDelete = vi.fn().mockResolvedValue(undefined);

      render(
        <SavedResourcesList
          resources={[]}
          onDeleteResource={handleDelete}
        />
      );

      expect(screen.getByText("No Saved Places Yet")).toBeInTheDocument();
    });

    it("renders bookmarked places and handles removal", async () => {
      const handleDelete = vi.fn().mockResolvedValue(undefined);

      render(
        <SavedResourcesList
          resources={[mockSavedResource]}
          onDeleteResource={handleDelete}
        />
      );

      expect(screen.getByText("Bookmarked Places for this Request (1)")).toBeInTheDocument();
      expect(screen.getByText("Zolo Coliving Hinjewadi")).toBeInTheDocument();

      const deleteBtn = screen.getByTitle("Remove Bookmark");
      fireEvent.click(deleteBtn);

      await waitFor(() => {
        expect(handleDelete).toHaveBeenCalledWith("place-zolo-1");
      });
    });
  });

  /* ========================================================================= */
  /* ResolveRequestModal Tests                                                 */
  /* ========================================================================= */
  describe("ResolveRequestModal", () => {
    it("allows entering resolution summary and submitting", async () => {
      const handleConfirm = vi.fn().mockResolvedValue(undefined);
      const handleClose = vi.fn();

      render(
        <ResolveRequestModal
          isOpen={true}
          onClose={handleClose}
          onConfirm={handleConfirm}
        />
      );

      expect(screen.getByText("Mark Request as Resolved")).toBeInTheDocument();

      const textarea = screen.getByPlaceholderText(/Found a great PG/);
      fireEvent.change(textarea, { target: { value: "Found a great PG through NEST community!" } });

      const confirmBtn = screen.getByText("Confirm Resolution");
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(handleConfirm).toHaveBeenCalledWith("Found a great PG through NEST community!");
      });
    });
  });
});
