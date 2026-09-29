import { api } from "./api";
import type {
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

  async getMyRequests(): Promise<NewcomerRequest[]> {
    const res = await api.get<NewcomerRequest[]>("/api/requests");
    return res.data;
  },

  async getRequestById(id: string): Promise<NewcomerRequest> {
    const res = await api.get<NewcomerRequest>(`/api/requests/${id}`);
    return res.data;
  },

  async updateRequest(id: string, payload: RequestUpdatePayload): Promise<NewcomerRequest> {
    const res = await api.patch<NewcomerRequest>(`/api/requests/${id}`, payload);
    return res.data;
  },

  async deleteRequest(id: string): Promise<void> {
    await api.delete(`/api/requests/${id}`);
  },
};
