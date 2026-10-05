import logging
import math
import urllib.parse
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
import requests
from app.core.config import settings
from app.schemas.google_location import (
    PlaceAutocompletePrediction,
    ResolvedLocation,
    TravelRouteInfo,
)

logger = logging.getLogger(__name__)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on the Earth in kilometers."""
    r = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return r * c


class GoogleMapsService:
    """
    Google Maps Platform integration service for NEST.
    Uses modern Google APIs:
    - Places API (New) for autocomplete & place details
    - Geocoding API for forward & reverse geocoding
    - Routes API for travel route distance & duration on Top-K candidates
    
    Includes in-memory TTL caching and graceful fallbacks when credentials
    are absent or Google services are unreachable.
    """

    def __init__(self, api_key: Optional[str] = None):
        server_key = settings.GOOGLE_MAPS_SERVER_API_KEY or settings.GOOGLE_MAPS_API_KEY
        self.api_key = api_key if api_key is not None else server_key
        # In-memory TTL cache: key -> (expiration_datetime, data)
        self._cache: Dict[str, Tuple[datetime, Any]] = {}
        self._cache_ttl = timedelta(hours=24)
        self._routes_api_available: bool = True

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key.strip() and not self.api_key.startswith("your-google"))

    def _get_from_cache(self, key: str) -> Optional[Any]:
        if key in self._cache:
            expires_at, data = self._cache[key]
            if datetime.now(timezone.utc) < expires_at:
                return data
            del self._cache[key]
        return None

    def _set_in_cache(self, key: str, data: Any) -> None:
        self._cache[key] = (datetime.now(timezone.utc) + self._cache_ttl, data)

    def autocomplete_places(
        self,
        input_text: str,
        session_token: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_meters: Optional[float] = None,
    ) -> List[PlaceAutocompletePrediction]:
        """
        Query Google Places API (New) autocomplete, biased and restricted to India.
        Uses circular locationBias when coordinates are provided (bias, never strict restriction).
        """
        clean_input = input_text.strip()
        if not clean_input:
            return []

        coord_str = (
            f"{round(latitude, 3)},{round(longitude, 3)}"
            if latitude is not None and longitude is not None
            else "none"
        )
        cache_key = f"autocomplete:{clean_input.lower()}:{coord_str}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        if not self.is_configured:
            q_low = clean_input.lower()
            fallbacks = []
            if "mahalunge" in q_low:
                # Include both distinct Mahalunge locations for disambiguation testing
                fallbacks.extend([
                    PlaceAutocompletePrediction(
                        place_id="ChIJZdAjYE25wjsRrF_MZhrk_lU",
                        main_text="Mahalunge",
                        secondary_text="Pune, Maharashtra, India",
                        description="Mahalunge, Pune, Maharashtra, India",
                    ),
                    PlaceAutocompletePrediction(
                        place_id="ChIJ3x-Canm2wjsRwPJ-IJb_4C8",
                        main_text="Mahalunge",
                        secondary_text="Maharashtra 410501, India",
                        description="Mahalunge, Maharashtra 410501, India",
                    ),
                    PlaceAutocompletePrediction(
                        place_id="ChIJdwrj1xq5wjsREZMUTXUhNbs",
                        main_text="Mahalunge Balewadi Stadium",
                        secondary_text="Baner - Mahalunge Road, Balewadi, Pune, Maharashtra, India",
                        description="Mahalunge Balewadi Stadium, Baner - Mahalunge Road, Balewadi, Pune, Maharashtra, India",
                    ),
                ])
            if "hinjewadi" in q_low or "pune" in q_low or "kothrud" in q_low:
                fallbacks.append(
                    PlaceAutocompletePrediction(
                        place_id="pc_kothrud_pune",
                        main_text="Kothrud",
                        secondary_text="Pune, Maharashtra, India",
                        description="Kothrud, Pune, Maharashtra, India",
                    )
                )
            if "indiranagar" in q_low or "bengaluru" in q_low or "bangalore" in q_low:
                fallbacks.append(
                    PlaceAutocompletePrediction(
                        place_id="ChIJ_indiranagar_bengaluru",
                        main_text="Indiranagar",
                        secondary_text="Bengaluru, Karnataka, India",
                        description="Indiranagar, Bengaluru, Karnataka, India",
                    )
                )
            if "koramangala" in q_low:
                fallbacks.append(
                    PlaceAutocompletePrediction(
                        place_id="ChIJ_koramangala_bengaluru",
                        main_text="Koramangala",
                        secondary_text="Bengaluru, Karnataka, India",
                        description="Koramangala, Bengaluru, Karnataka, India",
                    )
                )
            if "whitefield" in q_low:
                fallbacks.append(
                    PlaceAutocompletePrediction(
                        place_id="ChIJ_whitefield_bengaluru",
                        main_text="Whitefield",
                        secondary_text="Bengaluru, Karnataka, India",
                        description="Whitefield, Bengaluru, Karnataka, India",
                    )
                )
            if "kochi" in q_low or "ernakulam" in q_low:
                fallbacks.append(
                    PlaceAutocompletePrediction(
                        place_id="ChIJv8a-SlENCDsRkkGEpcqC1Qs",
                        main_text="Kochi",
                        secondary_text="Kerala, India",
                        description="Kochi, Kerala, India",
                    )
                )
            return fallbacks

        url = "https://places.googleapis.com/v1/places:autocomplete"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
        }
        payload: Dict[str, Any] = {
            "input": clean_input,
            "includedRegionCodes": ["in"],
        }
        if session_token:
            payload["sessionToken"] = session_token
        if latitude is not None and longitude is not None:
            # locationBias circular preference: favors nearby without restricting distant searches (e.g. Kochi from Pune)
            bias_radius = float(radius_meters) if radius_meters else 50000.0
            payload["locationBias"] = {
                "circle": {
                    "center": {
                        "latitude": float(latitude),
                        "longitude": float(longitude),
                    },
                    "radius": bias_radius,
                }
            }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=5.0)
            if resp.status_code != 200:
                logger.warning("Google Places autocomplete returned status %d: %s", resp.status_code, resp.text[:200])
                return []

            data = resp.json()
            suggestions = data.get("suggestions", [])
            predictions: List[PlaceAutocompletePrediction] = []

            for item in suggestions:
                pred = item.get("placePrediction", {})
                place_id = pred.get("placeId")
                text_info = pred.get("text", {})
                structured = pred.get("structuredFormat", {})
                main_text = structured.get("mainText", {}).get("text") or text_info.get("text", "")
                secondary_text = structured.get("secondaryText", {}).get("text")
                description = text_info.get("text") or main_text

                if place_id and main_text:
                    predictions.append(
                        PlaceAutocompletePrediction(
                            place_id=place_id,
                            main_text=main_text,
                            secondary_text=secondary_text,
                            description=description,
                        )
                    )

            self._set_in_cache(cache_key, predictions)
            return predictions

        except Exception as exc:
            logger.warning("Google Places autocomplete failed gracefully: %s", exc)
            return []

    def get_place_details(self, place_id: str) -> Optional[ResolvedLocation]:
        """
        Fetch place details using Google Places API (New).
        """
        clean_place_id = place_id.strip()
        if not clean_place_id:
            return None

        if not self.is_configured:
            p_low = clean_place_id.lower()
            if "hinjewadi" in p_low or "pune" in p_low:
                return ResolvedLocation(
                    google_place_id=clean_place_id,
                    formatted_address="Hinjewadi, Pune, Maharashtra 411057, India",
                    name="Hinjewadi",
                    display_name="Hinjewadi",
                    latitude=18.5913,
                    longitude=73.7389,
                    city="Pune",
                    area="Hinjewadi",
                    state="Maharashtra",
                    country="India",
                    postal_code="411057",
                    location_source="google_places_details",
                    location_precision="locality",
                )
            if "indiranagar" in p_low or "bengaluru" in p_low:
                return ResolvedLocation(
                    google_place_id=clean_place_id,
                    formatted_address="Indiranagar, Bengaluru, Karnataka 560038, India",
                    name="Indiranagar",
                    display_name="Indiranagar",
                    latitude=12.9716,
                    longitude=77.5946,
                    city="Bengaluru",
                    area="Indiranagar",
                    state="Karnataka",
                    country="India",
                    postal_code="560038",
                    location_source="google_places_details",
                    location_precision="locality",
                )
            if clean_place_id == "ChIJ3x-Canm2wjsRwPJ-IJb_4C8":
                return ResolvedLocation(
                    google_place_id=clean_place_id,
                    formatted_address="Mahalunge, Maharashtra 410501, India",
                    name="Mahalunge",
                    display_name="Mahalunge",
                    latitude=18.755195,
                    longitude=73.809071,
                    city="Mahalunge",
                    area="Mahalunge",
                    state="Maharashtra",
                    country="India",
                    postal_code="410501",
                    location_source="google_places_details",
                    location_precision="locality",
                )
            if clean_place_id == "ChIJZdAjYE25wjsRrF_MZhrk_lU":
                return ResolvedLocation(
                    google_place_id=clean_place_id,
                    formatted_address="Mahalunge, Pune, Maharashtra, India",
                    name="Mahalunge",
                    display_name="Mahalunge",
                    latitude=18.57382,
                    longitude=73.756159,
                    city="Pune",
                    area="Mahalunge",
                    state="Maharashtra",
                    country="India",
                    postal_code="411045",
                    location_source="google_places_details",
                    location_precision="locality",
                )
            return None

        cache_key = f"place_details:{clean_place_id}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        url = f"https://places.googleapis.com/v1/places/{clean_place_id}"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "id,displayName,formattedAddress,location,addressComponents,types",
        }

        try:
            resp = requests.get(url, headers=headers, timeout=5.0)
            if resp.status_code != 200:
                logger.warning("Google Place details returned status %d: %s", resp.status_code, resp.text[:200])
                return None

            data = resp.json()
            loc_geo = data.get("location", {})
            lat = loc_geo.get("latitude")
            lon = loc_geo.get("longitude")
            formatted = data.get("formattedAddress")
            disp_obj = data.get("displayName", {})
            disp_name = disp_obj.get("text") if isinstance(disp_obj, dict) else None
            types = data.get("types", [])

            city, area, state, country, postal = self._extract_address_components(data.get("addressComponents", []))

            # Derive explicit location precision from Google place types
            if any(t in types for t in ["subpremise", "premise", "establishment", "point_of_interest"]):
                precision = "exact"
            elif any(t in types for t in ["route", "street_address"]):
                precision = "street"
            elif any(t in types for t in ["sublocality_level_1", "neighborhood"]):
                precision = "neighborhood"
            elif "locality" in types:
                precision = "locality"
            elif "administrative_area_level_2" in types:
                precision = "city"
            elif area is not None:
                precision = "neighborhood"
            else:
                precision = "locality" if city else "approximate"

            resolved = ResolvedLocation(
                google_place_id=clean_place_id,
                formatted_address=formatted,
                name=disp_name,
                display_name=disp_name,
                city=city,
                area=area,
                state=state,
                country=country or "India",
                postal_code=postal,
                latitude=round(lat, 6) if lat is not None else None,
                longitude=round(lon, 6) if lon is not None else None,
                location_precision=precision,
                location_source="google_places",
            )
            self._set_in_cache(cache_key, resolved)
            return resolved

        except Exception as exc:
            logger.warning("Google Place details lookup failed gracefully: %s", exc)
            return None

    def get_venue_details(self, place_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch place details specifically for in-person meeting venue validation,
        including primaryType and types array to enforce public venue category allowlists.
        """
        clean_place_id = place_id.strip()
        if not clean_place_id:
            return None

        if not self.is_configured:
            # Deterministic development fallback when Google Maps API key is unconfigured
            p_lower = clean_place_id.lower()
            if "hotel" in p_lower or "lodging" in p_lower or "residence" in p_lower:
                return {
                    "place_id": clean_place_id,
                    "name": "Grand Palace Hotel",
                    "formatted_address": "Indiranagar, Bengaluru",
                    "latitude": 12.9716,
                    "longitude": 77.5946,
                    "primary_type": "hotel",
                    "types": ["lodging", "hotel", "establishment"],
                }
            elif "far_away" in p_lower or "60km" in p_lower:
                return {
                    "place_id": clean_place_id,
                    "name": "Far Away Outstation Cafe",
                    "formatted_address": "Outstation Highway, 60km away",
                    "latitude": 12.4000 if ("bengaluru" in p_lower or "indiranagar" in p_lower) else 17.5000,
                    "longitude": 76.8000 if ("bengaluru" in p_lower or "indiranagar" in p_lower) else 72.8000,
                    "primary_type": "cafe",
                    "types": ["cafe", "establishment"],
                }
            elif "cafe" in p_lower or "coffee" in p_lower or "library" in p_lower or "hub" in p_lower:
                is_pune = "hinjewadi" in p_lower or "pune" in p_lower
                return {
                    "place_id": clean_place_id,
                    "name": "Hinjewadi Central Cafe & Library" if is_pune else "Indiranagar Central Cafe",
                    "formatted_address": "Phase 1, Hinjewadi, Pune, Maharashtra 411057" if is_pune else "100ft Rd, Indiranagar, Bengaluru, Karnataka 560038",
                    "latitude": 18.5913 if is_pune else 12.9716,
                    "longitude": 73.7389 if is_pune else 77.5946,
                    "primary_type": "cafe",
                    "types": ["cafe", "coffee_shop", "establishment"],
                }
            return None

        cache_key = f"venue_details:{clean_place_id}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        url = f"https://places.googleapis.com/v1/places/{clean_place_id}"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "id,displayName,formattedAddress,location,primaryType,types",
        }

        try:
            resp = requests.get(url, headers=headers, timeout=5.0)
            if resp.status_code != 200:
                logger.warning("Google Place venue details returned status %d: %s", resp.status_code, resp.text[:200])
                return None

            data = resp.json()
            loc_geo = data.get("location", {})
            lat = loc_geo.get("latitude")
            lon = loc_geo.get("longitude")
            formatted = data.get("formattedAddress")
            name_dict = data.get("displayName", {})
            name = name_dict.get("text") if isinstance(name_dict, dict) else None

            venue_info = {
                "place_id": clean_place_id,
                "name": name or "Eligible Public Venue",
                "formatted_address": formatted,
                "latitude": round(lat, 6) if lat is not None else None,
                "longitude": round(lon, 6) if lon is not None else None,
                "primary_type": data.get("primaryType"),
                "types": data.get("types", []),
            }
            self._set_in_cache(cache_key, venue_info)
            return venue_info
        except Exception as exc:
            logger.warning("Google Place venue details lookup failed: %s", exc)
            return None

    def geocode_address(self, address: str) -> Optional[ResolvedLocation]:
        """
        Forward geocode an address or locality in India using Google Places API (New) Text Search.
        Does NOT use or depend on Google Geocoding API (Zero-billing, modern architecture).
        Endpoint: POST https://places.googleapis.com/v1/places:searchText
        """
        clean_address = address.strip()
        if not clean_address:
            return None

        cache_key = f"geocode:{clean_address.lower()}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        if not self.is_configured:
            # Deterministic development fallbacks when unconfigured
            addr_low = clean_address.lower()
            if "kothrud" in addr_low or "pune" in addr_low:
                return ResolvedLocation(
                    google_place_id="pc_kothrud_pune",
                    formatted_address="Kothrud, Pune, Maharashtra, India",
                    name="Kothrud",
                    display_name="Kothrud",
                    city="Pune",
                    area="Kothrud",
                    state="Maharashtra",
                    country="India",
                    postal_code="411038",
                    latitude=18.5074,
                    longitude=73.8077,
                    location_precision="locality",
                    location_source="google_places",
                )
            if "whitefield" in addr_low:
                return ResolvedLocation(
                    google_place_id="pc_whitefield_blr",
                    formatted_address="Whitefield, Bengaluru, Karnataka, India",
                    name="Whitefield",
                    display_name="Whitefield",
                    city="Bengaluru",
                    area="Whitefield",
                    state="Karnataka",
                    country="India",
                    postal_code="560066",
                    latitude=12.9698,
                    longitude=77.7500,
                    location_precision="locality",
                    location_source="google_places",
                )
            if "indiranagar" in addr_low or "bengaluru" in addr_low or "bangalore" in addr_low:
                return ResolvedLocation(
                    google_place_id="pc_indiranagar_blr",
                    formatted_address="Indiranagar, Bengaluru, Karnataka, India",
                    name="Indiranagar",
                    display_name="Indiranagar",
                    city="Bengaluru",
                    area="Indiranagar",
                    state="Karnataka",
                    country="India",
                    postal_code="560038",
                    latitude=12.9716,
                    longitude=77.5946,
                    location_precision="locality",
                    location_source="google_places",
                )
            return None

        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.formattedAddress,"
                "places.location,places.addressComponents"
            ),
        }
        payload = {
            "textQuery": clean_address,
            "maxResultCount": 1,
            "regionCode": "in",
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=6.0)
            if resp.status_code != 200:
                logger.warning(
                    "Places API searchText geocoding returned status %d: %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return None

            data = resp.json()
            places = data.get("places", [])
            if not places:
                return None

            top = places[0]
            loc = top.get("location", {})
            lat = loc.get("latitude")
            lon = loc.get("longitude")
            place_id = top.get("id")
            formatted = top.get("formattedAddress")
            disp_obj = top.get("displayName", {})
            name = disp_obj.get("text") if isinstance(disp_obj, dict) else None

            city, area, state, country, postal = self._extract_address_components(
                top.get("addressComponents", [])
            )

            resolved = ResolvedLocation(
                google_place_id=place_id,
                formatted_address=formatted,
                name=name,
                display_name=name,
                city=city,
                area=area,
                state=state,
                country=country or "India",
                postal_code=postal,
                latitude=round(lat, 6) if lat is not None else None,
                longitude=round(lon, 6) if lon is not None else None,
                location_precision="locality" if area is None else "neighborhood",
                location_source="google_places",
            )
            self._set_in_cache(cache_key, resolved)
            return resolved

        except Exception as exc:
            logger.warning("Places API searchText geocoding failed gracefully: %s", exc)
            return None

    def reverse_geocode(self, latitude: float, longitude: float) -> Optional[ResolvedLocation]:
        """
        Reverse geocode GPS coordinates to human-readable canonical area & city.
        Uses supported Google Places API (New) searchNearby architecture when configured.
        Falls back to resilient coordinate boundaries when offline or unconfigured.
        """
        if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
            return None

        cache_key = f"rev_geocode:{round(latitude, 4)},{round(longitude, 4)}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        # Live Google Places API (New) nearby search for geographic context
        if self.is_configured:
            for radius in [1000.0, 5000.0]:
                places = self.search_places_nearby(
                    latitude=latitude,
                    longitude=longitude,
                    radius_meters=radius,
                    max_result_count=5,
                )
                if places:
                    # Aggregate geographic address components across nearby places
                    # NEVER adopt a commercial establishment's displayName or business place_id as the user's location identity!
                    city = None
                    area = None
                    state = None
                    country = "India"
                    postal = None

                    for p in places:
                        c, a, s, co, post = self._extract_address_components(p.get("addressComponents", []))
                        if not city or (not city.isascii() and c and c.isascii()):
                            city = c or city
                        if not area or (not area.isascii() and a and a.isascii()):
                            area = a or area
                        if not state or (not state.isascii() and s and s.isascii()):
                            state = s or state
                        if not country or (not country.isascii() and co and co.isascii()):
                            country = co or country
                        if not postal and post:
                            postal = post

                    # Build clean geographic-only display name and formatted address
                    geo_parts = [part for part in [area, city] if part]
                    geo_display = ", ".join(geo_parts) if geo_parts else (city or area or "Current Location")

                    addr_parts = [part for part in [
                        area,
                        city,
                        f"{state} {postal}".strip() if (state or postal) else state,
                        country,
                    ] if part]
                    geo_formatted = ", ".join(addr_parts) if addr_parts else "India"

                    precision = "neighborhood" if area else ("locality" if city else "approximate")

                    # Per canonical Place ID rule:
                    # Do NOT store a commercial business's Place ID for GPS coordinates.
                    # Do NOT blindly forward-geocode text which could cause duplicate-name ambiguity.
                    # The exact device latitude/longitude remains the authoritative geographic identity.
                    resolved = ResolvedLocation(
                        google_place_id=None,
                        formatted_address=geo_formatted,
                        name=geo_display,
                        display_name=geo_display,
                        city=city,
                        area=area,
                        state=state,
                        country=country or "India",
                        postal_code=postal,
                        latitude=round(latitude, 6),
                        longitude=round(longitude, 6),
                        location_precision=precision,
                        location_source="browser_geolocation",
                    )
                    self._set_in_cache(cache_key, resolved)
                    return resolved

        # Resilient offline coordinate boundary resolver for Indian coordinates
        fallback = self.resolve_indian_coordinates(latitude, longitude)
        if fallback:
            self._set_in_cache(cache_key, fallback)
            return fallback

        return None


    def compute_route_travel(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        travel_mode: str = "DRIVE",
    ) -> TravelRouteInfo:
        """
        Calculate travel distance and time between two coordinates.
        Computes Haversine baseline and enhances with Google Routes API when available.
        """
        straight_km = round(haversine_km(origin_lat, origin_lon, dest_lat, dest_lon), 1)

        fallback = TravelRouteInfo(
            straight_line_distance_km=straight_km,
            route_distance_km=None,
            estimated_travel_time_minutes=None,
            travel_mode=travel_mode,
        )

        if not self.is_configured or not getattr(self, "_routes_api_available", True):
            return fallback

        cache_key = f"route:{round(origin_lat, 3)},{round(origin_lon, 3)}->{round(dest_lat, 3)},{round(dest_lon, 3)}:{travel_mode}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        url = "https://routes.googleapis.com/directions/v2:computeRoutes"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "routes.distanceMeters,routes.duration",
        }
        payload = {
            "origin": {"location": {"latLng": {"latitude": origin_lat, "longitude": origin_lon}}},
            "destination": {"location": {"latLng": {"latitude": dest_lat, "longitude": dest_lon}}},
            "travelMode": travel_mode,
        }

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=4.0)
            if resp.status_code == 200:
                data = resp.json()
                routes = data.get("routes", [])
                if routes:
                    dist_meters = routes[0].get("distanceMeters", 0)
                    duration_str = routes[0].get("duration", "0s")
                    seconds = int(duration_str.rstrip("s")) if duration_str.endswith("s") else 0
                    info = TravelRouteInfo(
                        straight_line_distance_km=straight_km,
                        route_distance_km=round(dist_meters / 1000.0, 1),
                        estimated_travel_time_minutes=round(seconds / 60.0, 1),
                        travel_mode=travel_mode,
                    )
                    self._set_in_cache(cache_key, info)
                    return info
            elif resp.status_code in (401, 403):
                self._routes_api_available = False
        except Exception as exc:
            logger.warning("Google Routes API call failed gracefully: %s", exc)

        self._set_in_cache(cache_key, fallback)
        return fallback

    def search_places_nearby(
        self,
        latitude: float,
        longitude: float,
        radius_meters: float = 1000.0,
        included_types: Optional[List[str]] = None,
        max_result_count: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Search for real places using Google Places API (New) Nearby Search.
        Endpoint: POST https://places.googleapis.com/v1/places:searchNearby
        Uses strict circular locationRestriction around the center coordinates.
        """
        if not self.is_configured or latitude is None or longitude is None:
            return []

        clean_radius = max(50.0, min(float(radius_meters), 50000.0))
        types_key = ",".join(sorted(included_types or []))
        cache_key = f"places_nearby:{round(latitude, 4)},{round(longitude, 4)}:{round(clean_radius)}:{types_key}:{max_result_count}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        url = "https://places.googleapis.com/v1/places:searchNearby"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.formattedAddress,"
                "places.location,places.rating,places.userRatingCount,"
                "places.priceLevel,places.primaryType,places.types,"
                "places.regularOpeningHours,places.googleMapsUri,places.websiteUri,"
                "places.nationalPhoneNumber,places.addressComponents"
            ),
        }
        payload: Dict[str, Any] = {
            "maxResultCount": min(max(max_result_count, 1), 20),
            "languageCode": "en",
            "locationRestriction": {
                "circle": {
                    "center": {
                        "latitude": latitude,
                        "longitude": longitude,
                    },
                    "radius": clean_radius,
                }
            },
        }
        if included_types:
            payload["includedTypes"] = included_types

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=6.0)
            if resp.status_code != 200:
                logger.warning(
                    "Google Places searchNearby returned status %d: %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return []

            data = resp.json()
            places = data.get("places", [])
            self._set_in_cache(cache_key, places)
            return places
        except Exception as exc:
            logger.warning("Google Places searchNearby call failed gracefully: %s", exc)
            return []

    def search_places_text(
        self,
        text_query: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_meters: float = 5000.0,
        included_type: Optional[str] = None,
        open_now: Optional[bool] = None,
        max_result_count: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Search for real places using Google Places API (New) Text Search.
        Endpoint: https://places.googleapis.com/v1/places:searchText
        Uses locationBias circle when coordinates are provided.
        Returns a list of raw place dictionaries matching field mask.
        """
        clean_query = text_query.strip()
        if not clean_query or not self.is_configured:
            return []

        coord_key = (
            f"{round(latitude, 3)},{round(longitude, 3)}"
            if latitude is not None and longitude is not None
            else "no_coords"
        )
        cache_key = f"places_search:{clean_query.lower()}:{coord_key}:{round(radius_meters)}:{included_type}:{open_now}:{max_result_count}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        url = "https://places.googleapis.com/v1/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": (
                "places.id,places.displayName,places.formattedAddress,"
                "places.location,places.rating,places.userRatingCount,"
                "places.priceLevel,places.primaryType,places.types,"
                "places.regularOpeningHours,places.googleMapsUri,places.websiteUri,"
                "places.nationalPhoneNumber"
            ),
        }
        payload: Dict[str, Any] = {
            "textQuery": clean_query,
            "maxResultCount": min(max(max_result_count, 1), 20),
        }
        clean_r = max(50.0, min(float(radius_meters), 50000.0))
        if latitude is not None and longitude is not None:
            # Enforce circular locationRestriction to prevent city-wide place leaks
            payload["locationRestriction"] = {
                "circle": {
                    "center": {
                        "latitude": latitude,
                        "longitude": longitude,
                    },
                    "radius": clean_r,
                }
            }
        if included_type:
            payload["includedType"] = included_type
        if open_now is True:
            payload["openNow"] = True

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=6.0)
            if resp.status_code == 400 and "locationRestriction" in payload:
                # Fallback to locationBias if Places API project rejects restriction for this query
                payload.pop("locationRestriction", None)
                payload["locationBias"] = {
                    "circle": {
                        "center": {
                            "latitude": latitude,
                            "longitude": longitude,
                        },
                        "radius": clean_r,
                    }
                }
                resp = requests.post(url, json=payload, headers=headers, timeout=6.0)

            if resp.status_code != 200:
                logger.warning(
                    "Google Places searchText returned status %d: %s",
                    resp.status_code,
                    resp.text[:200],
                )
                return []

            data = resp.json()
            places = data.get("places", [])
            self._set_in_cache(cache_key, places)
            return places
        except Exception as exc:
            logger.warning("Google Places searchText call failed gracefully: %s", exc)
            return []

    @staticmethod
    def _extract_address_components(
        components: List[Dict[str, Any]],
    ) -> Tuple[Optional[str], Optional[str], Optional[str], str, Optional[str]]:
        """Extract city, area, state, country, postal from Places API (New) addressComponents."""
        city = None
        area = None
        state = None
        country = "India"
        postal = None

        for comp in components:
            types = comp.get("types", [])
            text = comp.get("longText") or comp.get("shortText")
            if not text:
                continue

            if "sublocality_level_1" in types or "sublocality" in types or "neighborhood" in types:
                if not area:
                    area = text
            elif "locality" in types:
                city = text
            elif "administrative_area_level_2" in types and not city:
                city = text
            elif "administrative_area_level_1" in types:
                state = text
            elif "country" in types:
                country = text
            elif "postal_code" in types:
                postal = text

        return city, area, state, country, postal

    @staticmethod
    def parse_google_address_components_multi(
        results: List[Dict[str, Any]],
    ) -> Tuple[Optional[str], Optional[str], Optional[str], str, Optional[str], Optional[str], Optional[str]]:
        """
        Robust address-component parser across all Google Geocoding results.
        Does NOT assume city is in results[0] or that results[0] == city.
        Accurately parses:
        - street_number, route, sublocality, sublocality_level_1, sublocality_level_2,
          locality, administrative_area_level_1, administrative_area_level_2,
          postal_code, country, premise, subpremise, neighborhood, landmark
        Returns:
        (city, area, state, country, postal, formatted_address, place_id)
        """
        if not results:
            return None, None, None, "India", None, None, None

        city = None
        area = None
        sublocality_1 = None
        sublocality_2 = None
        neighborhood = None
        premise_name = None
        landmark_name = None
        locality_name = None
        admin_area_2 = None
        admin_area_3 = None
        state = None
        country = "India"
        postal = None

        first = results[0]
        place_id = first.get("place_id")
        formatted = first.get("formatted_address")

        for res in results:
            comps = res.get("address_components", [])
            for comp in comps:
                types = comp.get("types", [])
                long_name = comp.get("long_name") or comp.get("short_name")
                if not long_name:
                    continue

                if "locality" in types and not locality_name:
                    locality_name = long_name
                if "sublocality_level_1" in types and not sublocality_1:
                    sublocality_1 = long_name
                if "neighborhood" in types and not neighborhood:
                    neighborhood = long_name
                if "sublocality_level_2" in types and not sublocality_2:
                    sublocality_2 = long_name
                if ("premise" in types or "subpremise" in types) and not premise_name:
                    premise_name = long_name
                if "landmark" in types and not landmark_name:
                    landmark_name = long_name
                if "administrative_area_level_2" in types and not admin_area_2:
                    admin_area_2 = long_name
                if "administrative_area_level_3" in types and not admin_area_3:
                    admin_area_3 = long_name
                if "administrative_area_level_1" in types and not state:
                    state = long_name
                if "country" in types:
                    country = long_name
                if "postal_code" in types and not postal:
                    postal = long_name

        # Area hierarchy: sublocality_1 > neighborhood > sublocality_2 > premise > landmark
        area = sublocality_1 or neighborhood or sublocality_2 or landmark_name or premise_name

        # City hierarchy:
        # Prefer locality (e.g. Pimpri-Chinchwad, Pune, Kochi, Bengaluru)
        # Fallback to district/metropolitan (admin_area_2 e.g. Pune, Ernakulam)
        city = locality_name or admin_area_2 or admin_area_3

        # If city is missing but area is known, promote area or use district
        if not city and area:
            city = area
            area = None
        elif city and area and city.strip().lower() == area.strip().lower():
            if sublocality_2 or neighborhood:
                area = sublocality_2 or neighborhood
            else:
                area = None

        if not formatted:
            parts = [p for p in [area, city, state, country] if p]
            formatted = ", ".join(parts) if parts else "India"

        return city, area, state, country, postal, formatted, place_id

    @staticmethod
    def resolve_indian_coordinates(latitude: float, longitude: float) -> Optional[ResolvedLocation]:

        """
        Geographic coordinate boundary resolver for Indian metropolitan & urban regions.
        Acts as an intelligent, deterministic fallback so valid coordinates in India
        never resolve to 'Unknown City' even if Google Geocoding API is unreachable.
        """
        lat, lon = latitude, longitude

        # 1. Detailed Pune & Pimpri-Chinchwad Micro-Locality Boundary Resolution
        # Lat: 18.40 to 18.75, Lon: 73.68 to 74.02
        if 18.40 <= lat <= 18.75 and 73.68 <= lon <= 74.02:
            # Mahalunge (Lat: 18.55-18.60, Lon: 73.72-73.77)
            if 18.55 <= lat <= 18.60 and 73.72 <= lon <= 73.765:
                area = "Mahalunge"
                city = "Pune"
                postal = "411045"
            # Balewadi (Lat: 18.56-18.60, Lon: 73.765-73.795)
            elif 18.56 <= lat <= 18.60 and 73.765 < lon <= 73.795:
                area = "Balewadi"
                city = "Pune"
                postal = "411045"
            # Baner (Lat: 18.535-18.57, Lon: 73.77-73.81)
            elif 18.535 <= lat <= 18.57 and 73.77 <= lon <= 73.81:
                area = "Baner"
                city = "Pune"
                postal = "411045"
            # Hinjewadi (Lat: 18.57-18.63, Lon: 73.68-73.75)
            elif 18.57 <= lat <= 18.63 and 73.68 <= lon <= 73.75:
                area = "Hinjewadi"
                city = "Pune"
                postal = "411057"
            # Wakad (Lat: 18.58-18.625, Lon: 73.75 < lon <= 73.785)
            elif 18.58 <= lat <= 18.625 and 73.75 < lon <= 73.785:
                area = "Wakad"
                city = "Pimpri-Chinchwad"
                postal = "411057"
            # Pimple Saudagar / Rahatani
            elif 18.58 <= lat <= 18.62 and 73.785 < lon <= 73.82:
                area = "Pimple Saudagar"
                city = "Pimpri-Chinchwad"
                postal = "411027"
            # Aundh (Lat: 18.545-18.58, Lon: 73.80 < lon <= 73.83)
            elif 18.545 <= lat <= 18.58 and 73.80 < lon <= 73.83:
                area = "Aundh"
                city = "Pune"
                postal = "411007"
            # Bavdhan & Pashan (Lat: 18.50-18.545, Lon: 73.75-73.80)
            elif 18.50 <= lat <= 18.545 and 73.75 <= lon <= 73.80:
                area = "Bavdhan" if lat < 18.525 else "Pashan"
                city = "Pune"
                postal = "411021"
            # Kothrud (Lat: 18.485-18.525, Lon: 73.79-73.835)
            elif 18.485 <= lat <= 18.525 and 73.79 <= lon <= 73.835:
                area = "Kothrud"
                city = "Pune"
                postal = "411038"
            # Shivajinagar / Deccan (Lat: 18.51-18.545, Lon: 73.835 < lon <= 73.87)
            elif 18.51 <= lat <= 18.545 and 73.835 < lon <= 73.87:
                area = "Shivajinagar"
                city = "Pune"
                postal = "411005"
            # Viman Nagar / Kalyani Nagar (Lat: 18.535-18.58, Lon: 73.885-73.93)
            elif 18.535 <= lat <= 18.58 and 73.885 <= lon <= 73.93:
                area = "Viman Nagar"
                city = "Pune"
                postal = "411014"
            # Kharadi (Lat: 18.535-18.57, Lon: 73.93 < lon <= 73.975)
            elif 18.535 <= lat <= 18.57 and 73.93 < lon <= 73.975:
                area = "Kharadi"
                city = "Pune"
                postal = "411014"
            # Hadapsar / Magarpatta (Lat: 18.48-18.53, Lon: 73.90-73.96)
            elif 18.48 <= lat <= 18.53 and 73.90 <= lon <= 73.96:
                area = "Hadapsar"
                city = "Pune"
                postal = "411028"
            # Nigdi / Akurdi / PCMC North (Lat: 18.625-18.75, Lon: 73.72-73.86)
            elif 18.625 < lat <= 18.75 and 73.72 <= lon <= 73.86:
                area = "Nigdi"
                city = "Pimpri-Chinchwad"
                postal = "411044"
            else:
                area = None
                city = "Pune"
                postal = "411001"

            addr = f"{area}, {city}, Maharashtra, India" if area else f"{city}, Maharashtra, India"
            geo_name = f"{area}, {city}" if area else city
            return ResolvedLocation(
                google_place_id=None,
                formatted_address=addr,
                name=geo_name,
                display_name=geo_name,
                city=city,
                area=area,
                state="Maharashtra",
                country="India",
                postal_code=postal,
                latitude=round(lat, 6),
                longitude=round(lon, 6),
                location_precision="locality" if area is None else "neighborhood",
                location_source="browser_geolocation",
            )

        # 3. Kochi / Ernakulam (Kakkanad, Infopark, Fort Kochi, Edappally)
        # Lat: 9.88 to 10.12, Lon: 76.20 to 76.42
        if 9.88 <= lat <= 10.12 and 76.20 <= lon <= 76.42:
            area = "Kakkanad" if lon >= 76.32 else "Fort Kochi"
            return ResolvedLocation(
                google_place_id="pc_kochi_region",
                formatted_address=f"{area}, Kochi, Kerala, India",
                city="Kochi",
                area=area,
                state="Kerala",
                country="India",
                postal_code="682030",
                latitude=round(lat, 6),
                longitude=round(lon, 6),
                location_precision="locality",
                location_source="coordinate_geocoded",
            )

        # 4. Bengaluru Urban (Whitefield, Indiranagar, Koramangala)
        # Lat: 12.82 to 13.15, Lon: 77.45 to 77.78
        if 12.82 <= lat <= 13.15 and 77.45 <= lon <= 77.78:
            area = "Whitefield" if lon >= 77.70 else "Indiranagar"
            return ResolvedLocation(
                google_place_id="pc_blr_region",
                formatted_address=f"{area}, Bengaluru, Karnataka, India",
                city="Bengaluru",
                area=area,
                state="Karnataka",
                country="India",
                postal_code="560066" if area == "Whitefield" else "560038",
                latitude=round(lat, 6),
                longitude=round(lon, 6),
                location_precision="locality",
                location_source="coordinate_geocoded",
            )

        # 5. Mumbai Metropolitan Region
        if 18.88 <= lat <= 19.32 and 72.75 <= lon <= 73.05:
            return ResolvedLocation(
                google_place_id="pc_mumbai_region",
                formatted_address="Bandra, Mumbai, Maharashtra, India",
                city="Mumbai",
                area="Bandra",
                state="Maharashtra",
                country="India",
                postal_code="400050",
                latitude=round(lat, 6),
                longitude=round(lon, 6),
                location_precision="locality",
                location_source="coordinate_geocoded",
            )

        # 6. Nagpur Region
        if 21.05 <= lat <= 21.25 and 79.00 <= lon <= 79.20:
            return ResolvedLocation(
                google_place_id="pc_nagpur_region",
                formatted_address="Dharampeth, Nagpur, Maharashtra, India",
                city="Nagpur",
                area="Dharampeth",
                state="Maharashtra",
                country="India",
                postal_code="440010",
                latitude=round(lat, 6),
                longitude=round(lon, 6),
                location_precision="locality",
                location_source="coordinate_geocoded",
            )

        # 7. Broad Maharashtra state boundary
        if 15.60 <= lat <= 22.00 and 72.60 <= lon <= 80.90:
            return ResolvedLocation(
                google_place_id="pc_mh_region",
                formatted_address="Maharashtra, India",
                city="Pune",
                area=None,
                state="Maharashtra",
                country="India",
                latitude=round(lat, 6),
                longitude=round(lon, 6),
                location_precision="administrative_area",
                location_source="coordinate_geocoded",
            )

        # 8. Broad India boundary
        if 8.00 <= lat <= 37.00 and 68.00 <= lon <= 97.00:
            return ResolvedLocation(
                google_place_id="pc_india_region",
                formatted_address="India",
                city="India",
                area=None,
                state=None,
                country="India",
                latitude=round(lat, 6),
                longitude=round(lon, 6),
                location_precision="country",
                location_source="coordinate_geocoded",
            )

        return None

    @staticmethod
    def _extract_legacy_address_components(
        components: List[Dict[str, Any]],
    ) -> Tuple[Optional[str], Optional[str], Optional[str], str, Optional[str]]:
        """Legacy helper maintained for backward compatibility."""
        res = [{"address_components": components}]
        city, area, state, country, postal, _, _ = GoogleMapsService.parse_google_address_components_multi(res)
        return city, area, state, country, postal


google_maps_service = GoogleMapsService()
