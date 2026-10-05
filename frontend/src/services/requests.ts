import { api } from "./api";
import type {
  NearbyRequestItem,
  NewcomerRequest,
  RequestCreatePayload,
  RequestParseResponse,
  RequestUpdatePayload,
} from "@/types/request";

export const requestsService = {
  async parseRequestText(text: string): Promise<RequestParseResponse> {
    const res = await api.post<RequestParseResponse>("/api/requests/parse", { text });
    return res.data;
  },

  async createRequest(payload: RequestCreatePayload): Promise<NewcomerRequest> {
    const res = await api.post<NewcomerRequest>("/api/requests", payload);
    return res.data;
  },

  async getMyRequests(signal?: AbortSignal): Promise<NewcomerRequest[]> {
    const res = await api.get<NewcomerRequest[]>("/api/requests", { signal });
    return res.data;
  },

  async getRequestById(id: string, signal?: AbortSignal): Promise<NewcomerRequest> {
    const res = await api.get<NewcomerRequest>(`/api/requests/${id}`, { signal });
    return res.data;
  },

  async updateRequest(id: string, payload: RequestUpdatePayload): Promise<NewcomerRequest> {
    const res = await api.patch<NewcomerRequest>(`/api/requests/${id}`, payload);
    return res.data;
  },

  async deleteRequest(id: string): Promise<void> {
    await api.delete(`/api/requests/${id}`);
  },

  async getNearbyRequests(
    params?: { radius_km?: number; limit?: number },
    signal?: AbortSignal
  ): Promise<NearbyRequestItem[]> {
    const res = await api.get<NearbyRequestItem[]>("/api/requests/nearby", { params, signal });
    return res.data;
  },
};
