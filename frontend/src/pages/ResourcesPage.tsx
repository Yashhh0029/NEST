import React, { useState, useEffect, useCallback, useMemo } from "react";
import { useSearchParams, Link } from "react-router-dom";
import {
  Search,
  MapPin,
  List,
  Map,
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
} from "lucide-react";
import { ResourceCard } from "@/components/resource/ResourceCard";
import { GoogleMap, type MapCandidate } from "@/components/location/GoogleMap";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { useToast } from "@/hooks/useToast";
import { getResourceCategories, searchResources } from "@/services/resources";
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

  const { error: toastError } = useToast();

  const [categories, setCategories] = useState<ResourceCategory[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>(initialCategoryParam);
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [viewMode, setViewMode] = useState<"list" | "map">("list");
  const [searchResult, setSearchResult] = useState<ResourceSearchResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [selectedResourceId, setSelectedResourceId] = useState<string | null>(null);

  // Load category metadata on mount
  useEffect(() => {
    getResourceCategories()
      .then((data) => setCategories(data.categories || []))
      .catch(() => {
        // Fallback or silent fail
      });
  }, []);

  // Fetch resources
  const fetchResources = useCallback(async () => {
    setIsLoading(true);
    try {
      const resp = await searchResources({
        request_id: requestIdParam,
        category: selectedCategory || undefined,
        query: searchQuery.trim() || undefined,
        limit: 15,
      });
      setSearchResult(resp);
    } catch {
      toastError("Failed to fetch local resources. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }, [requestIdParam, selectedCategory, searchQuery, toastError]);

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

  // Map resources to MapCandidates for GoogleMap component
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

  return (
    <div className="space-y-6 max-w-5xl mx-auto py-2 sm:py-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <h1 className="text-2xl sm:text-3xl font-bold font-heading text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <Compass className="w-7 h-7 text-brand-primary" />
            Local Resource Discovery
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Discover real local places, PGs, tiffin services, and transit around your area.
          </p>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center gap-1 bg-gray-100 dark:bg-brand-dark-muted p-1 rounded-xl self-start sm:self-auto">
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
            <Map className="w-4 h-4" />
            <span>Map</span>
          </button>
        </div>
      </div>

      {/* Target Location Context Banner */}
      {searchResult?.search_center?.label && (
        <div className="flex flex-wrap items-center justify-between gap-2 p-3.5 rounded-xl bg-teal-50/70 dark:bg-brand-dark-muted/40 border border-teal-200/60 dark:border-brand-dark-border text-xs">
          <div className="flex items-center gap-2 text-teal-900 dark:text-teal-200">
            <MapPin className="w-4 h-4 text-brand-primary shrink-0" />
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
        <Card className="p-8 text-center space-y-3">
          <div className="w-12 h-12 rounded-full bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 flex items-center justify-center mx-auto">
            <AlertCircle className="w-6 h-6" />
          </div>
          <h3 className="font-bold text-lg text-gray-900 dark:text-gray-100">
            Local Places Search Unavailable
          </h3>
          <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md mx-auto">
            Google Places integration is currently unavailable or unconfigured. NEST does not fabricate fake businesses. Please try connecting with local community helpers instead.
          </p>
          {requestIdParam && (
            <Link to={`/matching?request_id=${requestIdParam}`}>
              <Button variant="primary" size="sm" className="mt-2">
                Find Community Helpers
              </Button>
            </Link>
          )}
        </Card>
      ) : searchResult?.resources.length === 0 ? (
        <EmptyState
          icon={<Compass className="w-8 h-8 text-gray-400" />}
          title="No Local Places Found"
          description="We couldn't find real places matching your query in this area. Try clearing filters or searching another category."
        />
      ) : viewMode === "map" ? (
        <div className="space-y-4">
          <Card className="p-2 overflow-hidden rounded-2xl">
            <GoogleMap
              targetLocation={
                searchResult?.search_center
                  ? {
                      latitude: searchResult.search_center.latitude,
                      longitude: searchResult.search_center.longitude,
                      label: searchResult.search_center.label || undefined,
                    }
                  : null
              }
              candidates={mapCandidates}
              selectedCandidateId={selectedResourceId}
              onSelectCandidate={(id) => setSelectedResourceId(id)}
              className="h-96 sm:h-[450px]"
            />
          </Card>

          {/* Selected resource card below map */}
          {selectedResource && (
            <div className="animate-fade-in">
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
                Selected Place
              </h4>
              <ResourceCard resource={selectedResource} isSelected={true} />
            </div>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {searchResult?.resources.map((item) => (
            <ResourceCard
              key={item.id}
              resource={item}
              isSelected={selectedResourceId === item.id}
              onSelect={() => setSelectedResourceId(item.id)}
            />
          ))}
        </div>
      )}
    </div>
  );
};
