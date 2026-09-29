import { api } from "./api";
import type { ConnectionItem } from "../types/connection";
import type {
  ReputationSummary,
  ReviewCreatePayload,
  ReviewItem,
  ReviewListResponse,
} from "../types/review";

export async function completeConnection(connectionId: string): Promise<ConnectionItem> {
  const resp = await api.post<ConnectionItem>(`/api/connections/${connectionId}/complete`);
  return resp.data;
}

export async function createReview(
  connectionId: string,
  payload: ReviewCreatePayload
): Promise<ReviewItem> {
  const resp = await api.post<ReviewItem>(`/api/connections/${connectionId}/reviews`, payload);
  return resp.data;
}

export async function getConnectionReviews(connectionId: string): Promise<ReviewItem[]> {
  const resp = await api.get<ReviewItem[] | { reviews: ReviewItem[] }>(`/api/connections/${connectionId}/reviews`);
  if (Array.isArray(resp.data)) {
    return resp.data;
  }
  return (resp.data as { reviews: ReviewItem[] })?.reviews || [];
}

export async function getUserReputation(userId: string): Promise<ReputationSummary> {
  const resp = await api.get<ReputationSummary>(`/api/users/${userId}/reputation`);
  return resp.data;
}

export async function getUserReviews(userId: string): Promise<ReviewListResponse> {
  const resp = await api.get<ReviewListResponse>(`/api/users/${userId}/reviews`);
  return resp.data;
}
