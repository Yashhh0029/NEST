import { api } from "./api";
import type {
  AssistanceSession,
  SessionCreate,
  SessionReschedule,
  SessionCancel,
} from "@/types/session";

export interface SessionListParams {
  status?: string;
  role?: string;
  request_id?: string;
  connection_id?: string;
}

export interface SessionListResponse {
  total: number;
  sessions: AssistanceSession[];
}

export const sessionService = {
  /**
   * Propose a new assistance session between connected users.
   */
  async proposeSession(payload: SessionCreate): Promise<AssistanceSession> {
    const { data } = await api.post<AssistanceSession>("/api/sessions", payload);
    return data;
  },

  /**
   * List assistance sessions for current user with optional filters.
   */
  async listSessions(params?: SessionListParams): Promise<AssistanceSession[]> {
    const { data } = await api.get<SessionListResponse | AssistanceSession[]>("/api/sessions", { params });
    if (Array.isArray(data)) {
      return data;
    }
    return data?.sessions ?? [];
  },

  /**
   * Get single assistance session by ID.
   */
  async getSessionById(id: string): Promise<AssistanceSession> {
    const { data } = await api.get<AssistanceSession>(`/api/sessions/${id}`);
    return data;
  },

  /**
   * Accept a proposed or reschedule-proposed session (recipient only).
   */
  async acceptSession(id: string): Promise<AssistanceSession> {
    const { data } = await api.post<AssistanceSession>(`/api/sessions/${id}/accept`);
    return data;
  },

  /**
   * Decline a proposed or reschedule-proposed session (recipient only).
   */
  async declineSession(id: string): Promise<AssistanceSession> {
    const { data } = await api.post<AssistanceSession>(`/api/sessions/${id}/decline`);
    return data;
  },

  /**
   * Cancel an active assistance session with mandatory reason.
   */
  async cancelSession(id: string, payload: SessionCancel): Promise<AssistanceSession> {
    const { data } = await api.post<AssistanceSession>(`/api/sessions/${id}/cancel`, payload);
    return data;
  },

  /**
   * Propose new scheduled time for an assistance session.
   */
  async rescheduleSession(id: string, payload: SessionReschedule): Promise<AssistanceSession> {
    const { data } = await api.post<AssistanceSession>(`/api/sessions/${id}/reschedule`, payload);
    return data;
  },

  /**
   * Dual-confirmation: mark session complete. Completed once both parties confirm.
   */
  async completeSession(id: string): Promise<AssistanceSession> {
    const { data } = await api.post<AssistanceSession>(`/api/sessions/${id}/complete`);
    return data;
  },

  /**
   * Download RFC 5545 iCalendar (.ics) file for confirmed session.
   */
  async downloadCalendarIcs(id: string, title?: string): Promise<void> {
    const response = await api.get(`/api/sessions/${id}/calendar.ics`, {
      responseType: "blob",
    });
    const blob = new Blob([response.data], { type: "text/calendar;charset=utf-8" });
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = downloadUrl;
    link.setAttribute("download", `nest-session-${title ? title.toLowerCase().replace(/\s+/g, "-") : id}.ics`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(downloadUrl);
  },
};
