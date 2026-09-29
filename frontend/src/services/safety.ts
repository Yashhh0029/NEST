import { api } from "./api";
import type {
  BlockItem,
  BlockListResponse,
  ModerationActionListResponse,
  ReportCreatePayload,
  ReportItem,
  ReportListResponse,
  ReportStatus,
  ReportUpdatePayload,
} from "../types/safety";

// 1. Blocking API
export async function blockUser(userId: string): Promise<BlockItem> {
  const resp = await api.post<BlockItem>(`/api/blocks/${userId}`);
  return resp.data;
}

export async function unblockUser(userId: string): Promise<void> {
  await api.delete(`/api/blocks/${userId}`);
}

export async function listBlockedUsers(): Promise<BlockListResponse> {
  const resp = await api.get<BlockListResponse>("/api/blocks");
  return resp.data;
}

// 2. Reporting API
export async function createReport(payload: ReportCreatePayload): Promise<ReportItem> {
  const resp = await api.post<ReportItem>("/api/reports", payload);
  return resp.data;
}

export async function getMyReports(): Promise<ReportListResponse> {
  const resp = await api.get<ReportListResponse>("/api/reports/mine");
  return resp.data;
}

export async function getReportDetail(reportId: string): Promise<ReportItem> {
  const resp = await api.get<ReportItem>(`/api/reports/${reportId}`);
  return resp.data;
}

// 3. Admin Moderation API
export async function adminListReports(
  status?: ReportStatus,
  page: number = 1,
  limit: number = 50
): Promise<ReportListResponse> {
  const params: Record<string, any> = { page, limit };
  if (status) {
    params.status = status;
  }
  const resp = await api.get<ReportListResponse>("/api/admin/reports", { params });
  return resp.data;
}

export async function adminGetReport(reportId: string): Promise<ReportItem> {
  const resp = await api.get<ReportItem>(`/api/admin/reports/${reportId}`);
  return resp.data;
}

export async function adminUpdateReport(
  reportId: string,
  payload: ReportUpdatePayload
): Promise<ReportItem> {
  const resp = await api.patch<ReportItem>(`/api/admin/reports/${reportId}`, payload);
  return resp.data;
}

export async function adminSuspendUser(userId: string, reason: string): Promise<void> {
  await api.post(`/api/admin/users/${userId}/suspend`, { reason });
}

export async function adminReactivateUser(userId: string, reason: string): Promise<void> {
  await api.post(`/api/admin/users/${userId}/reactivate`, { reason });
}

export async function adminListAuditLogs(
  page: number = 1,
  limit: number = 50
): Promise<ModerationActionListResponse> {
  const resp = await api.get<ModerationActionListResponse>("/api/admin/audit-logs", {
    params: { page, limit },
  });
  return resp.data;
}
