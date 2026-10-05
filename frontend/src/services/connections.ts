import { api } from "./api";
import type {
  ConnectionCreatePayload,
  ConnectionItem,
  ConnectionListResponse,
} from "../types/connection";

export async function createConnection(
  payload: ConnectionCreatePayload
): Promise<ConnectionItem> {
  const resp = await api.post<ConnectionItem>("/api/connections", payload);
  return resp.data;
}

export async function listConnections(params?: {
  status?: string;
  role?: string;
}): Promise<ConnectionListResponse> {
  const resp = await api.get<ConnectionListResponse>("/api/connections", {
    params,
  });
  return resp.data;
}

export async function getConnectionById(id: string): Promise<ConnectionItem> {
  const resp = await api.get<ConnectionItem>(`/api/connections/${id}`);
  return resp.data;
}

export async function updateConnectionStatus(
  id: string,
  action: "accept" | "decline" | "cancel" | "complete" | "reactivate"
): Promise<ConnectionItem> {
  const resp = await api.patch<ConnectionItem>(`/api/connections/${id}`, {
    action,
  });
  return resp.data;
}

export async function completeConnection(id: string): Promise<ConnectionItem> {
  const resp = await api.post<ConnectionItem>(`/api/connections/${id}/complete`);
  return resp.data;
}

export async function reactivateConnection(id: string): Promise<ConnectionItem> {
  const resp = await api.post<ConnectionItem>(`/api/connections/${id}/reactivate`);
  return resp.data;
}
