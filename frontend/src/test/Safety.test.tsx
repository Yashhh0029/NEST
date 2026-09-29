import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { BlockConfirmModal } from "@/components/safety/BlockConfirmModal";
import { ReportModal } from "@/components/safety/ReportModal";
import { HelperCard } from "@/components/match/HelperCard";
import { AdminReportsPage } from "@/pages/AdminReportsPage";
import * as safetyService from "@/services/safety";
import { useAuthStore } from "@/store/useAuthStore";
import type { HelperMatchItem } from "@/types/match";
import type { ReportItem, ModerationActionItem } from "@/types/safety";

vi.mock("@/services/safety");

describe("Phase 11: Real Safety, Trust, Blocking, Reporting & Moderation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: {
        id: "user-current",
        name: "Admin Alice",
        email: "alice@nest.local",
        is_verified: true,
        role: "admin",
        created_at: "2026-01-01T00:00:00Z",
      },
      isAuthenticated: true,
    });
  });

  describe("BlockConfirmModal", () => {
    it("renders modal with target name and warning message", () => {
      render(
        <BlockConfirmModal
          isOpen={true}
          targetUserId="target-user-123"
          targetName="Bad Actor"
          onClose={vi.fn()}
        />
      );

      expect(screen.getByText("Block Bad Actor?")).toBeInTheDocument();
      expect(
        screen.getByText(/They will no longer be able to message you/i)
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /block user/i })
      ).toBeInTheDocument();
    });

    it("calls blockUser and onSuccess on confirmation", async () => {
      const mockBlock = vi
        .spyOn(safetyService, "blockUser")
        .mockResolvedValueOnce({
          id: "block-1",
          blocker_id: "user-current",
          blocked_id: "target-user-123",
          created_at: "2026-03-30T00:00:00Z",
        });
      const onSuccess = vi.fn();
      const onClose = vi.fn();

      render(
        <BlockConfirmModal
          isOpen={true}
          targetUserId="target-user-123"
          targetName="Bad Actor"
          onClose={onClose}
          onSuccess={onSuccess}
        />
      );

      const confirmBtn = screen.getByRole("button", { name: /block user/i });
      fireEvent.click(confirmBtn);

      await waitFor(() => {
        expect(mockBlock).toHaveBeenCalledWith("target-user-123");
        expect(onSuccess).toHaveBeenCalled();
        expect(onClose).toHaveBeenCalled();
      });
    });
  });

  describe("ReportModal", () => {
    it("renders report reasons dropdown and details textarea", () => {
      render(
        <ReportModal
          isOpen={true}
          targetUserId="target-user-123"
          targetName="Spammer Bob"
          onClose={vi.fn()}
        />
      );

      expect(screen.getByText("Report Spammer Bob")).toBeInTheDocument();
      expect(screen.getByRole("combobox")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /submit report/i })).toBeInTheDocument();
    });

    it("submits report with selected reason and optional details", async () => {
      const mockReport = vi
        .spyOn(safetyService, "createReport")
        .mockResolvedValueOnce({
          id: "report-1",
          reporter_id: "user-current",
          reported_user_id: "target-user-123",
          reason: "SPAM",
          description: "Sending repeated commercial solicitations",
          status: "PENDING",
          created_at: "2026-03-30T00:00:00Z",
        });

      render(
        <ReportModal
          isOpen={true}
          targetUserId="target-user-123"
          targetName="Spammer Bob"
          onClose={vi.fn()}
        />
      );

      // Select Spam from combobox
      const select = screen.getByRole("combobox");
      fireEvent.change(select, { target: { value: "SPAM" } });

      // Enter details
      const textarea = screen.getByPlaceholderText(/Provide context, details/i);
      fireEvent.change(textarea, {
        target: { value: "Sending repeated commercial solicitations" },
      });

      const submitBtn = screen.getByRole("button", {
        name: /submit report/i,
      });
      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(mockReport).toHaveBeenCalledWith({
          reported_user_id: "target-user-123",
          connection_id: undefined,
          message_id: undefined,
          reason: "SPAM",
          description: "Sending repeated commercial solicitations",
        });
      });

      expect(
        screen.getByText("Report Submitted")
      ).toBeInTheDocument();
    });
  });

  describe("HelperCard Safety Integration", () => {
    const sampleHelper: HelperMatchItem = {
      user_id: "helper-456",
      name: "Ramesh Sharma",
      headline: "Local Plumber",
      bio: "Available to help with water problems",
      area: "Baner",
      city: "Pune",
      skills: ["Plumbing", "Carpentry"],
      is_available_for_help: true,
      scores: {
        skills_score: 0.9,
        location_score: 0.85,
        reputation_score: null,
        final_score: 0.88,
      },
      reasons: [],
    };

    it("renders Report and Block action buttons", () => {
      render(<HelperCard helper={sampleHelper} />);

      expect(screen.getByTitle("Report user")).toBeInTheDocument();
      expect(screen.getByTitle("Block user")).toBeInTheDocument();
    });

    it("opens block modal when block button is clicked", () => {
      render(<HelperCard helper={sampleHelper} />);

      fireEvent.click(screen.getByTitle("Block user"));
      expect(screen.getByText("Block Ramesh Sharma?")).toBeInTheDocument();
    });
  });

  describe("AdminReportsPage", () => {
    const mockReports: ReportItem[] = [
      {
        id: "rep-1",
        reporter_id: "user-1",
        reported_user_id: "target-bad",
        reason: "HARASSMENT",
        description: "Sent abusive messages in chat",
        status: "PENDING",
        created_at: "2026-03-30T10:00:00Z",
      },
    ];

    const mockLogs: ModerationActionItem[] = [
      {
        id: "log-1",
        admin_id: "user-current",
        target_user_id: "target-bad",
        action: "SUSPEND_USER",
        reason: "Policy violation: Harassment",
        created_at: "2026-03-30T10:30:00Z",
      },
    ];

    it("renders moderation dashboard, loads reports and displays status tabs", async () => {
      vi.spyOn(safetyService, "adminListReports").mockResolvedValueOnce({
        reports: mockReports,
        total: 1,
      });
      vi.spyOn(safetyService, "adminListAuditLogs").mockResolvedValueOnce({
        actions: mockLogs,
        total: 1,
      });

      render(
        <BrowserRouter>
          <AdminReportsPage />
        </BrowserRouter>
      );

      expect(screen.getByText("Safety & Moderation Dashboard")).toBeInTheDocument();

      await waitFor(() => {
        expect(screen.getByText(/Harassment/i)).toBeInTheDocument();
        expect(screen.getByText("Sent abusive messages in chat")).toBeInTheDocument();
      });
    });
  });
});
