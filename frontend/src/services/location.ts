import { api } from "./api";
import type {
  AutocompleteResponse,
  ResolvedLocation,
  RequestLocationResponse,
} from "../types/google-location";

export async function autocompletePlaces(
  inputText: string,
  sessionToken?: string,
  latitude?: number | null,
  longitude?: number | null,
  radiusMeters?: number | null,
  primaryType?: string
): Promise<AutocompleteResponse> {
  const params: Record<string, any> = { input_text: inputText };
  if (sessionToken) params.session_token = sessionToken;
  if (latitude != null) params.latitude = latitude;
  if (longitude != null) params.longitude = longitude;
  if (radiusMeters != null) params.radius_meters = radiusMeters;
  if (primaryType) params.primary_type = primaryType;

  const resp = await api.get<AutocompleteResponse>("/api/location/autocomplete", {
    params,
  });
  return resp.data;
}

export async function resolveAddressText(text: string): Promise<ResolvedLocation> {
  const resp = await api.post<ResolvedLocation>("/api/location/resolve", { text });
  return resp.data;
}

export async function reverseGeocodeCoordinates(
  latitude: number,
  longitude: number
): Promise<ResolvedLocation> {
  const resp = await api.post<ResolvedLocation>("/api/location/reverse-geocode", {
    latitude,
    longitude,
  });
  return resp.data;
}

export async function getPlaceDetails(placeId: string, sessionToken?: string): Promise<ResolvedLocation> {
  const params: Record<string, any> = {};
  if (sessionToken) params.session_token = sessionToken;
  const resp = await api.get<ResolvedLocation>(`/api/location/place/${encodeURIComponent(placeId)}`, {
    params,
  });
  return resp.data;
}

export async function getRequestTargetLocation(
  requestId: string
): Promise<RequestLocationResponse> {
  const resp = await api.get<RequestLocationResponse>(`/api/location/request/${requestId}`);
  return resp.data;
}
