import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { WeeklyScheduleEditor } from "@/components/availability/WeeklyScheduleEditor";
import { CapacityControls } from "@/components/availability/CapacityControls";
import { SessionCard } from "@/components/session/SessionCard";
import { ProposeSessionModal } from "@/components/session/ProposeSessionModal";
import { RescheduleModal } from "@/components/session/RescheduleModal";
import { SessionsPage } from "@/pages/SessionsPage";
import { sessionService } from "@/services/sessions";
import { availabilityService } from "@/services/availability";
import { useAuthStore } from "@/store/useAuthStore";
import type {
  HelperAvailabilitySlot,
  PublicAvailabilityProfile,
} from "@/types/availability";
import type { AssistanceSession } from "@/types/session";

vi.mock("@/services/sessions");
vi.mock("@/services/availability");

const sampleSlot: HelperAvailabilitySlot = {
  id: "slot-1",
  user_id: "user-helper",
  day_of_week: 0, // Monday
  start_time: "09:00:00",
  end_time: "17:00:00",
  is_recurring: true,
  effective_date: null,
  created_at: "2026-03-01T10:00:00Z",
};

const sampleCapacity: PublicAvailabilityProfile = {
  user_id: "user-helper",
  helper_timezone: "Asia/Kolkata",
  timezone: "Asia/Kolkata",
  max_weekly_sessions: 3,
  accepting_sessions: true,
  current_status: "AVAILABLE",
  availability_badge: "Available this week",
  available_days: [0, 2, 4],
  available_time_ranges: ["09:00 - 17:00"],
};

const sampleProposedSession: AssistanceSession = {
  id: "sess-1",
  request_id: "req-1",
  connection_id: "conn-1",
  proposer_id: "user-requester",
  recipient_id: "user-helper",
  title: "Flat Hunting Tour",
  modality: "IN_PERSON",
  meeting_place_id: "ChIJ_cafe_123",
  meeting_place_name: "Central Cafe",
  meeting_place_address: "100ft Rd, Indiranagar",
  meeting_url: null,
  scheduled_start: "2026-04-10T10:00:00Z",
  duration_minutes: 60,
  timezone: "Asia/Kolkata",
  status: "PROPOSED",
  requester_completed_at: null,
  helper_completed_at: null,
  reschedule_counter: 0,
  cancellation_reason: null,
  cancelled_by_id: null,
  created_at: "2026-03-01T10:00:00Z",
  updated_at: "2026-03-01T10:00:00Z",
};

const sampleConfirmedRemoteSession: AssistanceSession = {
  id: "sess-2",
  request_id: "req-1",
  connection_id: "conn-1",
  proposer_id: "user-requester",
  recipient_id: "user-helper",
  title: "Virtual Consultation",
  modality: "REMOTE",
  meeting_place_id: null,
  meeting_place_name: null,
  meeting_place_address: null,
  meeting_url: "https://meet.google.com/abc-def-ghi",
  scheduled_start: "2026-04-11T14:00:00Z",
  duration_minutes: 45,
  timezone: "Asia/Kolkata",
  status: "CONFIRMED",
  requester_completed_at: "2026-04-11T15:00:00Z",
  helper_completed_at: null,
  reschedule_counter: 0,
  cancellation_reason: null,
  cancelled_by_id: null,
  created_at: "2026-03-01T10:00:00Z",
  updated_at: "2026-03-01T10:00:00Z",
};

describe("Phase 14 — Sessions and Availability Frontend Components", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: {
        id: "user-helper",
        email: "helper@example.com",
        name: "Helper User",
        role: "helper",
      },
      isAuthenticated: true,
      loading: false,
    });
  });

  it("1. WeeklyScheduleEditor renders day tabs and initial time slots", () => {
    const handleSave = vi.fn().mockResolvedValue(undefined);
    render(
      <WeeklyScheduleEditor
        initialSlots={[sampleSlot]}
        onSave={handleSave}
      />
    );

    expect(screen.getByText("Weekly Availability Schedule")).toBeInTheDocument();
    expect(screen.getByText("Monday")).toBeInTheDocument();
    expect(screen.getByText("Tuesday")).toBeInTheDocument();
    expect(screen.getByDisplayValue("09:00")).toBeInTheDocument();
    expect(screen.getByDisplayValue("17:00")).toBeInTheDocument();
  });

  it("2. WeeklyScheduleEditor allows adding and removing a time slot", () => {
    const handleSave = vi.fn().mockResolvedValue(undefined);
    render(
      <WeeklyScheduleEditor
        initialSlots={[]}
        onSave={handleSave}
      />
    );

    expect(screen.getByText("No availability configured for Monday")).toBeInTheDocument();
    const addBtn = screen.getByText("Add Window");
    fireEvent.click(addBtn);

    expect(screen.getByDisplayValue("09:00")).toBeInTheDocument();
    expect(screen.getByDisplayValue("17:00")).toBeInTheDocument();
  });

  it("3. WeeklyScheduleEditor validates slot start_time before end_time before saving", async () => {
    const handleSave = vi.fn().mockResolvedValue(undefined);
    render(
      <WeeklyScheduleEditor
        initialSlots={[
          {
            ...sampleSlot,
            start_time: "18:00:00",
            end_time: "09:00:00",
          },
        ]}
        onSave={handleSave}
      />
    );

    const saveBtn = screen.getByText("Save Schedule");
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(screen.getByText(/start time must be before end time/i)).toBeInTheDocument();
    });
    expect(handleSave).not.toHaveBeenCalled();
  });

  it("4. CapacityControls renders capacity limits and badge", () => {
    const handleSave = vi.fn().mockResolvedValue(undefined);
    render(
      <CapacityControls
        initialCapacity={sampleCapacity}
        onSave={handleSave}
      />
    );

    expect(screen.getByText("Assistance Capacity & Timezone")).toBeInTheDocument();
    expect(screen.getByText("Available this week")).toBeInTheDocument();
    expect(screen.getByDisplayValue("3")).toBeInTheDocument(); // max weekly sessions
    expect(screen.getByText("Max Weekly Sessions")).toBeInTheDocument();
  });

  it("5. CapacityControls submits updated capacity configuration", async () => {
    const handleSave = vi.fn().mockResolvedValue(undefined);
    render(
      <CapacityControls
        initialCapacity={sampleCapacity}
        onSave={handleSave}
      />
    );

    const sessionsInput = screen.getByDisplayValue("3");
    fireEvent.change(sessionsInput, { target: { value: "5" } });

    const submitBtn = screen.getByText("Save Capacity Preferences");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(handleSave).toHaveBeenCalledWith({
        helper_timezone: "Asia/Kolkata",
        timezone: "Asia/Kolkata",
        max_weekly_sessions: 5,
        accepting_sessions: true,
      });
    });
  });

  it("6. SessionCard renders proposed in-person session with recipient action buttons", () => {
    const onAccept = vi.fn().mockResolvedValue(undefined);
    const onDecline = vi.fn().mockResolvedValue(undefined);

    render(
      <SessionCard
        session={sampleProposedSession}
        currentUserId="user-helper" // recipient
        onAccept={onAccept}
        onDecline={onDecline}
      />
    );

    expect(screen.getByText("Flat Hunting Tour")).toBeInTheDocument();
    expect(screen.getByText("Central Cafe")).toBeInTheDocument();
    expect(screen.getByText("100ft Rd, Indiranagar")).toBeInTheDocument();
    expect(screen.getByText("Proposal Pending")).toBeInTheDocument();

    const acceptBtn = screen.getByText("Accept");
    expect(acceptBtn).toBeInTheDocument();
    fireEvent.click(acceptBtn);
    expect(onAccept).toHaveBeenCalledWith("sess-1");
  });

  it("7. SessionCard hides accept/decline from proposer", () => {
    render(
      <SessionCard
        session={sampleProposedSession}
        currentUserId="user-requester" // proposer
      />
    );

    expect(screen.getByText("You proposed this session")).toBeInTheDocument();
    expect(screen.queryByText("Accept")).not.toBeInTheDocument();
    expect(screen.queryByText("Decline")).not.toBeInTheDocument();
  });

  it("8. SessionCard renders confirmed remote session with meeting link and calendar button", () => {
    const onComplete = vi.fn().mockResolvedValue(undefined);
    const onDownloadIcs = vi.fn().mockResolvedValue(undefined);

    render(
      <SessionCard
        session={sampleConfirmedRemoteSession}
        currentUserId="user-helper"
        onComplete={onComplete}
        onDownloadIcs={onDownloadIcs}
      />
    );

    expect(screen.getByText("Virtual Consultation")).toBeInTheDocument();
    expect(screen.getByText("Join Secure Meeting Room")).toBeInTheDocument();
    expect(screen.getByText("Confirmed")).toBeInTheDocument();
    expect(screen.getByText(/Requester: Marked Complete/i)).toBeInTheDocument();
    expect(screen.getByText(/Helper: Pending Confirmation/i)).toBeInTheDocument();

    const calBtn = screen.getByText("Add to Calendar");
    expect(calBtn).toBeInTheDocument();
    fireEvent.click(calBtn);
    expect(onDownloadIcs).toHaveBeenCalledWith("sess-2", "Virtual Consultation");
  });

  it("9. SessionCard enforces mandatory reason when cancelling", async () => {
    const onCancel = vi.fn().mockResolvedValue(undefined);

    render(
      <SessionCard
        session={sampleProposedSession}
        currentUserId="user-helper"
        onCancel={onCancel}
      />
    );

    const cancelBtn = screen.getByText("Cancel");
    fireEvent.click(cancelBtn);

    expect(screen.getByText(/Mandatory Cancellation Reason:/i)).toBeInTheDocument();
    const confirmBtn = screen.getByText("Confirm Cancellation");
    expect(confirmBtn).toBeDisabled();

    const input = screen.getByPlaceholderText(/Please specify why you are cancelling/i);
    fireEvent.change(input, { target: { value: "Sudden urgent conflict" } });

    expect(confirmBtn).not.toBeDisabled();
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(onCancel).toHaveBeenCalledWith("sess-1", "Sudden urgent conflict");
    });
  });

  it("10. ProposeSessionModal enforces Google Places ID for in-person modality", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    render(
      <ProposeSessionModal
        requestId="req-1"
        recipientId="user-helper"
        isOpen={true}
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />
    );

    expect(screen.getByText("Propose Assistance Session")).toBeInTheDocument();
    const dateInput = screen.getByLabelText("Date");
    fireEvent.change(dateInput, { target: { value: "2027-05-15" } });

    // Submit with empty meeting_place_id
    const submitBtn = screen.getByText("Send Proposal");
    fireEvent.submit(submitBtn.closest("form")!);

    await waitFor(() => {
      expect(screen.getByText(/Please enter a Google Places ID/i)).toBeInTheDocument();
    });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("11. ProposeSessionModal enforces HTTPS meeting URL for remote modality", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    render(
      <ProposeSessionModal
        requestId="req-1"
        recipientId="user-helper"
        isOpen={true}
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />
    );

    // Switch to Remote
    const remoteBtn = screen.getByText(/Remote Video/i);
    fireEvent.click(remoteBtn);

    const dateInput = screen.getByLabelText("Date");
    fireEvent.change(dateInput, { target: { value: "2027-05-15" } });

    // Provide insecure http url
    const urlInput = screen.getByPlaceholderText("https://meet.google.com/...");
    fireEvent.change(urlInput, { target: { value: "http://insecure.test/meet" } });

    const submitBtn = screen.getByText("Send Proposal");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Please provide a secure HTTPS meeting URL/i)).toBeInTheDocument();
    });
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("12. RescheduleModal validates future date and submits payload", async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);

    render(
      <RescheduleModal
        sessionId="sess-1"
        isOpen={true}
        onClose={vi.fn()}
        onSubmit={onSubmit}
      />
    );

    const dateInput = screen.getByLabelText("New Date");
    fireEvent.change(dateInput, { target: { value: "2027-06-20" } });

    const reasonInput = screen.getByPlaceholderText(/Flight was delayed/i);
    fireEvent.change(reasonInput, { target: { value: "Travel schedule updated" } });

    const submitBtn = screen.getByText("Propose New Time");
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(onSubmit).toHaveBeenCalledWith(
        "sess-1",
        expect.objectContaining({
          reason: "Travel schedule updated",
          new_duration_minutes: 60,
        })
      );
    });
  });

  it("13. SessionsPage lists sessions and switches filter tabs", async () => {
    vi.mocked(sessionService.listSessions).mockResolvedValue([sampleProposedSession]);

    render(
      <BrowserRouter>
        <SessionsPage />
      </BrowserRouter>
    );

    await waitFor(() => {
      expect(screen.getByText("Assistance Sessions")).toBeInTheDocument();
      expect(screen.getByText("Flat Hunting Tour")).toBeInTheDocument();
    });

    const confirmedTab = screen.getByText("Confirmed");
    fireEvent.click(confirmedTab);

    await waitFor(() => {
      expect(sessionService.listSessions).toHaveBeenCalledWith({ status: "CONFIRMED" });
    });
  });
});
