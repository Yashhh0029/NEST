import type { ConnectionRequestSummary, ConnectionUserSummary } from "./connection";

export interface MessageItem {
  id: string;
  conversation_id: string;
  sender_id: string;
  sender_name: string;
  content: string;
  is_read: boolean;
  is_mine?: boolean;
  created_at: string;
  updated_at: string;
  edited_at?: string | null;
  deleted_at?: string | null;
}

export interface ConversationItem {
  id: string;
  connection_id: string;
  partner: ConnectionUserSummary;
  request?: ConnectionRequestSummary | null;
  created_at: string;
  updated_at: string;
  last_message?: MessageItem | null;
  unread_count: number;
}

export interface MessageListResponse {
  total: number;
  has_more: boolean;
  messages: MessageItem[];
}

export interface ConversationListResponse {
  total: number;
  conversations: ConversationItem[];
}

export interface SendMessagePayload {
  content: string;
}

export interface EditMessagePayload {
  content: string;
}
