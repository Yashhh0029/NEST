export interface PlaceAutocompletePrediction {
  place_id: string;
  main_text: string;
  secondary_text?: string | null;
  description: string;
}

export interface AutocompleteResponse {
  predictions: PlaceAutocompletePrediction[];
}

export interface ResolvedLocation {
  google_place_id?: string | null;
  formatted_address?: string | null;
  name?: string | null;
  display_name?: string | null;
  city?: string | null;
  area?: string | null;
  taluka?: string | null;
  district?: string | null;
  state?: string | null;
  country: string;
  postal_code?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  location_precision: string;
  location_source: string;
  road?: string | null;
  neighborhood?: string | null;
  suburb?: string | null;
  premise?: string | null;
  subpremise?: string | null;
  street_number?: string | null;
  route?: string | null;
  sublocality?: string | null;
  locality?: string | null;
  short_display_name?: string | null;
  full_display_address?: string | null;
  is_unresolved?: boolean;
}


export interface RequestLocationResponse {
  id: string;
  request_id: string;
  google_place_id?: string | null;
  display_name?: string | null;
  formatted_address?: string | null;
  city?: string | null;
  area?: string | null;
  state?: string | null;
  country: string;
  postal_code?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  location_source: string;
  location_precision: string;
  created_at: string;
  updated_at: string;
}
