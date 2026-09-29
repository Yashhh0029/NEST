export interface ResourceCategory {
  id: string;
  display_name: string;
  icon: string;
  description: string;
  default_query_terms: string[];
}

export interface ResourceItem {
  id: string;
  name: string;
  category: string;
  category_display_name: string;
  formatted_address?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  distance_km?: number | null;
  rating?: number | null;
  review_count?: number | null;
  price_level?: string | null;
  is_open_now?: boolean | null;
  google_place_id: string;
  maps_url?: string | null;
  website_url?: string | null;
  phone_number?: string | null;
  primary_type?: string | null;
  ranking_score: number;
  ranking_reasons: string[];
}

export interface SearchCenter {
  latitude?: number | null;
  longitude?: number | null;
  label?: string | null;
}

export interface ResourceSearchResponse {
  status: "SUCCESS" | "NO_RESULTS" | "PROVIDER_UNAVAILABLE" | string;
  total: number;
  resources: ResourceItem[];
  search_center?: SearchCenter | null;
  category?: string | null;
  query: string;
  radius_meters: number;
}

export interface ResourceCategoriesResponse {
  total: number;
  categories: ResourceCategory[];
}
