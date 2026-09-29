export type ConnectionStatus = "PENDING" | "ACCEPTED" | "DECLINED" | "CANCELLED" | "COMPLETED";

export interface ConnectionUserSummary {
  id: string;
  name: string;
  headline?: string | null;
  city?: string | null;
  area?: string | null;
}

export interface ConnectionRequestSummary {
  id: string;
  raw_text: string;
  city?: string | null;
  area?: string | null;
  intent?: string | null;
}

export interface ConnectionItem {
  id: string;
  request_id: string;
  requester_id: string;
  helper_id: string;
  status: ConnectionStatus;
  initial_message?: string | null;
  created_at: string;
  updated_at: string;
  accepted_at?: string | null;
  declined_at?: string | null;
  completed_at?: string | null;
  requester?: ConnectionUserSummary | null;
  helper?: ConnectionUserSummary | null;
  request?: ConnectionRequestSummary | null;
}

export interface ConnectionCreatePayload {
  request_id: string;
  helper_id: string;
  initial_message?: string;
}

export interface ConnectionListResponse {
  total: number;
  connections: ConnectionItem[];
}
