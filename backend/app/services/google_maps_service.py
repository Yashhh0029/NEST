import logging
import math
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
        self.api_key = api_key if api_key is not None else settings.GOOGLE_MAPS_API_KEY
        # In-memory TTL cache: key -> (expiration_datetime, data)
        self._cache: Dict[str, Tuple[datetime, Any]] = {}
        self._cache_ttl = timedelta(hours=24)

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
        self, input_text: str, session_token: Optional[str] = None
    ) -> List[PlaceAutocompletePrediction]:
        """
        Query Google Places API (New) autocomplete, biased and restricted to India.
        """
        clean_input = input_text.strip()
        if not clean_input or not self.is_configured:
            return []

        cache_key = f"autocomplete:{clean_input.lower()}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

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
        if not clean_place_id or not self.is_configured:
            return None

        cache_key = f"place_details:{clean_place_id}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        url = f"https://places.googleapis.com/v1/places/{clean_place_id}"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "id,displayName,formattedAddress,location,addressComponents",
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

            city, area, state, country, postal = self._extract_address_components(data.get("addressComponents", []))

            resolved = ResolvedLocation(
                google_place_id=clean_place_id,
                formatted_address=formatted,
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
            logger.warning("Google Place details lookup failed gracefully: %s", exc)
            return None

    def geocode_address(self, address: str) -> Optional[ResolvedLocation]:
        """
        Forward geocode an address string in India using Google Geocoding API.
        """
        clean_address = address.strip()
        if not clean_address or not self.is_configured:
            return None

        cache_key = f"geocode:{clean_address.lower()}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": clean_address,
            "components": "country:IN",
            "key": self.api_key,
        }

        try:
            resp = requests.get(url, params=params, timeout=5.0)
            if resp.status_code != 200:
                logger.warning("Google Geocoding returned status %d", resp.status_code)
                return None

            data = resp.json()
            results = data.get("results", [])
            if not results:
                return None

            top = results[0]
            place_id = top.get("place_id")
            formatted = top.get("formatted_address")
            geometry = top.get("geometry", {})
            loc = geometry.get("location", {})
            lat = loc.get("lat")
            lng = loc.get("lng")
            precision = geometry.get("location_type", "approximate").lower()

            city, area, state, country, postal = self._extract_legacy_address_components(top.get("address_components", []))

            resolved = ResolvedLocation(
                google_place_id=place_id,
                formatted_address=formatted,
                city=city,
                area=area,
                state=state,
                country=country or "India",
                postal_code=postal,
                latitude=round(lat, 6) if lat is not None else None,
                longitude=round(lng, 6) if lng is not None else None,
                location_precision=precision,
                location_source="google_geocoding",
            )
            self._set_in_cache(cache_key, resolved)
            return resolved

        except Exception as exc:
            logger.warning("Google Geocoding failed gracefully: %s", exc)
            return None

    def reverse_geocode(self, latitude: float, longitude: float) -> Optional[ResolvedLocation]:
        """
        Reverse geocode GPS coordinates to city/area using Google Geocoding API.
        """
        if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
            return None
        if not self.is_configured:
            return None

        cache_key = f"rev_geocode:{round(latitude, 3)},{round(longitude, 3)}"
        cached = self._get_from_cache(cache_key)
        if cached is not None:
            return cached

        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "latlng": f"{latitude},{longitude}",
            "key": self.api_key,
        }

        try:
            resp = requests.get(url, params=params, timeout=5.0)
            if resp.status_code != 200:
                logger.warning("Google Reverse Geocoding returned status %d", resp.status_code)
                return None

            data = resp.json()
            results = data.get("results", [])
            if not results:
                return None

            top = results[0]
            place_id = top.get("place_id")
            formatted = top.get("formatted_address")
            city, area, state, country, postal = self._extract_legacy_address_components(top.get("address_components", []))

            resolved = ResolvedLocation(
                google_place_id=place_id,
                formatted_address=formatted,
                city=city,
                area=area,
                state=state,
                country=country or "India",
                postal_code=postal,
                latitude=round(latitude, 6),
                longitude=round(longitude, 6),
                location_precision="rooftop",
                location_source="google_reverse_geocoding",
            )
            self._set_in_cache(cache_key, resolved)
            return resolved

        except Exception as exc:
            logger.warning("Google Reverse Geocoding failed gracefully: %s", exc)
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

        if not self.is_configured:
            return TravelRouteInfo(
                straight_line_distance_km=straight_km,
                route_distance_km=None,
                estimated_travel_time_minutes=None,
                travel_mode=travel_mode,
            )

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
        except Exception as exc:
            logger.warning("Google Routes API call failed gracefully: %s", exc)

        fallback = TravelRouteInfo(
            straight_line_distance_km=straight_km,
            route_distance_km=None,
            estimated_travel_time_minutes=None,
            travel_mode=travel_mode,
        )
        return fallback

    def search_places_text(
        self,
        text_query: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_meters: float = 5000.0,
        included_type: Optional[str] = None,
        open_now: Optional[bool] = None,
        max_result_count: int = 10,
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
        if latitude is not None and longitude is not None:
            payload["locationBias"] = {
                "circle": {
                    "center": {
                        "latitude": latitude,
                        "longitude": longitude,
                    },
                    "radius": float(radius_meters),
                }
            }
        if included_type:
            payload["includedType"] = included_type
        if open_now is True:
            payload["openNow"] = True

        try:
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
    def _extract_legacy_address_components(
        components: List[Dict[str, Any]],
    ) -> Tuple[Optional[str], Optional[str], Optional[str], str, Optional[str]]:
        """Extract city, area, state, country, postal from Geocoding API address_components."""
        city = None
        area = None
        state = None
        country = "India"
        postal = None

        for comp in components:
            types = comp.get("types", [])
            long_name = comp.get("long_name")
            if not long_name:
                continue

            if "sublocality_level_1" in types or "sublocality" in types or "neighborhood" in types:
                if not area:
                    area = long_name
            elif "locality" in types:
                city = long_name
            elif "administrative_area_level_2" in types and not city:
                city = long_name
            elif "administrative_area_level_1" in types:
                state = long_name
            elif "country" in types:
                country = long_name
            elif "postal_code" in types:
                postal = long_name

        return city, area, state, country, postal


google_maps_service = GoogleMapsService()
