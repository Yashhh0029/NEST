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
  provider?: string;
}

export interface ResourceCategoriesResponse {
  total: number;
  categories: ResourceCategory[];
}

export interface NearbyHelperItem {
  user_id: string;
  name: string;
  headline?: string | null;
  bio?: string | null;
  city?: string | null;
  area?: string | null;
  approximate_latitude?: number | null;
  approximate_longitude?: number | null;
  distance_km?: number | null;
  skills: string[];
  reputation_rating?: number | null;
  reputation_reviews: number;
  is_available_for_help: boolean;
}

export interface NearbyHelpersResponse {
  total: number;
  helpers: NearbyHelperItem[];
  center_latitude: number;
  center_longitude: number;
  radius_km: number;
}

