import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useSearchParams, Link } from "react-router-dom";
import {
  Search,
  MapPin,
  List,
  Map as MapIcon,
  Compass,
  AlertCircle,
  Home,
  Utensils,
  Coffee,
  Hospital,
  Stethoscope,
  Pill,
  Landmark,
  Banknote,
  ShoppingCart,
  Bus,
  Dumbbell,
  Briefcase,
  GraduationCap,
  Building,
  Wrench,
  Sparkles,
  Crosshair,
  RefreshCw,
  KeyRound,
  X,
  ExternalLink,
  Layers,
  Users,
} from "lucide-react";
import { ResourceCard } from "@/components/resource/ResourceCard";
import { GoogleMap, type MapCandidate, type ViewportBounds } from "@/components/location/GoogleMap";
import { PlaceAutocomplete } from "@/components/location/PlaceAutocomplete";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/hooks/useToast";
import { getNearbyHelpers, getResourceCategories, searchResources } from "@/services/resources";
import {
  getPlaceDetails,
  resolveAddressText,
  getRequestTargetLocation,
} from "@/services/location";
import type { PlaceAutocompletePrediction } from "@/types/google-location";
import type {
  NearbyHelperItem,
  ResourceCategory,
  ResourceSearchResponse,
} from "@/types/resource";


const CATEGORY_ICON_MAP: Record<string, React.FC<{ className?: string }>> = {
  Home,
  Utensils,
  Coffee,
  Hospital,
  Stethoscope,
  Pill,
  Landmark,
  Banknote,
  ShoppingCart,
  Bus,
  Dumbbell,
  Briefcase,
  GraduationCap,
  Building,
  Wrench,
};

export const ResourcesPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestIdParam = searchParams.get("request_id") || undefined;
  const initialCategoryParam = searchParams.get("category") || "";

  const { error: toastError, success: toastSuccess } = useToast();

  const [categories, setCategories] = useState<ResourceCategory[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>(initialCategoryParam);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [viewMode, setViewMode] = useState<"list" | "map">("list");
  const [searchResult, setSearchResult] = useState<ResourceSearchResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [selectedResourceId, setSelectedResourceId] = useState<string | null>(null);

  // Provider mode: Google Maps Platform & Google Places API (New)
  const providerMode: "google" | "osm" = "google";

  // Selected place or society identity (preserves society name vs generic area)
  const [selectedPlace, setSelectedPlace] = useState<{
    id: string;
    name: string;
    formattedAddress?: string | null;
    latitude: number;
    longitude: number;
  } | null>(null);
  const [isCurrentLocation, setIsCurrentLocation] = useState<boolean>(false);

  // Location exploration state
  const [exploreCenter, setExploreCenter] = useState<{
    latitude: number;
    longitude: number;
    label?: string;
  } | null>(null);
  const [exploreRadius, setExploreRadius] = useState<number>(1000);
  const [exploreLocationLabel, setExploreLocationLabel] = useState<string>("");
  const [viewportBounds, setViewportBounds] = useState<ViewportBounds | null>(null);
  const [isChangingLocation, setIsChangingLocation] = useState<boolean>(false);
  const [isLocatingUser, setIsLocatingUser] = useState<boolean>(false);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState<boolean>(false);
  const [nearbyHelpers, setNearbyHelpers] = useState<NearbyHelperItem[]>([]);
  const [isLoadingHelpers, setIsLoadingHelpers] = useState<boolean>(false);

  // Fetch real eligible NEST community helpers near the active exploration center
  useEffect(() => {
    if (exploreCenter?.latitude != null && exploreCenter?.longitude != null) {
      setIsLoadingHelpers(true);
      getNearbyHelpers({
        latitude: exploreCenter.latitude,
        longitude: exploreCenter.longitude,
        radius_km: 15.0,
        request_id: requestIdParam || undefined,
      })
        .then((res) => {
          setNearbyHelpers(res.helpers || []);
        })
        .catch(() => {
          setNearbyHelpers([]);
        })
        .finally(() => {
          setIsLoadingHelpers(false);
        });
    } else {
      setNearbyHelpers([]);
    }
  }, [exploreCenter?.latitude, exploreCenter?.longitude, requestIdParam]);


  // Load category metadata on mount
  useEffect(() => {
    getResourceCategories()
      .then((data) => setCategories(data.categories || []))
      .catch(() => {
        // Fallback or silent fail
      });
  }, []);

  // When request_id is provided, resolve the request's target location first
  // Priority: REQUEST TARGET LOCATION > explicitly selected exploration area > saved profile location > browser current location
  useEffect(() => {
    if (requestIdParam) {
      getRequestTargetLocation(requestIdParam)
        .then((res) => {
          if (
            res.latitude != null &&
            res.longitude != null
          ) {
            const label =
              res.display_name ||
              res.formatted_address ||
              [res.area, res.city].filter(Boolean).join(", ") ||
              "Request Target Location";
            setExploreCenter({
              latitude: res.latitude,
              longitude: res.longitude,
              label,
            });
            setExploreLocationLabel(label);
            if (res.display_name) {
              setSelectedPlace({
                id: res.google_place_id || "request_target",
                name: res.display_name,
                formattedAddress: res.formatted_address,
                latitude: res.latitude,
                longitude: res.longitude,
              });
            }
          }
        })
        .catch(() => {
          // If request location endpoint fails, backend search will handle fallback
        });
    }
  }, [requestIdParam]);

  // Fetch resources
  const fetchResources = useCallback(async () => {
    setIsLoading(true);
    try {
      const params: {
        request_id?: string;
        category?: string;
        query?: string;
        latitude?: number;
        longitude?: number;
        radius_meters?: number;
        min_lat?: number;
        max_lat?: number;
        min_lon?: number;
        max_lon?: number;
        provider?: string;
        limit?: number;
      } = {
        category: selectedCategory || undefined,
        query: searchQuery.trim() || undefined,
        provider: providerMode,
        limit: 50,
      };

      if (exploreCenter?.latitude != null && exploreCenter?.longitude != null) {
        params.latitude = exploreCenter.latitude;
        params.longitude = exploreCenter.longitude;
        params.radius_meters = exploreRadius;
      } else if (requestIdParam) {
        params.request_id = requestIdParam;
      }

      if (viewportBounds) {
        params.min_lat = viewportBounds.minLat;
        params.max_lat = viewportBounds.maxLat;
        params.min_lon = viewportBounds.minLon;
        params.max_lon = viewportBounds.maxLon;
      }

      const resp = await searchResources(params);
      setSearchResult(resp);
      if (resp.search_center?.label && !exploreLocationLabel) {
        setExploreLocationLabel(resp.search_center.label);
      }
    } catch {
      toastError("Failed to fetch local resources. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, [
    requestIdParam,
    selectedCategory,
    searchQuery,
    exploreCenter,
    exploreRadius,
    viewportBounds,
    providerMode,
    exploreLocationLabel,
    toastError,
  ]);

  useEffect(() => {
    fetchResources();
  }, [fetchResources]);

  // Sync category state with query params
  const handleCategoryClick = (catId: string) => {
    const nextCat = selectedCategory === catId ? "" : catId;
    setSelectedCategory(nextCat);
    const newParams = new URLSearchParams(searchParams);
    if (nextCat) {
      newParams.set("category", nextCat);
    } else {
      newParams.delete("category");
    }
    setSearchParams(newParams);
  };

  // Map real verified eligible helpers to MapCandidates for the map layer (ZERO fake markers)
  const helperMapCandidates: MapCandidate[] = useMemo(() => {
    return nearbyHelpers
      .filter((h) => h.approximate_latitude != null && h.approximate_longitude != null)
      .map((h) => ({
        id: h.user_id,
        name: h.name,
        approximateLatitude: h.approximate_latitude,
        approximateLongitude: h.approximate_longitude,
        area: h.area,
        city: h.city,
        distanceKm: h.distance_km,
        score: h.reputation_rating,
        headline: h.headline,
        skills: h.skills,
        isHelper: true,
      }));
  }, [nearbyHelpers]);

  const selectedResource = useMemo(() => {
    if (!selectedResourceId || !searchResult?.resources) return null;
    return searchResult.resources.find((r) => r.id === selectedResourceId) || null;
  }, [selectedResourceId, searchResult?.resources]);

  // Handle selecting location from autocomplete dropdown
  const handleSelectExplorePrediction = async (
    prediction: PlaceAutocompletePrediction
  ) => {
    setIsChangingLocation(false);
    setViewportBounds(null);
    setIsCurrentLocation(false);

    try {
      const details = await getPlaceDetails(prediction.place_id);
      if (details.latitude != null && details.longitude != null) {
        const placeName = details.name || prediction.main_text || "";
        const localityParts = [details.area, details.city].filter(Boolean);
        let label = placeName;
        if (localityParts.length > 0) {
          const localityStr = localityParts.join(", ");
          if (!label.toLowerCase().includes(localityStr.toLowerCase())) {
            label = `${label}, ${localityStr}`;
          }
        }
        if (!label) {
          label = details.formatted_address || prediction.description;
        }

        setSelectedPlace({
          id: details.google_place_id || prediction.place_id,
          name: placeName || label,
          formattedAddress: details.formatted_address || prediction.description,
          latitude: details.latitude,
          longitude: details.longitude,
        });

        setExploreCenter({
          latitude: details.latitude,
          longitude: details.longitude,
          label,
        });
        setExploreLocationLabel(label);
        toastSuccess(`Exploring places near ${label}`);
        return;
      }
    } catch {
      // Fallback to text resolve
    }

    try {
      const resolved = await resolveAddressText(prediction.description);
      if (resolved.latitude != null && resolved.longitude != null) {
        const placeName = resolved.name || prediction.main_text || "";
        const localityParts = [resolved.area, resolved.city].filter(Boolean);
        let label = placeName;
        if (localityParts.length > 0) {
          const localityStr = localityParts.join(", ");
          if (!label.toLowerCase().includes(localityStr.toLowerCase())) {
            label = `${label}, ${localityStr}`;
          }
        }
        if (!label) {
          label = resolved.formatted_address || prediction.description;
        }

        setSelectedPlace({
          id: resolved.google_place_id || prediction.place_id,
          name: placeName || label,
          formattedAddress: resolved.formatted_address || prediction.description,
          latitude: resolved.latitude,
          longitude: resolved.longitude,
        });

        setExploreCenter({
          latitude: resolved.latitude,
          longitude: resolved.longitude,
          label,
        });
        setExploreLocationLabel(label);
        toastSuccess(`Exploring places near ${label}`);
      }
    } catch {
      toastError("Could not resolve coordinates for this area.");
    }
  };

  // Handle "Near Me" GPS exploration (explicit permission)
  const handleUseCurrentLocation = () => {
    if (!navigator.geolocation) {
      toastError("Geolocation is not supported by your browser.");
      return;
    }
    setIsLocatingUser(true);
    setViewportBounds(null);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setIsLocatingUser(false);
        setSelectedPlace(null);
        setIsCurrentLocation(true);
        const label = "Current location";
        setExploreCenter({
          latitude: pos.coords.latitude,
          longitude: pos.coords.longitude,
          label,
        });
        setExploreLocationLabel(label);
        toastSuccess("Exploring places near your current location");
      },
      () => {
        setIsLocatingUser(false);
        toastError("Location permission denied. Please search your area manually.");
      },
      { timeout: 10000 }
    );
  };

  // Viewport search handler for map "Search this area" floating action
  const handleSearchThisArea = (
    center: { latitude: number; longitude: number },
    radiusMeters: number,
    bounds?: ViewportBounds
  ) => {
    setIsCurrentLocation(false);
    const label = exploreLocationLabel || "Custom map area";
    setExploreLocationLabel(label);
    setExploreCenter({
      latitude: center.latitude,
      longitude: center.longitude,
      label,
    });
    setExploreRadius(radiusMeters);
    if (bounds) {
      setViewportBounds(bounds);
    }
  };


  const handleSelectPlaceOnMap = (placeId: string) => {
    setSelectedResourceId(placeId);
    setMobileDrawerOpen(true);
  };

  const handleSwitchToMapWithPlace = (placeId: string) => {
    setSelectedResourceId(placeId);
    setViewMode("map");
    setMobileDrawerOpen(true);
  };

  const currentSearchTarget =
    exploreCenter?.latitude != null && exploreCenter?.longitude != null
      ? exploreCenter
      : searchResult?.search_center?.latitude != null &&
        searchResult?.search_center?.longitude != null
      ? {
          latitude: searchResult.search_center.latitude,
          longitude: searchResult.search_center.longitude,
          label: searchResult.search_center.label || undefined,
        }
      : null;

  return (
    <div className="space-y-6 max-w-5xl mx-auto py-2 sm:py-6 relative">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-bold font-heading text-gray-950 dark:text-white flex items-center gap-2">
              <Compass className="w-7 h-7 text-brand-primary" />
              Local Resource Discovery
            </h1>
            {searchResult?.provider && (
              <span className="hidden sm:inline-flex items-center gap-1 text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-700">
                <Layers className="w-3 h-3" />
                Google Places API (New)
              </span>
            )}
          </div>
          <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Discover real local places, PGs, tiffin services, and transit around your area.
          </p>
        </div>

        {/* View Mode & Provider Toggle */}
        <div className="flex items-center gap-2 self-start sm:self-auto">
          <div className="flex items-center gap-1 bg-gray-100 dark:bg-brand-dark-muted p-1 rounded-xl">
            <button
              onClick={() => setViewMode("list")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                viewMode === "list"
                  ? "bg-white dark:bg-brand-dark-card text-brand-primary dark:text-teal-400 shadow-sm"
                  : "text-gray-700 dark:text-gray-300 hover:text-gray-950"
              }`}
            >
              <List className="w-4 h-4" />
              <span>List</span>
            </button>
            <button
              onClick={() => setViewMode("map")}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                viewMode === "map"
                  ? "bg-white dark:bg-brand-dark-card text-brand-primary dark:text-teal-400 shadow-sm"
                  : "text-gray-700 dark:text-gray-300 hover:text-gray-950"
              }`}
            >
              <MapIcon className="w-4 h-4" />
              <span>Map</span>
            </button>
          </div>
        </div>
      </div>

      {/* Location Exploration Control Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 p-3.5 bg-white dark:bg-brand-dark-surface rounded-2xl border border-gray-200 dark:border-brand-dark-border shadow-sm">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-9 h-9 rounded-xl bg-teal-50 dark:bg-teal-950/50 text-brand-primary flex items-center justify-center shrink-0">
            <MapPin className="w-5 h-5" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-[11px] font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                {requestIdParam
                  ? "Request Destination"
                  : selectedPlace
                  ? "Selected Place"
                  : isCurrentLocation
                  ? "Current GPS Location"
                  : "Exploration Area"}
              </span>
              {selectedPlace && (
                <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-200 border border-emerald-300/60 dark:border-emerald-700">
                  Exact Place
                </span>
              )}
              {isCurrentLocation && (
                <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-blue-100 dark:bg-blue-950/60 text-blue-800 dark:text-blue-200 border border-blue-300/60 dark:border-blue-700">
                  GPS Active
                </span>
              )}
              {requestIdParam && (
                <span className="text-[10px] px-2 py-0.5 rounded-full font-semibold bg-teal-100 dark:bg-teal-900/60 text-teal-800 dark:text-teal-200 border border-teal-300/60 dark:border-teal-700">
                  Request Linked
                </span>
              )}
            </div>
            <p className="text-base font-bold text-gray-950 dark:text-white truncate">
              {exploreLocationLabel ||
                searchResult?.search_center?.label ||
                "Pune, Maharashtra"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 self-end sm:self-center shrink-0">
          {isChangingLocation ? (
            <div className="flex items-center gap-2 w-full sm:w-80">
              <div className="flex-1">
                <PlaceAutocomplete
                  onSelectPrediction={handleSelectExplorePrediction}
                  placeholder="Search any society or locality (e.g. Megapolis Mystic, Kakkanad)..."
                />
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsChangingLocation(false)}
                className="shrink-0 text-gray-600 dark:text-gray-300 hover:text-gray-900"
              >
                <X className="w-4 h-4" />
              </Button>
            </div>
          ) : (
            <>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => setIsChangingLocation(true)}
                className="text-xs font-semibold text-gray-800 dark:text-gray-200"
              >
                Change Area
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleUseCurrentLocation}
                disabled={isLocatingUser}
                title="Explore places near my GPS location"
                className="text-xs font-semibold text-gray-800 dark:text-gray-200 hover:text-brand-primary"
              >
                <Crosshair className={`w-3.5 h-3.5 mr-1 ${isLocatingUser ? "animate-spin" : ""}`} />
                Near Me
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Target Location Context Banner with Radius Controls */}
      {searchResult?.search_center?.label && (
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-xl bg-teal-50/70 dark:bg-brand-dark-muted/40 border border-teal-200/60 dark:border-brand-dark-border text-xs">
          <div className="flex items-center gap-2 text-teal-950 dark:text-teal-200 font-medium">
            <Compass className="w-4 h-4 text-brand-primary shrink-0" />
            <span>
              Searching near{" "}
              <strong className="font-bold text-gray-950 dark:text-white">
                {searchResult.search_center.label}
              </strong>{" "}
              within{" "}
              <span className="font-bold text-brand-primary">
                {searchResult.radius_meters < 1000
                  ? `${searchResult.radius_meters} m`
                  : `${(searchResult.radius_meters / 1000).toFixed(1)} km`}
              </span>
            </span>
          </div>

          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[11px] text-gray-500 dark:text-gray-400 font-semibold mr-1">
              Radius:
            </span>
            {[100, 250, 500, 1000, 2000].map((r) => (
              <button
                key={r}
                type="button"
                onClick={() => setExploreRadius(r)}
                className={`px-2 py-0.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                  exploreRadius === r
                    ? "bg-brand-primary text-white shadow-sm"
                    : "bg-white dark:bg-brand-dark-card border border-gray-200 dark:border-brand-dark-border text-gray-700 dark:text-gray-300 hover:border-brand-primary"
                }`}
              >
                {r < 1000 ? `${r}m` : `${r / 1000}km`}
              </button>
            ))}

            {requestIdParam && (
              <Link
                to={`/matching?request_id=${requestIdParam}`}
                className="ml-2 text-brand-primary hover:underline font-bold flex items-center gap-1"
              >
                <Sparkles className="w-3.5 h-3.5" />
                <span>Helper Matches</span>
              </Link>
            )}
          </div>
        </div>
      )}

      {/* Search Input */}
      <div className="relative">
        <Search className="w-4 h-4 text-gray-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search places by name or specialty (e.g. vegetarian tiffin, ladies PG, metro)..."
          className="w-full pl-10 pr-4 py-2.5 rounded-xl text-sm border border-gray-200 dark:border-brand-dark-border bg-white dark:bg-brand-dark-card text-gray-950 dark:text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-brand-primary font-medium"
        />
      </div>

      {/* Category Pills (Horizontal Scroll) */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
        <button
          onClick={() => handleCategoryClick("")}
          className={`shrink-0 px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all border ${
            selectedCategory === ""
              ? "bg-brand-primary text-white border-brand-primary"
              : "bg-white dark:bg-brand-dark-card text-gray-800 dark:text-gray-200 border-gray-200 dark:border-brand-dark-border hover:border-brand-primary"
          }`}
        >
          All Categories
        </button>

        {categories.map((cat) => {
          const IconComp = CATEGORY_ICON_MAP[cat.icon] || Compass;
          const isSelected = selectedCategory === cat.id;

          return (
            <button
              key={cat.id}
              onClick={() => handleCategoryClick(cat.id)}
              className={`shrink-0 flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all border ${
                isSelected
                  ? "bg-brand-primary text-white border-brand-primary"
                  : "bg-white dark:bg-brand-dark-card text-gray-800 dark:text-gray-200 border-gray-200 dark:border-brand-dark-border hover:border-brand-primary"
              }`}
            >
              <IconComp className="w-3.5 h-3.5" />
              <span>{cat.display_name}</span>
            </button>
          );
        })}
      </div>

      {/* Main Content Area */}
      {viewMode === "map" ? (
        <div className="space-y-4">
          {/* Real Community Helper Status (Zero Fake Markers) */}
          {isLoadingHelpers ? (
            <div className="flex items-center gap-2 p-2.5 px-3.5 rounded-xl bg-gray-50 dark:bg-brand-dark-muted/20 border border-gray-200 dark:border-brand-dark-border text-xs font-medium text-gray-700 dark:text-gray-300">
              <Users className="w-3.5 h-3.5 text-gray-500 animate-pulse shrink-0" />
              <span>Checking for enrolled community helpers in this area...</span>
            </div>
          ) : nearbyHelpers.length === 0 ? (
            <div className="flex flex-wrap items-center justify-between gap-2 p-2.5 px-3.5 rounded-xl bg-gray-50 dark:bg-brand-dark-muted/20 border border-gray-200 dark:border-brand-dark-border text-xs font-medium text-gray-700 dark:text-gray-300">
              <div className="flex items-center gap-2">
                <Users className="w-3.5 h-3.5 text-gray-500 shrink-0" />
                <span>No NEST helpers found in this area yet.</span>
              </div>
              <Link
                to="/register?role=helper"
                className="text-brand-primary hover:underline font-bold"
              >
                Be the first local helper to join this area →
              </Link>
            </div>
          ) : (
            <div className="flex flex-wrap items-center justify-between gap-2 p-2.5 px-3.5 rounded-xl bg-indigo-50/80 dark:bg-indigo-950/30 border border-indigo-200/80 dark:border-indigo-800 text-xs font-semibold text-indigo-950 dark:text-indigo-100">
              <div className="flex items-center gap-2">
                <Users className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400 shrink-0" />
                <span>
                  Found <strong>{nearbyHelpers.length}</strong> verified NEST community helper{nearbyHelpers.length > 1 ? "s" : ""} active nearby
                </span>
              </div>
              {requestIdParam ? (
                <Link
                  to={`/matching?request_id=${requestIdParam}`}
                  className="text-indigo-700 dark:text-indigo-300 hover:underline font-bold"
                >
                  View Helper Matches →
                </Link>
              ) : (
                <Link
                  to="/connections"
                  className="text-indigo-700 dark:text-indigo-300 hover:underline font-bold"
                >
                  Connect with Helpers →
                </Link>
              )}
            </div>
          )}

          <Card className="p-2 overflow-hidden rounded-2xl">
            <GoogleMap
              targetLocation={currentSearchTarget}
              candidates={helperMapCandidates}
              places={searchResult?.resources || []}
              selectedPlaceId={selectedResourceId}
              onSelectPlace={(place) => handleSelectPlaceOnMap(place.id)}
              onSearchThisArea={handleSearchThisArea}
              isSearchingArea={isLoading}
              className="h-[440px] sm:h-[540px]"
            />
          </Card>

          {/* Desktop: Selected place preview card below map */}
          {selectedResource ? (
            <div className="hidden sm:block animate-fade-in space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
                  Selected Place Details
                </h4>
                {selectedResource.maps_url && (
                  <a
                    href={selectedResource.maps_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs font-bold text-brand-primary hover:underline flex items-center gap-1"
                  >
                    <span>View in Maps</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>
              <ResourceCard resource={selectedResource} isSelected={true} />
            </div>
          ) : (
            <div className="hidden sm:block p-4 bg-gray-50 dark:bg-brand-dark-muted/20 border border-gray-200 dark:border-brand-dark-border rounded-xl text-center text-xs font-medium text-gray-700 dark:text-gray-300">
              Click any place marker on the map to preview its ratings, open hours, and direct navigation links.
            </div>
          )}

          {/* Mobile Bottom-Sheet Drawer for place details */}
          {mobileDrawerOpen && selectedResource && (
            <div className="sm:hidden fixed inset-x-0 bottom-0 z-50 p-4 bg-white dark:bg-brand-dark-surface rounded-t-3xl shadow-2xl border-t border-gray-200 dark:border-brand-dark-border animate-slide-up">
              <div className="w-10 h-1 bg-gray-400 dark:bg-gray-500 rounded-full mx-auto mb-3" />
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-brand-primary">
                  {selectedResource.category_display_name}
                </span>
                <button
                  type="button"
                  onClick={() => setMobileDrawerOpen(false)}
                  className="p-1 rounded-full text-gray-500 hover:text-gray-800 dark:hover:text-gray-200"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <h3 className="font-bold text-base text-gray-950 dark:text-white line-clamp-1">
                {selectedResource.name}
              </h3>
              {selectedResource.formatted_address && (
                <p className="text-xs font-medium text-gray-700 dark:text-gray-300 line-clamp-2 mt-1">
                  {selectedResource.formatted_address}
                </p>
              )}
              <div className="flex items-center gap-3 mt-3 text-xs">
                {selectedResource.rating != null ? (
                  <span className="font-bold text-amber-700 dark:text-amber-400">
                    ★ {selectedResource.rating.toFixed(1)}
                  </span>
                ) : (
                  <span className="text-gray-500 dark:text-gray-400 font-medium">Rating unavailable</span>
                )}
                {selectedResource.distance_km != null && (
                  <span className="text-gray-700 dark:text-gray-300 font-semibold">
                    {selectedResource.distance_km} km away
                  </span>
                )}
                {selectedResource.is_open_now != null && (
                  <span className={selectedResource.is_open_now ? "text-emerald-700 dark:text-emerald-400 font-semibold" : "text-gray-600 dark:text-gray-400"}>
                    {selectedResource.is_open_now ? "Open Now" : "Closed"}
                  </span>
                )}
              </div>
              {selectedResource.maps_url && (
                <div className="mt-4 pt-3 border-t border-gray-100 dark:border-brand-dark-border">
                  <a
                    href={selectedResource.maps_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-brand-primary text-white font-semibold text-xs"
                  >
                    <span>Open in Maps</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                </div>
              )}
            </div>
          )}
        </div>
      ) : isLoading ? (
        <div className="space-y-4">
          <CardSkeleton />
          <CardSkeleton />
          <CardSkeleton />
        </div>
      ) : searchResult?.status === "PROVIDER_UNAVAILABLE" ? (
        <Card className="p-8 text-center space-y-4">
          <div className="w-12 h-12 rounded-full bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 flex items-center justify-center mx-auto">
            <AlertCircle className="w-6 h-6" />
          </div>
          <div className="space-y-1.5">
            <h3 className="font-bold text-lg text-gray-950 dark:text-white font-heading">
              Local Places Search Unavailable
            </h3>
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 max-w-md mx-auto">
              Real Google Places Platform data is required for NEST Local Resource Discovery. Google Places integration is currently unavailable or unconfigured. NEST does not fabricate fake businesses or synthetic places.
            </p>
          </div>

          {/* Diagnostic Setup Guidance for Developers/Admins */}
          <div className="p-5 text-left bg-gray-50 dark:bg-brand-dark-muted/30 border border-gray-200 dark:border-brand-dark-border rounded-xl max-w-lg mx-auto space-y-3 text-xs text-gray-800 dark:text-gray-200">
            <div className="flex items-center gap-2 font-bold text-gray-900 dark:text-white">
              <KeyRound className="w-4 h-4 text-brand-primary" />
              <span>How to enable Google Places Exploration:</span>
            </div>
            <ol className="list-decimal list-inside space-y-2 text-gray-700 dark:text-gray-300 font-mono text-[11px]">
              <li>Add <code className="bg-white dark:bg-brand-dark-card px-1.5 py-0.5 rounded border">GOOGLE_MAPS_SERVER_API_KEY</code> to <code className="font-sans font-semibold">backend/.env</code></li>
              <li>Add <code className="bg-white dark:bg-brand-dark-card px-1.5 py-0.5 rounded border">VITE_GOOGLE_MAPS_API_KEY</code> to <code className="font-sans font-semibold">frontend/.env</code></li>
              <li className="font-sans text-xs">Enable <span className="font-bold text-gray-950 dark:text-white">Places API (New)</span> and <span className="font-bold text-gray-950 dark:text-white">Maps JavaScript API</span> in Google Cloud Console</li>
            </ol>
            <div className="pt-2 flex justify-end">
              <Button
                variant="primary"
                size="sm"
                onClick={() => fetchResources()}
                className="text-xs flex items-center gap-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Retry Places Search
              </Button>
            </div>
          </div>

          {requestIdParam && (
            <div className="pt-2">
              <Link to={`/matching?request_id=${requestIdParam}`}>
                <Button variant="primary" size="sm">
                  Find Community Helpers
                </Button>
              </Link>
            </div>
          )}
        </Card>
      ) : searchResult?.resources.length === 0 ? (
        <EmptyState
          icon={<Compass className="w-8 h-8 text-gray-400" />}
          title="No Local Places Found"
          description="We couldn't find real places matching your query in this area. Try clearing filters, expanding the search area, or searching another category."
        />
      ) : (
        <div className="space-y-4">
          {searchResult?.resources.map((item) => (
            <div key={item.id} className="relative group">
              <ResourceCard
                resource={item}
                isSelected={selectedResourceId === item.id}
                onSelect={() => handleSwitchToMapWithPlace(item.id)}
              />
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
