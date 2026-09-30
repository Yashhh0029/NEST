import type { HelperMatchItem } from "./match";
import type { ResourceItem } from "./resource";
import type { CommunitySearchItem } from "./community";

export type NeedStatus =
  | "UNRESOLVED"
  | "EXPLORING"
  | "CONNECTED"
  | "RESOLUTION_PENDING"
  | "RESOLVED";

export type ResolutionSource =
  | "connection"
  | "community_question"
  | "saved_resource"
  | "manual";

export interface NeedProgressItem {
  category: string;
  item: string;
  status: NeedStatus;
  resolved_via?: ResolutionSource | null;
  resolved_entity_id?: string | null;
  notes?: string | null;
  updated_at?: string | null;
}

export interface NeedProgressUpdate {
  category: string;
  status: NeedStatus;
  resolved_via?: ResolutionSource | null;
  resolved_entity_id?: string | null;
  notes?: string | null;
}

export interface SavedResourceCreate {
  place_id: string;
  name: string;
  category: string;
  formatted_address?: string | null;
  rating?: number | null;
  user_ratings_total?: number | null;
  latitude?: number | null;
  longitude?: number | null;
  notes?: string | null;
}

export interface SavedResource {
  id: string;
  request_id: string;
  user_id: string;
  place_id: string;
  name: string;
  category: string;
  formatted_address?: string | null;
  rating?: number | null;
  user_ratings_total?: number | null;
  latitude?: number | null;
  longitude?: number | null;
  notes?: string | null;
  created_at: string;
}

export interface ActiveConnectionSummary {
  id: string;
  helper_id: string;
  helper_name: string;
  status: string;
  created_at: string;
  completed_at?: string | null;
  has_review: boolean;
}

export interface NeedIntelligenceBundle {
  category: string;
  item: string;
  status: NeedStatus;
  resolved_via?: string | null;
  resolved_entity_id?: string | null;
  matched_helpers: HelperMatchItem[];
  community_questions: CommunitySearchItem[];
  local_resources: ResourceItem[];
}

export interface RequestIntelligenceResponse {
  request_id: string;
  raw_text: string;
  status: string;
  city?: string | null;
  area?: string | null;
  budget?: {
    amount?: number | null;
    currency?: string | null;
    period?: string | null;
    operator?: string | null;
  } | null;
  total_needs: number;
  resolved_needs: number;
  progress_percentage: number;
  action_plan: string[];
  needs: NeedIntelligenceBundle[];
  active_connections: ActiveConnectionSummary[];
  saved_resources: SavedResource[];
  resolution_summary?: string | null;
  resolved_at?: string | null;
}
