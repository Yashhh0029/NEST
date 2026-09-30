export type SessionModality = 'IN_PERSON' | 'REMOTE';

export type SessionStatus =
  | 'PROPOSED'
  | 'CONFIRMED'
  | 'RESCHEDULE_PROPOSED'
  | 'COMPLETED'
  | 'CANCELLED'
  | 'DECLINED';

export interface AssistanceSession {
  id: string;
  request_id: string;
  connection_id: string;
  proposer_id: string;
  recipient_id: string;
  title: string;
  modality: SessionModality;
  meeting_place_id?: string | null;
  meeting_place_name?: string | null;
  meeting_place_address?: string | null;
  meeting_url?: string | null;
  scheduled_start: string; // ISO 8601
  duration_minutes: number;
  timezone: string;
  status: SessionStatus;
  requester_completed_at?: string | null;
  helper_completed_at?: string | null;
  reschedule_counter: number;
  cancellation_reason?: string | null;
  cancelled_by_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface SessionCreate {
  request_id: string;
  recipient_id: string;
  title: string;
  modality: SessionModality;
  meeting_place_id?: string | null;
  meeting_url?: string | null;
  scheduled_start: string;
  duration_minutes: number;
  timezone?: string;
}

export interface SessionReschedule {
  new_scheduled_start: string;
  new_duration_minutes?: number | null;
  reason?: string | null;
}

export interface SessionCancel {
  reason: string;
}
