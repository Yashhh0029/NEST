import { api } from "./api";
import type {
  ConversationItem,
  ConversationListResponse,
  ConversationPresenceResponse,
  MessageItem,
  MessageListResponse,
} from "../types/chat";

export async function createConversation(
  connection_id: string
): Promise<ConversationItem> {
  const resp = await api.post<ConversationItem>("/api/conversations", {
    connection_id,
  });
  return resp.data;
}

export async function getConversationByConnection(
  connection_id: string
): Promise<ConversationItem> {
  const resp = await api.get<ConversationItem>(
    `/api/conversations/by-connection/${connection_id}`
  );
  return resp.data;
}

export async function getConversation(
  conversation_id: string
): Promise<ConversationItem> {
  const resp = await api.get<ConversationItem>(
    `/api/conversations/${conversation_id}`
  );
  return resp.data;
}

export async function listConversations(): Promise<ConversationListResponse> {
  const resp = await api.get<ConversationListResponse>("/api/conversations");
  return resp.data;
}

export async function getMessages(
  conversation_id: string,
  params?: { limit?: number; before?: string }
): Promise<MessageListResponse> {
  const resp = await api.get<MessageListResponse>(
    `/api/conversations/${conversation_id}/messages`,
    { params }
  );
  return resp.data;
}

export async function sendMessage(
  conversation_id: string,
  content: string
): Promise<MessageItem> {
  const resp = await api.post<MessageItem>(
    `/api/conversations/${conversation_id}/messages`,
    { content }
  );
  return resp.data;
}

export async function editMessage(
  message_id: string,
  content: string
): Promise<MessageItem> {
  const resp = await api.patch<MessageItem>(`/api/messages/${message_id}`, {
    content,
  });
  return resp.data;
}

export async function deleteMessage(
  message_id: string
): Promise<MessageItem> {
  const resp = await api.delete<MessageItem>(`/api/messages/${message_id}`);
  return resp.data;
}

export interface TranslateChatResponse {
  original_text: string;
  translated_text: string;
  detected_source_language: string;
  target_language: string;
  message_id?: string;
  provider: string;
}

export async function translateChatMessage(
  text: string,
  target_language: string,
  source_language: string = "auto",
  message_id?: string
): Promise<TranslateChatResponse> {
  const resp = await api.post<TranslateChatResponse>("/api/chat/translate", {
    text,
    target_language,
    source_language,
    message_id,
  });
  return resp.data;
}

export async function getConversationPresence(
  conversation_id: string
): Promise<ConversationPresenceResponse> {
  const resp = await api.get<ConversationPresenceResponse>(
    `/api/conversations/${conversation_id}/presence`
  );
  return resp.data;
}
