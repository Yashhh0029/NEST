import type { User } from "./auth";

export interface Profile {
  id: string;
  user_id: string;
  headline?: string | null;
  bio?: string | null;
  occupation?: string | null;
  organization?: string | null;
  years_experience?: number | null;
  languages?: string[] | null;
  help_description?: string | null;
  needs_description?: string | null;
  availability: boolean;
  created_at: string;
  updated_at: string;
}

export interface ProfileUpdatePayload {
  role?: "newcomer" | "helper" | "both";
  headline?: string;
  bio?: string;
  occupation?: string;
  organization?: string;
  years_experience?: number;
  languages?: string[];
  help_description?: string;
  needs_description?: string;
  availability?: boolean;
}

export interface Location {
  id: string;
  city: string;
  area?: string | null;
  state?: string | null;
  country: string;
  latitude?: number | null;
  longitude?: number | null;
  location_label: string;
  display_name?: string | null;
  place_types?: string | null;
  google_place_id?: string | null;
  formatted_address?: string | null;
  postal_code?: string | null;
  private_unit?: string | null;
  location_source?: string;
  location_precision?: string;
  created_at: string;
  updated_at: string;
}

export interface LocationCreateOrUpdatePayload {
  city: string;
  area?: string;
  state?: string;
  country?: string;
  latitude?: number;
  longitude?: number;
  location_label?: string;
  display_name?: string;
  place_types?: string;
  google_place_id?: string;
  formatted_address?: string;
  postal_code?: string;
  private_unit?: string;
  location_source?: string;
  location_precision?: string;
}

export interface UserSkill {
  id: string;
  skill_id: string;
  skill_name: string;
  proficiency?: string | null;
  years_experience?: number | null;
  created_at: string;
}

export interface SkillCreatePayload {
  name: string;
  proficiency?: string;
  years_experience?: number;
}

export interface FullProfile {
  user: User;
  profile?: Profile | null;
  location?: Location | null;
  skills: UserSkill[];
}

export interface PublicProfile {
  user: {
    id: string;
    name: string;
    role: string;
    created_at: string;
  };
  profile?: Profile | null;
  location?: {
    city?: string | null;
    area?: string | null;
    state?: string | null;
    country?: string | null;
  } | null;
  skills: UserSkill[];
  reputation?: {
    user_id: string;
    average_rating?: number | null;
    review_count: number;
    status: string;
  } | null;
  public_availability?: {
    user_id: string;
    helper_timezone: string;
    capacity_status: string;
    has_schedule_configured: boolean;
    next_available_date?: string | null;
    coarse_windows: string[];
    active_slots_count: number;
  } | null;
}
