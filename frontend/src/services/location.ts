import { api } from "./api";
import type {
  AutocompleteResponse,
  ResolvedLocation,
  RequestLocationResponse,
} from "../types/google-location";

export async function autocompletePlaces(
  inputText: string,
  sessionToken?: string
): Promise<AutocompleteResponse> {
  const resp = await api.get<AutocompleteResponse>("/api/location/autocomplete", {
    params: { input_text: inputText, session_token: sessionToken },
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

export async function getPlaceDetails(placeId: string): Promise<ResolvedLocation> {
  const resp = await api.get<ResolvedLocation>(`/api/location/place/${encodeURIComponent(placeId)}`);
  return resp.data;
}

export async function getRequestTargetLocation(
  requestId: string
): Promise<RequestLocationResponse> {
  const resp = await api.get<RequestLocationResponse>(`/api/location/request/${requestId}`);
  return resp.data;
}
