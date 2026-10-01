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
} from "lucide-react";
import { ResourceCard } from "@/components/resource/ResourceCard";
import { GoogleMap, type MapCandidate, type ViewportBounds } from "@/components/location/GoogleMap";
import { PlaceAutocomplete } from "@/components/location/PlaceAutocomplete";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/hooks/useToast";
import { getResourceCategories, searchResources } from "@/services/resources";
import {
  getPlaceDetails,
  resolveAddressText,
  reverseGeocodeCoordinates,
  getRequestTargetLocation,
} from "@/services/location";
import type { PlaceAutocompletePrediction } from "@/types/google-location";
import type {
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

  // Provider mode: auto (Google if configured, else OpenStreetMap), osm, or google
  const [providerMode, setProviderMode] = useState<"auto" | "osm" | "google">("auto");

  // Location exploration state
  const [exploreCenter, setExploreCenter] = useState<{
    latitude: number;
    longitude: number;
    label?: string;
  } | null>(null);
  const [exploreRadius, setExploreRadius] = useState<number>(5000);
  const [exploreLocationLabel, setExploreLocationLabel] = useState<string>("");
  const [viewportBounds, setViewportBounds] = useState<ViewportBounds | null>(null);
  const [isChangingLocation, setIsChangingLocation] = useState<boolean>(false);
  const [isLocatingUser, setIsLocatingUser] = useState<boolean>(false);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState<boolean>(false);

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
              res.formatted_address ||
              [res.area, res.city].filter(Boolean).join(", ") ||
              "Request Target Location";
            setExploreCenter({
              latitude: res.latitude,
              longitude: res.longitude,
              label,
            });
            setExploreLocationLabel(label);
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
        limit: 15,
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

  // Map resources to MapCandidates for fallback backward compatibility
  const mapCandidates: MapCandidate[] = useMemo(() => {
    if (!searchResult?.resources) return [];
    return searchResult.resources
      .filter((r) => r.latitude != null && r.longitude != null)
      .map((r) => ({
        id: r.id,
        name: r.name,
        approximateLatitude: r.latitude,
        approximateLongitude: r.longitude,
        area: r.category_display_name,
        city: r.formatted_address,
        distanceKm: r.distance_km,
        score: r.ranking_score,
      }));
  }, [searchResult?.resources]);

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
    try {
      const details = await getPlaceDetails(prediction.place_id);
      if (details.latitude != null && details.longitude != null) {
        const label =
          [details.area, details.city].filter(Boolean).join(", ") ||
          details.formatted_address ||
          prediction.description;
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
        const label =
          [resolved.area, resolved.city].filter(Boolean).join(", ") ||
          resolved.formatted_address ||
          prediction.description;
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
      async (pos) => {
        setIsLocatingUser(false);
        try {
          const rev = await reverseGeocodeCoordinates(
            pos.coords.latitude,
            pos.coords.longitude
          );
          const label =
            [rev.area, rev.city].filter(Boolean).join(", ") ||
            rev.formatted_address ||
            "My Current Location";
          setExploreCenter({
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            label,
          });
          setExploreLocationLabel(label);
          toastSuccess(`Exploring places near ${label}`);
        } catch {
          setExploreCenter({
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
            label: "My Current Location",
          });
          setExploreLocationLabel("My Current Location");
        }
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
    setExploreCenter({
      latitude: center.latitude,
      longitude: center.longitude,
      label: `Map Viewport (${center.latitude.toFixed(2)}, ${center.longitude.toFixed(2)})`,
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
            <h1 className="text-2xl sm:text-3xl font-bold font-heading text-gray-900 dark:text-gray-100 flex items-center gap-2">
              <Compass className="w-7 h-7 text-brand-primary" />
              Local Resource Discovery
            </h1>
            {searchResult?.provider && (
              <span className="hidden sm:inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-teal-50 dark:bg-teal-950/40 text-brand-primary border border-teal-200 dark:border-teal-800">
                <Layers className="w-3 h-3" />
                {searchResult.provider === "openstreetmap"
                  ? "OpenStreetMap (Zero-Billing)"
                  : "Google Places API"}
              </span>
            )}
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400">
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
                  : "text-gray-600 dark:text-gray-400 hover:text-gray-900"
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
                  : "text-gray-600 dark:text-gray-400 hover:text-gray-900"
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
              <span className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">
                {requestIdParam ? "Request Destination" : "Exploration Area"}
              </span>
              {requestIdParam && (
                <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-teal-100 dark:bg-teal-900/60 text-teal-800 dark:text-teal-200">
                  Request Linked
                </span>
              )}
            </div>
            <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">
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
                  placeholder="Search any locality (e.g. Kakkanad, Kochi)..."
                />
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setIsChangingLocation(false)}
                className="shrink-0 text-gray-500 hover:text-gray-800"
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
                className="text-xs"
              >
                Change Area
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleUseCurrentLocation}
                disabled={isLocatingUser}
                title="Explore places near my GPS location"
                className="text-xs text-gray-600 dark:text-gray-300 hover:text-brand-primary"
              >
                <Crosshair className={`w-3.5 h-3.5 mr-1 ${isLocatingUser ? "animate-spin" : ""}`} />
                Near Me
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Target Location Context Banner */}
      {searchResult?.search_center?.label && (
        <div className="flex flex-wrap items-center justify-between gap-2 p-3.5 rounded-xl bg-teal-50/70 dark:bg-brand-dark-muted/40 border border-teal-200/60 dark:border-brand-dark-border text-xs">
          <div className="flex items-center gap-2 text-teal-900 dark:text-teal-200">
            <Compass className="w-4 h-4 text-brand-primary shrink-0" />
            <span>
              Searching places near{" "}
              <strong className="font-semibold text-gray-900 dark:text-gray-100">
                {searchResult.search_center.label}
              </strong>{" "}
              (within {(searchResult.radius_meters / 1000).toFixed(0)} km)
            </span>
          </div>

          {requestIdParam && (
            <Link
              to={`/matching?request_id=${requestIdParam}`}
              className="text-brand-primary hover:underline font-semibold flex items-center gap-1"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>View People Matches</span>
            </Link>
          )}
        </div>
      )}

      {/* Search Input */}
      <div className="relative">
        <Search className="w-4 h-4 text-gray-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search places by name or specialty (e.g. vegetarian tiffin, ladies PG, metro)..."
          className="w-full pl-10 pr-4 py-2.5 rounded-xl text-sm border border-gray-200 dark:border-brand-dark-border bg-white dark:bg-brand-dark-card text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-primary"
        />
      </div>

      {/* Category Pills (Horizontal Scroll) */}
      <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
        <button
          onClick={() => handleCategoryClick("")}
          className={`shrink-0 px-3.5 py-1.5 rounded-full text-xs font-semibold transition-all border ${
            selectedCategory === ""
              ? "bg-brand-primary text-white border-brand-primary"
              : "bg-white dark:bg-brand-dark-card text-gray-700 dark:text-gray-300 border-gray-200 dark:border-brand-dark-border hover:border-brand-primary"
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
                  : "bg-white dark:bg-brand-dark-card text-gray-700 dark:text-gray-300 border-gray-200 dark:border-brand-dark-border hover:border-brand-primary"
              }`}
            >
              <IconComp className="w-3.5 h-3.5" />
              <span>{cat.display_name}</span>
            </button>
          );
        })}
      </div>

      {/* Main Content Area */}
      {isLoading ? (
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
          <div className="space-y-1">
            <h3 className="font-bold text-lg text-gray-900 dark:text-gray-100">
              Local Places Search Unavailable
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md mx-auto">
              Google Places integration is currently unavailable or unconfigured. NEST does not fabricate fake businesses. Please try connecting with local community helpers instead.
            </p>
          </div>

          {/* Quick Option to Explore using OpenStreetMap (100% Free & Zero Billing) */}
          <div className="p-4 bg-teal-50 dark:bg-brand-dark-muted/40 border border-teal-200 dark:border-teal-800 rounded-xl max-w-lg mx-auto text-left text-xs space-y-2">
            <div className="flex items-center gap-2 font-semibold text-teal-900 dark:text-teal-200">
              <Compass className="w-4 h-4 text-brand-primary" />
              <span>Explore With OpenStreetMap (100% Free):</span>
            </div>
            <p className="text-gray-600 dark:text-gray-300">
              You can instantly explore real community-verified places, hostels, hospitals, and transit without any Google Cloud billing credentials.
            </p>
            <div className="pt-1 flex items-center gap-2">
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setProviderMode("osm");
                  fetchResources();
                }}
                className="text-xs"
              >
                Switch to OpenStreetMap Mode
              </Button>
            </div>
          </div>

          {/* Diagnostic Setup Guidance for Developers/Admins */}
          <div className="p-4 text-left bg-gray-50 dark:bg-brand-dark-muted/30 border border-gray-200 dark:border-brand-dark-border rounded-xl max-w-lg mx-auto space-y-2 text-xs text-gray-600 dark:text-gray-300">
            <div className="flex items-center gap-2 font-semibold text-gray-800 dark:text-gray-200">
              <KeyRound className="w-4 h-4 text-brand-primary" />
              <span>How to enable Google Places Exploration:</span>
            </div>
            <ol className="list-decimal list-inside space-y-1 text-gray-600 dark:text-gray-400">
              <li>Add <code className="font-mono bg-white dark:bg-brand-dark-card px-1 py-0.5 rounded border">GOOGLE_MAPS_API_KEY</code> to <code className="font-mono">backend/.env</code></li>
              <li>Add <code className="font-mono bg-white dark:bg-brand-dark-card px-1 py-0.5 rounded border">VITE_GOOGLE_MAPS_API_KEY</code> to <code className="font-mono">frontend/.env</code></li>
              <li>Enable <span className="font-medium">Places API (New)</span>, <span className="font-medium">Maps JavaScript API</span>, and <span className="font-medium">Geocoding API</span> in Google Cloud Console</li>
            </ol>
            <div className="pt-2 flex justify-end">
              <Button
                variant="secondary"
                size="sm"
                onClick={() => fetchResources()}
                className="text-xs flex items-center gap-1.5"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                Retry Search
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
      ) : viewMode === "map" ? (
        <div className="space-y-4">
          <Card className="p-2 overflow-hidden rounded-2xl">
            <GoogleMap
              targetLocation={currentSearchTarget}
              candidates={mapCandidates}
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
                <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">
                  Selected Place Details
                </h4>
                {selectedResource.maps_url && (
                  <a
                    href={selectedResource.maps_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs font-semibold text-brand-primary hover:underline flex items-center gap-1"
                  >
                    <span>View in Maps</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </a>
                )}
              </div>
              <ResourceCard resource={selectedResource} isSelected={true} />
            </div>
          ) : (
            <div className="hidden sm:block p-4 bg-gray-50 dark:bg-brand-dark-muted/20 border border-gray-200 dark:border-brand-dark-border rounded-xl text-center text-xs text-gray-500 dark:text-gray-400">
              Click any place marker on the map to preview its ratings, open hours, and direct navigation links.
            </div>
          )}

          {/* Mobile Bottom-Sheet Drawer for place details */}
          {mobileDrawerOpen && selectedResource && (
            <div className="sm:hidden fixed inset-x-0 bottom-0 z-50 p-4 bg-white dark:bg-brand-dark-surface rounded-t-3xl shadow-2xl border-t border-gray-200 dark:border-brand-dark-border animate-slide-up">
              <div className="w-10 h-1 bg-gray-300 dark:bg-gray-600 rounded-full mx-auto mb-3" />
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-brand-primary">
                  {selectedResource.category_display_name}
                </span>
                <button
                  type="button"
                  onClick={() => setMobileDrawerOpen(false)}
                  className="p-1 rounded-full text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <h3 className="font-bold text-base text-gray-900 dark:text-gray-100 line-clamp-1">
                {selectedResource.name}
              </h3>
              {selectedResource.formatted_address && (
                <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-2 mt-1">
                  {selectedResource.formatted_address}
                </p>
              )}
              <div className="flex items-center gap-3 mt-3 text-xs">
                {selectedResource.rating != null ? (
                  <span className="font-semibold text-amber-600">
                    ★ {selectedResource.rating.toFixed(1)}
                  </span>
                ) : (
                  <span className="text-gray-400">Rating unavailable</span>
                )}
                {selectedResource.distance_km != null && (
                  <span className="text-gray-500">
                    {selectedResource.distance_km} km away
                  </span>
                )}
                {selectedResource.is_open_now != null && (
                  <span className={selectedResource.is_open_now ? "text-emerald-600 font-medium" : "text-gray-400"}>
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
