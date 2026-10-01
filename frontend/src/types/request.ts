export interface ExtractedNeed {
  category: string;
  item: string;
  matched_text: string;
  source?: string;
}

export interface ExtractedLocation {
  city?: string | null;
  area?: string | null;
  state?: string | null;
  country?: string | null;
}

export interface BudgetInfo {
  amount?: number | null;
  currency?: string | null;
  operator?: string | null;
  period?: string | null;
  raw_text?: string | null;
}

export interface ExtractedRequest {
  raw_text: string;
  intent: string;
  location: ExtractedLocation;
  needs: ExtractedNeed[];
  budget?: BudgetInfo | null;
  preferences: string[];
  user_context: string[];
  extraction_method: string;
}

export interface RequestParseResponse {
  raw_text: string;
  extracted: ExtractedRequest;
}

export interface RequestCreatePayload {
  text: string;
  preferred_date?: string | null;
  preferred_start_time?: string | null;
  preferred_end_time?: string | null;
  requester_timezone?: string | null;
  is_time_flexible?: boolean | null;
  flexibility_window_days?: number | null;
  preferred_days_of_week?: number[] | null;
  target_city?: string | null;
  target_area?: string | null;
  target_google_place_id?: string | null;
  target_latitude?: number | null;
  target_longitude?: number | null;
  target_formatted_address?: string | null;
}

export interface RequestUpdatePayload {
  text?: string;
  status?: string;
  preferred_date?: string | null;
  preferred_start_time?: string | null;
  preferred_end_time?: string | null;
  requester_timezone?: string | null;
  is_time_flexible?: boolean | null;
  flexibility_window_days?: number | null;
  preferred_days_of_week?: number[] | null;
}

export interface NewcomerRequest {
  id: string;
  user_id: string;
  raw_text: string;
  intent?: string | null;
  status: "OPEN" | "MATCHED" | "CLOSED" | string;
  city?: string | null;
  area?: string | null;
  state?: string | null;
  country?: string | null;
  budget_amount?: number | null;
  budget_currency?: string | null;
  budget_period?: string | null;
  budget_operator?: string | null;
  extracted_requirements?: {
    intent?: string;
    location?: ExtractedLocation;
    needs?: ExtractedNeed[];
    budget?: BudgetInfo;
    preferences?: string[];
    user_context?: string[];
  } | null;
  preferences?: string[] | null;
  user_context?: string[] | null;
  extraction_method: string;
  preferred_date?: string | null;
  preferred_start_time?: string | null;
  preferred_end_time?: string | null;
  requester_timezone?: string | null;
  is_time_flexible?: boolean | null;
  flexibility_window_days?: number | null;
  preferred_days_of_week?: number[] | null;
  target_location?: {
    id?: string;
    request_id?: string;
    city?: string | null;
    area?: string | null;
    state?: string | null;
    country?: string;
    latitude?: number | null;
    longitude?: number | null;
    formatted_address?: string | null;
    google_place_id?: string | null;
    location_precision?: string;
    location_source?: string;
  } | null;
  created_at: string;
  updated_at: string;
}

export interface NearbyRequestItem {
  id: string;
  user_id: string;
  requester_name: string;
  raw_text: string;
  intent?: string | null;
  status: string;
  city?: string | null;
  area?: string | null;
  state?: string | null;
  country?: string | null;
  budget_amount?: number | null;
  budget_currency?: string | null;
  budget_period?: string | null;
  preferred_date?: string | null;
  preferred_start_time?: string | null;
  preferred_end_time?: string | null;
  requester_timezone?: string | null;
  is_time_flexible: boolean;
  needs: string[];
  distance_km?: number | null;
  match_reasons: string[];
  created_at: string;
}

