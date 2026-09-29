export type ReportReason =
  | "HARASSMENT"
  | "SPAM"
  | "SCAM"
  | "THREAT"
  | "INAPPROPRIATE_CONTENT"
  | "FAKE_PROFILE"
  | "SAFETY_CONCERN"
  | "OTHER";

export type ReportStatus = "OPEN" | "UNDER_REVIEW" | "RESOLVED" | "DISMISSED";

export type ModerationActionType =
  | "REPORT_REVIEWED"
  | "REPORT_RESOLVED"
  | "REPORT_DISMISSED"
  | "USER_SUSPENDED"
  | "USER_REACTIVATED";

export interface BlockUserSummary {
  id: string;
  name: string;
  email: string;
}

export interface BlockItem {
  id: string;
  blocker_id: string;
  blocked_id: string;
  created_at: string;
  blocked_user?: BlockUserSummary | null;
}

export interface BlockListResponse {
  total: number;
  blocks: BlockItem[];
}

export interface ReportUserSummary {
  id: string;
  name: string;
  email: string;
}

export interface ReportCreatePayload {
  reported_user_id: string;
  connection_id?: string;
  message_id?: string;
  question_id?: string;
  answer_id?: string;
  reason: ReportReason;
  description?: string;
}

export interface ReportItem {
  id: string;
  reporter_id: string;
  reported_user_id: string;
  connection_id?: string | null;
  message_id?: string | null;
  question_id?: string | null;
  answer_id?: string | null;
  reason: ReportReason;
  description?: string | null;
  status: ReportStatus;
  created_at: string;
  resolved_at?: string | null;
  resolution_note?: string | null;
  reporter?: ReportUserSummary | null;
  reported_user?: ReportUserSummary | null;
  resolved_by_user?: ReportUserSummary | null;
  message_snippet?: string | null;
  connection_summary?: string | null;
  question_title?: string | null;
  answer_snippet?: string | null;
}

export interface ReportListResponse {
  total: number;
  reports: ReportItem[];
}

export interface ReportUpdatePayload {
  status: ReportStatus;
  resolution_note?: string;
}

export interface ModerationActionItem {
  id: string;
  admin_id: string;
  target_user_id?: string | null;
  report_id?: string | null;
  action: ModerationActionType;
  reason: string;
  metadata_json?: Record<string, any> | null;
  created_at: string;
  admin_name?: string | null;
  target_user_name?: string | null;
}

export interface ModerationActionListResponse {
  total: number;
  actions: ModerationActionItem[];
}
