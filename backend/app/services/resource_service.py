import logging
import math
import re
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
import requests
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.models.request import Request
from app.models.request_location import RequestLocation
from app.models.user import User
from app.schemas.resource import (
    NearbyHelperItem,
    NearbyHelpersResponse,
    ResourceCategoriesResponse,
    ResourceCategory,
    ResourceItem,
    ResourceSearchResponse,
    SearchCenter,
)
from app.services.google_maps_service import GoogleMapsService, google_maps_service, haversine_km

logger = logging.getLogger(__name__)

# ============================================================================
# 1. Extensible NEST Resource Category Registry (15 Functional Categories)
# ============================================================================

CATEGORIES_REGISTRY: Dict[str, Dict[str, Any]] = {
    "accommodation": {
        "id": "accommodation",
        "display_name": "Accommodation & PGs",
        "icon": "Home",
        "description": "PGs, hostels, shared flats, co-living rentals, and temporary stays",
        "default_query_terms": ["paying guest", "pg accommodation", "hostel", "co-living", "room rental"],
        "google_included_type": None,  # Text query is far more accurate for Indian PGs/hostels
        "nlp_need_categories": ["accommodation"],
    },
    "food": {
        "id": "food",
        "display_name": "Food & Tiffin",
        "icon": "Utensils",
        "description": "Tiffin services, meal delivery, mess, dabba services, and home-cooked food",
        "default_query_terms": ["tiffin service", "mess food", "dabba service", "meal delivery"],
        "google_included_type": "meal_delivery",
        "nlp_need_categories": ["food"],
    },
    "restaurants": {
        "id": "restaurants",
        "display_name": "Restaurants & Cafes",
        "icon": "Coffee",
        "description": "Local eateries, dining spots, pure-veg restaurants, and cafes",
        "default_query_terms": ["restaurant", "eatery", "cafe", "dhaba", "dining"],
        "google_included_type": "restaurant",
        "nlp_need_categories": ["food"],
    },
    "hospitals": {
        "id": "hospitals",
        "display_name": "Hospitals",
        "icon": "Hospital",
        "description": "General hospitals, emergency trauma care, and healthcare centers",
        "default_query_terms": ["hospital", "emergency hospital", "healthcare center"],
        "google_included_type": "hospital",
        "nlp_need_categories": ["healthcare"],
    },
    "clinics": {
        "id": "clinics",
        "display_name": "Clinics & Doctors",
        "icon": "Stethoscope",
        "description": "Local physician clinics, diagnostic centers, dental clinics, and dispensaries",
        "default_query_terms": ["clinic", "doctor clinic", "medical center", "diagnostic clinic"],
        "google_included_type": "medical_clinic",
        "nlp_need_categories": ["healthcare"],
    },
    "pharmacies": {
        "id": "pharmacies",
        "display_name": "Pharmacies & Chemists",
        "icon": "Pill",
        "description": "24/7 pharmacies, medical stores, and chemists",
        "default_query_terms": ["pharmacy", "chemist", "medical store", "drugstore"],
        "google_included_type": "pharmacy",
        "nlp_need_categories": ["healthcare"],
    },
    "banks": {
        "id": "banks",
        "display_name": "Banks",
        "icon": "Landmark",
        "description": "Nationalized and private bank branches and customer service centers",
        "default_query_terms": ["bank branch", "bank"],
        "google_included_type": "bank",
        "nlp_need_categories": ["documentation"],
    },
    "atms": {
        "id": "atms",
        "display_name": "ATMs",
        "icon": "Banknote",
        "description": "Cash withdrawal machines and multi-bank ATM kiosks",
        "default_query_terms": ["atm", "cash machine"],
        "google_included_type": "atm",
        "nlp_need_categories": ["documentation"],
    },
    "grocery": {
        "id": "grocery",
        "display_name": "Grocery & Supermarkets",
        "icon": "ShoppingCart",
        "description": "Supermarkets, local kirana stores, and daily essentials",
        "default_query_terms": ["supermarket", "grocery store", "kirana store"],
        "google_included_type": "supermarket",
        "nlp_need_categories": ["food"],
    },
    "public_transport": {
        "id": "public_transport",
        "display_name": "Public Transport",
        "icon": "Bus",
        "description": "Metro stations, bus stops, railway stations, and transit hubs",
        "default_query_terms": ["metro station", "bus stop", "transit station", "railway station"],
        "google_included_type": "transit_station",
        "nlp_need_categories": ["transport"],
    },
    "gyms": {
        "id": "gyms",
        "display_name": "Gyms & Fitness",
        "icon": "Dumbbell",
        "description": "Fitness centers, gymnasiums, crossfit, and yoga studios",
        "default_query_terms": ["gym", "fitness center", "workout gym"],
        "google_included_type": "gym",
        "nlp_need_categories": [],
    },
    "coworking": {
        "id": "coworking",
        "display_name": "Coworking Spaces",
        "icon": "Briefcase",
        "description": "Shared workspaces, hot desks, private cabins, and startup hubs",
        "default_query_terms": ["coworking space", "shared office", "workspace"],
        "google_included_type": None,
        "nlp_need_categories": ["jobs"],
    },
    "education": {
        "id": "education",
        "display_name": "Education & Coaching",
        "icon": "GraduationCap",
        "description": "Schools, colleges, coaching institutes, and libraries",
        "default_query_terms": ["coaching institute", "college", "school", "library"],
        "google_included_type": "school",
        "nlp_need_categories": ["education"],
    },
    "government_services": {
        "id": "government_services",
        "display_name": "Govt & Civic Services",
        "icon": "Building",
        "description": "Post offices, Aadhaar seva kendras, ward offices, and police stations",
        "default_query_terms": ["post office", "police station", "aadhaar center", "seva kendra"],
        "google_included_type": "local_government_office",
        "nlp_need_categories": ["documentation"],
    },
    "repairs": {
        "id": "repairs",
        "display_name": "Repairs & Utilities",
        "icon": "Wrench",
        "description": "Appliance repairs, electricians, plumbers, vehicle repair centers",
        "default_query_terms": ["appliance repair", "electrician", "plumber", "vehicle repair"],
        "google_included_type": None,
        "nlp_need_categories": ["local guidance"],
    },
}


def get_all_categories() -> ResourceCategoriesResponse:
    """Return all configured NEST resource categories."""
    cats = [
        ResourceCategory(
            id=c["id"],
            display_name=c["display_name"],
            icon=c["icon"],
            description=c["description"],
            default_query_terms=c["default_query_terms"],
        )
        for c in CATEGORIES_REGISTRY.values()
    ]
    return ResourceCategoriesResponse(total=len(cats), categories=cats)


def resolve_category_from_need(need_category: str) -> Optional[str]:
    """Map Phase 3 NLP need category to NEST resource category."""
    clean = need_category.strip().lower()
    for cat_id, meta in CATEGORIES_REGISTRY.items():
        if clean in meta["nlp_need_categories"]:
            return cat_id
    return None


# ============================================================================
# 2. Transparent Ranking Algorithm
# ============================================================================

def rank_and_explain_resources(
    resources: List[Dict[str, Any]],
    search_lat: float,
    search_lon: float,
    radius_meters: float,
    category_id: str,
    preferences: List[str],
) -> List[ResourceItem]:
    """
    Apply a transparent, deterministic ranking formula to raw Google Places results.
    
    Formula components:
    - Distance Factor (45%): max(0, 1 - distance / radius_km).
    - Preference/Keyword Relevance (35%): Matches keywords from preferences against name/types.
    - Quality Rating (15%): (rating - 1.0) / 4.0 if present; neutral 0.5 if unrated (never penalized).
    - Review Volume Confidence (5%): min(1.0, log10(review_count + 1) / 2.0); strictly non-dominant.
    
    Returns normalized ResourceItems with strict nulls for missing provider data.
    """
    category_meta = CATEGORIES_REGISTRY.get(category_id, {})
    category_name = category_meta.get("display_name", category_id.title())
    radius_km = radius_meters / 1000.0

    scored_items: List[Tuple[float, ResourceItem]] = []

    for p in resources:
        place_id = p.get("id") or p.get("google_place_id", str(uuid.uuid4()))
        display_info = p.get("displayName", {})
        name = display_info.get("text") if isinstance(display_info, dict) else str(display_info or "Local Place")
        formatted_address = p.get("formattedAddress")

        loc = p.get("location", {})
        lat = loc.get("latitude") if isinstance(loc, dict) else None
        lon = loc.get("longitude") if isinstance(loc, dict) else None

        # Distance calculation
        dist_km: Optional[float] = None
        if lat is not None and lon is not None:
            dist_km = round(haversine_km(search_lat, search_lon, lat, lon), 2)

        # Rating and review count: MUST remain None if unavailable (no fake defaults)
        rating_raw = p.get("rating")
        rating: Optional[float] = round(float(rating_raw), 1) if rating_raw is not None else None

        reviews_raw = p.get("userRatingCount")
        review_count: Optional[int] = int(reviews_raw) if reviews_raw is not None else None

        price_level_raw = p.get("priceLevel")
        price_level: Optional[str] = str(price_level_raw).replace("PRICE_LEVEL_", "") if price_level_raw else None

        opening_hours = p.get("regularOpeningHours", {})
        is_open_now: Optional[bool] = opening_hours.get("openNow") if isinstance(opening_hours, dict) else None

        maps_url = p.get("googleMapsUri")
        website_url = p.get("websiteUri")
        phone_number = p.get("nationalPhoneNumber")
        primary_type = p.get("primaryType")

        # ----------------------------------------------------
        # Scoring & Explanations
        # ----------------------------------------------------
        reasons: List[str] = []

        # 1. Distance score (45%)
        if dist_km is not None:
            dist_score = max(0.0, 1.0 - (dist_km / max(radius_km, 1.0)))
            reasons.append(f"{dist_km} km away from target area")
        else:
            dist_score = 0.5

        # 2. Preference & keyword relevance score (35%)
        matched_prefs: List[str] = []
        name_lower = (name or "").lower()
        addr_lower = (formatted_address or "").lower()
        types = [t.lower() for t in p.get("types", [])]

        for pref in preferences:
            clean_pref = pref.strip().lower()
            if not clean_pref:
                continue
            if clean_pref in name_lower or clean_pref in addr_lower or any(clean_pref in t for t in types):
                matched_prefs.append(pref)

        if preferences:
            rel_score = 0.5 + 0.5 * (len(matched_prefs) / len(preferences))
            if matched_prefs:
                reasons.append(f"Matches preference: '{', '.join(matched_prefs)}'")
        else:
            rel_score = 0.75

        # 3. Rating quality score (15%)
        if rating is not None:
            rating_score = max(0.0, min(1.0, (rating - 1.0) / 4.0))
            reasons.append(f"Rated {rating}/5.0 by users")
        else:
            rating_score = 0.5  # Neutral baseline for unrated places

        # 4. Review volume confidence factor (5%) - strictly non-dominant
        if review_count is not None and review_count > 0:
            conf_score = min(1.0, math.log10(review_count + 1) / 2.0)
            if review_count >= 10:
                reasons.append(f"Established local presence ({review_count} reviews)")
        else:
            conf_score = 0.2

        final_score = round(
            (0.45 * dist_score) + (0.35 * rel_score) + (0.15 * rating_score) + (0.05 * conf_score),
            3,
        )

        item = ResourceItem(
            id=str(place_id),
            name=name,
            category=category_id,
            category_display_name=category_name,
            formatted_address=formatted_address,
            latitude=lat,
            longitude=lon,
            distance_km=dist_km,
            rating=rating,
            review_count=review_count,
            price_level=price_level,
            is_open_now=is_open_now,
            google_place_id=str(place_id),
            maps_url=maps_url,
            website_url=website_url,
            phone_number=phone_number,
            primary_type=primary_type,
            ranking_score=final_score,
            ranking_reasons=reasons,
        )
        scored_items.append((final_score, item))

    # Sort descending by final score
    scored_items.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored_items]


# ============================================================================
# 3. Provider Abstraction (Google Places & OpenStreetMap Zero-Billing)
# ============================================================================

OSM_CATEGORY_SEARCH_TERMS: Dict[str, str] = {
    "accommodation": "hostel",
    "food": "restaurant",
    "restaurants": "restaurant",
    "hospitals": "hospital",
    "clinics": "clinic",
    "pharmacies": "pharmacy",
    "banks": "bank",
    "atms": "atm",
    "grocery": "supermarket",
    "public_transport": "station",
    "gyms": "gym",
    "coworking": "coworking",
    "education": "college",
    "government_services": "police station",
    "repairs": "repair",
}


class OpenStreetMapResourceProvider:
    """
    Zero-billing, 100% real OpenStreetMap provider for local resource discovery.
    Uses public Nominatim endpoints with:
    - Custom User-Agent header (required by OSM policy)
    - 24-hour in-memory TTL caching
    - Strict preservation of real data (no fabricated reviews, ratings, or businesses)
    - Viewbox bounding box support for map viewport panning
    """
    def __init__(self):
        self._cache: Dict[str, Tuple[datetime, List[ResourceItem]]] = {}
        self._cache_ttl = timedelta(hours=24)
        self.endpoint = "https://nominatim.openstreetmap.org/search"
        self.user_agent = "NEST-LocalDiscovery/1.0 (contact: support@nest-app.local)"

    def _get_cache(self, key: str) -> Optional[List[ResourceItem]]:
        if key in self._cache:
            exp, data = self._cache[key]
            if datetime.now(timezone.utc) < exp:
                return data
            del self._cache[key]
        return None

    def _set_cache(self, key: str, data: List[ResourceItem]):
        self._cache[key] = (datetime.now(timezone.utc) + self._cache_ttl, data)

    def search(
        self,
        category: str,
        query: Optional[str],
        latitude: float,
        longitude: float,
        radius_meters: float,
        locality_label: Optional[str] = None,
        min_lat: Optional[float] = None,
        max_lat: Optional[float] = None,
        min_lon: Optional[float] = None,
        max_lon: Optional[float] = None,
        limit: int = 15,
    ) -> List[ResourceItem]:
        category_meta = CATEGORIES_REGISTRY.get(category, CATEGORIES_REGISTRY["accommodation"])
        default_osm_term = OSM_CATEGORY_SEARCH_TERMS.get(category, category_meta["default_query_terms"][0])
        terms = query.strip() if query and query.strip() else default_osm_term

        has_viewbox = (
            min_lat is not None and max_lat is not None and
            min_lon is not None and max_lon is not None
        )

        coord_str = f"{round(latitude, 3)},{round(longitude, 3)}"
        viewbox_str = f"{min_lon},{max_lat},{max_lon},{min_lat}" if has_viewbox else "none"
        cache_key = f"osm:{category}:{terms}:{coord_str}:{viewbox_str}:{limit}"
        cached = self._get_cache(cache_key)
        if cached is not None:
            return cached

        params: Dict[str, Any] = {
            "format": "json",
            "addressdetails": 1,
            "limit": max(limit, 10),
            "countrycodes": "in",
        }

        if has_viewbox:
            # viewbox=left,top,right,bottom -> min_lon,max_lat,max_lon,min_lat
            params["viewbox"] = f"{min_lon},{max_lat},{max_lon},{min_lat}"
            params["bounded"] = 1
            params["q"] = terms
        else:
            if locality_label:
                params["q"] = f"{terms} in {locality_label}"
            else:
                deg = radius_meters / 111320.0
                params["viewbox"] = f"{longitude - deg},{latitude + deg},{longitude + deg},{latitude - deg}"
                params["bounded"] = 0
                params["q"] = terms

        headers = {"User-Agent": self.user_agent}

        try:
            resp = requests.get(self.endpoint, params=params, headers=headers, timeout=6.0)
            if resp.status_code != 200:
                logger.warning("Nominatim search returned %d", resp.status_code)
                return []
            raw_places = resp.json()
            if not isinstance(raw_places, list):
                return []

            items: List[ResourceItem] = []
            for p in raw_places:
                try:
                    p_lat = float(p.get("lat"))
                    p_lon = float(p.get("lon"))
                except (ValueError, TypeError):
                    continue

                dist_km = round(haversine_km(latitude, longitude, p_lat, p_lon), 2)
                addr_dict = p.get("address", {})
                name = (
                    p.get("name")
                    or addr_dict.get("amenity")
                    or addr_dict.get("tourism")
                    or addr_dict.get("shop")
                    or (p.get("display_name", "").split(",")[0] if p.get("display_name") else "Local Facility")
                )

                osm_type = p.get("osm_type", "node")
                osm_id = str(p.get("osm_id", p.get("place_id", uuid.uuid4().hex[:8])))
                canonical_id = f"osm_{osm_type}_{osm_id}"

                score = round(max(0.1, min(1.0, 1.0 - (dist_km / max(radius_meters / 1000.0, 1.0)) * 0.5)), 2)

                reasons = [
                    f"Nearby ({dist_km} km)",
                    f"Category match: {category_meta['display_name']}",
                    "OpenStreetMap community verified place",
                ]

                item = ResourceItem(
                    id=canonical_id,
                    name=name,
                    category=category,
                    category_display_name=category_meta["display_name"],
                    formatted_address=p.get("display_name"),
                    latitude=p_lat,
                    longitude=p_lon,
                    distance_km=dist_km,
                    rating=None,
                    review_count=None,
                    price_level=None,
                    is_open_now=None,
                    google_place_id=canonical_id,
                    maps_url=f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
                    website_url=None,
                    phone_number=None,
                    primary_type=p.get("type"),
                    ranking_score=score,
                    ranking_reasons=reasons,
                )
                items.append(item)

            items.sort(key=lambda x: x.ranking_score, reverse=True)
            trimmed = items[:limit]
            self._set_cache(cache_key, trimmed)
            return trimmed

        except Exception as exc:
            logger.warning("Nominatim POI search failed gracefully: %s", exc)
            return []


_osm_resource_provider = OpenStreetMapResourceProvider()


# ============================================================================
# 4. Resource Discovery Orchestrator
# ============================================================================

def search_local_resources(
    db: Session,
    current_user: User,
    request_id: Optional[uuid.UUID] = None,
    category: Optional[str] = None,
    query: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius_meters: int = 5000,
    min_lat: Optional[float] = None,
    max_lat: Optional[float] = None,
    min_lon: Optional[float] = None,
    max_lon: Optional[float] = None,
    provider: Optional[str] = None,
    limit: int = 10,
    maps_service: GoogleMapsService = google_maps_service,
) -> ResourceSearchResponse:
    """
    Search and rank real local resources using Google Places API (New) or OpenStreetMap.
    
    Privacy guarantees:
    - Never uses or returns user's private home location.
    - Strictly uses request target location or explicit manual search coordinates.
    - Public place coordinates are returned for map display; user coordinates are never exposed.
    """
    # 1. Resolve search origin coordinates and context
    search_lat: Optional[float] = latitude
    search_lon: Optional[float] = longitude
    locality_label: Optional[str] = None
    preferences: List[str] = []
    effective_category: str = "accommodation"

    if request_id:
        req = db.query(Request).filter(Request.id == request_id).first()
        if not req:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Request not found.",
            )
        if req.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access resources for this request.",
            )

        # Retrieve request target location (isolated from user home location)
        req_loc = db.query(RequestLocation).filter(RequestLocation.request_id == request_id).first()
        if req_loc:
            search_lat = req_loc.latitude
            search_lon = req_loc.longitude
            parts = []
            for part in [req_loc.display_name, req_loc.area, req_loc.city]:
                if part and part.strip() and part.strip() not in parts:
                    parts.append(part.strip())
            locality_label = ", ".join(parts) if parts else None

        if not locality_label:
            locality_label = ", ".join(filter(None, [req.area, req.city]))

        # Geocode if coordinates were not resolved previously
        if (search_lat is None or search_lon is None) and locality_label:
            resolved_geo = maps_service.geocode_address(locality_label)
            if resolved_geo and resolved_geo.latitude and resolved_geo.longitude:
                search_lat = resolved_geo.latitude
                search_lon = resolved_geo.longitude

        # Extract preferences
        preferences = req.preferences or []

        # Infer category from request needs if not explicitly passed
        if not category and req.extracted_requirements:
            needs = req.extracted_requirements.get("needs", [])
            for need in needs:
                cat_slug = resolve_category_from_need(need.get("category", ""))
                if cat_slug:
                    effective_category = cat_slug
                    break

    if category:
        clean_cat = category.strip().lower()
        if clean_cat in CATEGORIES_REGISTRY:
            effective_category = clean_cat

    category_meta = CATEGORIES_REGISTRY.get(effective_category, CATEGORIES_REGISTRY["accommodation"])

    # Fallback coordinates if none resolved: Pune center baseline
    if search_lat is None or search_lon is None:
        search_lat = 18.5204
        search_lon = 73.8567
        locality_label = locality_label or "Pune, Maharashtra"
    elif not locality_label:
        rev = maps_service.reverse_geocode(search_lat, search_lon)
        if rev:
            parts = [p for p in [rev.road, rev.area, rev.city] if p]
            locality_label = ", ".join(dict.fromkeys(parts)) or rev.formatted_address or "Pune, Maharashtra"


    # 2. Build text query
    query_terms: List[str] = []
    if query and query.strip():
        query_terms.append(query.strip())
    else:
        default_kw = category_meta["default_query_terms"][0]
        query_terms.append(default_kw)

    if locality_label:
        query_terms.append(f"in {locality_label}")

    effective_query = " ".join(query_terms)

    # 3. Provider selection logic
    use_osm = False
    if provider in ("osm", "openstreetmap"):
        use_osm = True
    else:
        # Production Google Places requirement (provider="google", "auto", or None)
        if not maps_service.is_configured:
            logger.info("Google Maps Platform is not configured; returning PROVIDER_UNAVAILABLE.")
            return ResourceSearchResponse(
                status="PROVIDER_UNAVAILABLE",
                total=0,
                resources=[],
                search_center=SearchCenter(
                    latitude=search_lat,
                    longitude=search_lon,
                    label=locality_label,
                ),
                category=effective_category,
                query=effective_query,
                radius_meters=radius_meters,
                provider="google_places",
            )

    # 4A. Execute OpenStreetMap (Nominatim) search when requested or in auto zero-billing mode
    if use_osm:
        osm_items = _osm_resource_provider.search(
            category=effective_category,
            query=query,
            latitude=search_lat,
            longitude=search_lon,
            radius_meters=float(radius_meters),
            locality_label=locality_label,
            min_lat=min_lat,
            max_lat=max_lat,
            min_lon=min_lon,
            max_lon=max_lon,
            limit=limit,
        )
        return ResourceSearchResponse(
            status="SUCCESS" if osm_items else "NO_RESULTS",
            total=len(osm_items),
            resources=osm_items,
            search_center=SearchCenter(
                latitude=search_lat,
                longitude=search_lon,
                label=locality_label,
            ),
            category=effective_category,
            query=effective_query,
            radius_meters=radius_meters,
            provider="openstreetmap",
        )

    # 4B. Execute Google Places API (New) search
    raw_places = maps_service.search_places_text(
        text_query=effective_query,
        latitude=search_lat,
        longitude=search_lon,
        radius_meters=float(radius_meters),
        included_type=category_meta.get("google_included_type"),
        max_result_count=max(limit, 10),
    )

    # Adaptive radius expansion: If fewer than 3 results and radius <= 5000, try 10000m
    effective_radius = radius_meters
    if len(raw_places) < 3 and radius_meters <= 5000:
        expanded_radius = 10000.0
        expanded_places = maps_service.search_places_text(
            text_query=effective_query,
            latitude=search_lat,
            longitude=search_lon,
            radius_meters=expanded_radius,
            included_type=category_meta.get("google_included_type"),
            max_result_count=max(limit, 10),
        )
        if len(expanded_places) > len(raw_places):
            raw_places = expanded_places
            effective_radius = int(expanded_radius)

    if not raw_places:
        return ResourceSearchResponse(
            status="NO_RESULTS",
            total=0,
            resources=[],
            search_center=SearchCenter(
                latitude=search_lat,
                longitude=search_lon,
                label=locality_label,
            ),
            category=effective_category,
            query=effective_query,
            radius_meters=effective_radius,
            provider="google_places",
        )

    # 5. Rank and normalize results
    ranked_resources = rank_and_explain_resources(
        resources=raw_places,
        search_lat=search_lat,
        search_lon=search_lon,
        radius_meters=float(effective_radius),
        category_id=effective_category,
        preferences=preferences,
    )

    trimmed_resources = ranked_resources[:limit]

    return ResourceSearchResponse(
        status="SUCCESS",
        total=len(trimmed_resources),
        resources=trimmed_resources,
        search_center=SearchCenter(
            latitude=search_lat,
            longitude=search_lon,
            label=locality_label,
        ),
        category=effective_category,
        query=effective_query,
        radius_meters=effective_radius,
        provider="google_places",
    )


# ============================================================================
# 5. Real Community Helpers Query (Zero Fabrication)
# ============================================================================

def get_nearby_helpers(
    db: Session,
    current_user: User,
    latitude: float,
    longitude: float,
    radius_km: float = 15.0,
    request_id: Optional[uuid.UUID] = None,
) -> NearbyHelpersResponse:
    """
    Query real, verified, active NEST community helpers near specified coordinates.
    Strict Real-Data & Privacy Rules:
    - Never fabricates fake helpers, initials, ratings, reviews, or coordinates.
    - If zero eligible helpers in database, returns empty list ([]).
    - Excludes requesting user and blocked/suspended users.
    - Requires email_verified=True, is_active=True, role in ('helper', 'both').
    - Privacy protection: returns approximate coordinates (rounded to 2 decimal places),
      never raw private home or street coordinates.
    """
    from app.models.location import Location
    from app.models.profile import Profile
    from app.models.skill import Skill, UserSkill
    from app.models.user import UserRole
    from app.services.safety_service import get_blocked_user_ids
    from app.services.review_service import get_user_reputation

    blocked_user_ids = get_blocked_user_ids(db, current_user.id)

    # Eligible helpers: active, email_verified, role in ('helper', 'both'), not self, not blocked
    helper_query = (
        db.query(User, Location, Profile)
        .join(Location, Location.user_id == User.id)
        .outerjoin(Profile, Profile.user_id == User.id)
        .filter(
            User.id != current_user.id,
            User.is_active == True,
            User.email_verified == True,
            User.role.in_([UserRole.HELPER, UserRole.BOTH]),
            Location.location_label == "Primary",
            Location.latitude.isnot(None),
            Location.longitude.isnot(None),
        )
    )
    if blocked_user_ids:
        helper_query = helper_query.filter(~User.id.in_(list(blocked_user_ids)))

    candidate_rows = helper_query.all()
    nearby_items: List[NearbyHelperItem] = []

    for user, loc, prof in candidate_rows:
        dist_km = haversine_km(latitude, longitude, loc.latitude, loc.longitude)
        if dist_km <= radius_km:
            # Verified skills
            skills = (
                db.query(Skill.name)
                .join(UserSkill, UserSkill.skill_id == Skill.id)
                .filter(UserSkill.user_id == user.id)
                .all()
            )
            skills_list = [s[0] for s in skills]

            # Reputation
            rep = get_user_reputation(db, user.id)

            # Display name without private contact details
            display_name = user.name or user.email.split("@")[0].capitalize()

            # Privacy: round coordinates to 2 decimals (~1.1km area)
            approx_lat = round(loc.latitude, 2)
            approx_lon = round(loc.longitude, 2)

            nearby_items.append(
                NearbyHelperItem(
                    user_id=str(user.id),
                    name=display_name,
                    headline=prof.headline if prof else None,
                    bio=prof.bio if prof else None,
                    city=loc.city,
                    area=loc.area,
                    approximate_latitude=approx_lat,
                    approximate_longitude=approx_lon,
                    distance_km=round(dist_km, 1),
                    skills=skills_list,
                    reputation_rating=round(rep.average_rating, 1) if rep.average_rating is not None else None,
                    reputation_reviews=rep.review_count,
                    is_available_for_help=True,
                )
            )

    # Sort ascending by distance
    nearby_items.sort(key=lambda x: (x.distance_km if x.distance_km is not None else 999.0))

    return NearbyHelpersResponse(
        total=len(nearby_items),
        helpers=nearby_items,
        center_latitude=latitude,
        center_longitude=longitude,
        radius_km=radius_km,
    )

