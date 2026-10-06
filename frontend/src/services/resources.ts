import { api } from "./api";
import type {
  NearbyHelpersResponse,
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
  min_lat?: number;
  max_lat?: number;
  min_lon?: number;
  max_lon?: number;
  provider?: string;
  limit?: number;
  search_origin_type?: string;
}): Promise<ResourceSearchResponse> {
  const resp = await api.get<ResourceSearchResponse>("/api/resources/search", {
    params,
  });
  return resp.data;
}

export async function getNearbyHelpers(params: {
  latitude: number;
  longitude: number;
  radius_km?: number;
  request_id?: string;
}): Promise<NearbyHelpersResponse> {
  const resp = await api.get<NearbyHelpersResponse>("/api/resources/helpers", {
    params,
  });
  return resp.data;
}

