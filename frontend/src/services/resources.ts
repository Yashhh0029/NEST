import { api } from "./api";
import type {
  ResourceCategoriesResponse,
  ResourceSearchResponse,
} from "../types/resource";

export async function getResourceCategories(): Promise<ResourceCategoriesResponse> {
  const resp = await api.get<ResourceCategoriesResponse>("/api/resources/categories");
  return resp.data;
}

export async function searchResources(params?: {
  request_id?: string;
  category?: string;
  query?: string;
  latitude?: number;
  longitude?: number;
  radius_meters?: number;
  limit?: number;
}): Promise<ResourceSearchResponse> {
  const resp = await api.get<ResourceSearchResponse>("/api/resources/search", {
    params,
  });
  return resp.data;
}
