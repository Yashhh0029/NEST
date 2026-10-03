export type DimensionStatus = "ACTIVE" | "UNAVAILABLE";

export interface MatchScores {
  semantic_score: number;
  location_score: number;
  experience_score: number;
  reputation_score: number | null;
  availability_score: number | null;
  final_score: number;
}

export interface DimensionStatuses {
  semantic: DimensionStatus;
  location: DimensionStatus;
  experience: DimensionStatus;
  reputation: DimensionStatus;
  availability: DimensionStatus;
}

export interface MatchScoreWeights {
  semantic: number;
  location: number;
  experience: number;
  reputation: number;
  availability: number;
}

export interface WeightsSummary {
  raw: Record<string, number>;
  effective: Record<string, number>;
}

export interface MatchReason {
  category: "semantic" | "location" | "experience" | "skills" | "availability" | string;
  title: string;
  explanation: string;
}

export interface TravelRouteInfo {
  straight_line_distance_km: number;
  route_distance_km?: number | null;
  estimated_travel_time_minutes?: number | null;
  travel_mode?: string | null;
}

export interface HelperMatchItem {
  user_id: string;
  name: string;
  role?: string;
  headline?: string | null;
  bio?: string | null;
  city?: string | null;
  area?: string | null;
  distance_km?: number | null;
  approximate_latitude?: number | null;
  approximate_longitude?: number | null;
  route_info?: TravelRouteInfo | null;
  skills: string[];
  scores: MatchScores;
  dimension_statuses: DimensionStatuses;
  reasons: MatchReason[];
  is_available_for_help?: boolean | null;
}

export interface FindMatchesPayload {
  request_id: string;
  limit?: number;
  weights?: MatchScoreWeights;
  min_score?: number;
  max_distance_km?: number;
}

export interface TargetLocationSummary {
  city?: string | null;
  area?: string | null;
  formatted_address?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  location_source?: string | null;
}

export interface MatchingResultResponse {
  request_id: string;
  target_location?: TargetLocationSummary | null;
  total_candidates_evaluated: number;
  matches: HelperMatchItem[];
  weights_used: WeightsSummary;
  generated_at: string;
}
