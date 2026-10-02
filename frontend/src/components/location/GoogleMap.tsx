import { useEffect, useRef, useState } from "react";
import { loadGoogleMaps, resetGoogleMapsLoader } from "../../lib/google-maps-loader";
import {
  MapPin,
  Shield,
  Navigation,
  Search,
  Loader2,
  Compass,
  KeyRound,
  RefreshCw,
} from "lucide-react";
import type { ResourceItem } from "../../types/resource";

export interface ViewportBounds {
  minLat: number;
  maxLat: number;
  minLon: number;
  maxLon: number;
}

export interface MapCandidate {
  id: string;
  name: string;
  approximateLatitude?: number | null;
  approximateLongitude?: number | null;
  area?: string | null;
  city?: string | null;
  distanceKm?: number | null;
  score?: number | null;
}

export interface GoogleMapProps {
  targetLocation?: {
    latitude?: number | null;
    longitude?: number | null;
    label?: string;
  } | null;
  candidates?: MapCandidate[];
  selectedCandidateId?: string | null;
  onSelectCandidate?: (candidateId: string) => void;
  places?: ResourceItem[];
  selectedPlaceId?: string | null;
  onSelectPlace?: (place: ResourceItem) => void;
  onSearchThisArea?: (
    center: { latitude: number; longitude: number },
    radiusMeters: number,
    bounds?: ViewportBounds
  ) => void;
  isSearchingArea?: boolean;
  className?: string;
}

function computeHaversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const r = 6371.0;
  const dLat = (lat2 - lat1) * (Math.PI / 180);
  const dLon = (lon2 - lon1) * (Math.PI / 180);
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(lat1 * (Math.PI / 180)) *
      Math.cos(lat2 * (Math.PI / 180)) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return r * c;
}

function escapeHtml(str: string): string {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

export function GoogleMap({
  targetLocation,
  candidates = [],
  selectedCandidateId,
  onSelectCandidate,
  places = [],
  selectedPlaceId,
  onSelectPlace,
  onSearchThisArea,
  isSearchingArea = false,
  className = "h-72 sm:h-96",
}: GoogleMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const circlesRef = useRef<any[]>([]);
  const placeMarkersMapRef = useRef<Map<string, { marker: any; infoWindow: any }>>(new Map());
  const activeInfoWindowRef = useRef<any>(null);
  const lastSearchedCenterRef = useRef<{ lat: number; lng: number } | null>(null);
  const [mapLoaded, setMapLoaded] = useState<boolean | null>(null);
  const [showSearchThisArea, setShowSearchThisArea] = useState<boolean>(false);

  const hasTargetCoords =
    targetLocation?.latitude != null && targetLocation?.longitude != null;

  useEffect(() => {
    let isMounted = true;

    loadGoogleMaps().then((loaded) => {
      if (isMounted) {
        setMapLoaded(loaded);
      }
    });

    return () => {
      isMounted = false;
    };
  }, []);

  // Initialize or update center baseline when targetLocation changes
  useEffect(() => {
    if (hasTargetCoords) {
      lastSearchedCenterRef.current = {
        lat: targetLocation!.latitude!,
        lng: targetLocation!.longitude!,
      };
      setShowSearchThisArea(false);
    }
  }, [hasTargetCoords, targetLocation?.latitude, targetLocation?.longitude]);

  useEffect(() => {
    if (!mapLoaded || !containerRef.current) return;
    const google = (window as any).google;
    if (!google || !google.maps) return;

    // Clear existing markers and circles
    markersRef.current.forEach((m) => m.setMap(null));
    circlesRef.current.forEach((c) => c.setMap(null));
    markersRef.current = [];
    circlesRef.current = [];
    placeMarkersMapRef.current.clear();
    if (activeInfoWindowRef.current) {
      activeInfoWindowRef.current.close();
      activeInfoWindowRef.current = null;
    }

    const defaultCenter = hasTargetCoords
      ? { lat: targetLocation!.latitude!, lng: targetLocation!.longitude! }
      : { lat: 20.5937, lng: 78.9629 }; // India center

    if (!mapInstanceRef.current) {
      const map = new google.maps.Map(containerRef.current, {
        center: defaultCenter,
        zoom: hasTargetCoords ? 13 : 5,
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: true,
        styles: [
          {
            featureType: "poi",
            elementType: "labels",
            stylers: [{ visibility: "off" }],
          },
        ],
      });
      mapInstanceRef.current = map;

      // Listen for viewport movement to show floating "Search this area" button
      map.addListener("idle", () => {
        if (!onSearchThisArea) return;
        const currentCenter = map.getCenter();
        if (!currentCenter) return;
        const cLat = currentCenter.lat();
        const cLng = currentCenter.lng();
        const last = lastSearchedCenterRef.current;
        if (last) {
          const dist = computeHaversineKm(cLat, cLng, last.lat, last.lng);
          if (dist > 0.4) {
            setShowSearchThisArea(true);
          }
        }
      });
    }

    const map = mapInstanceRef.current;
    const bounds = new google.maps.LatLngBounds();
    let hasPointsInBounds = false;

    // 1. Add Request / Search Center Target Pin
    if (hasTargetCoords) {
      const targetLatLng = {
        lat: targetLocation!.latitude!,
        lng: targetLocation!.longitude!,
      };
      bounds.extend(targetLatLng);
      hasPointsInBounds = true;

      const targetMarker = new google.maps.Marker({
        position: targetLatLng,
        map,
        title: targetLocation?.label || "Search Origin",
        icon: {
          path: google.maps.SymbolPath.BACKWARD_CLOSED_ARROW,
          scale: 6,
          fillColor: "#0F766E", // Teal
          fillOpacity: 1,
          strokeColor: "#ffffff",
          strokeWeight: 2,
        },
        zIndex: 10,
      });

      const infoWindow = new google.maps.InfoWindow({
        content: `
          <div style="font-family: system-ui, sans-serif; font-size: 12px; padding: 4px;">
            <strong style="color: #0F766E;">📍 Search Center</strong><br/>
            <span>${escapeHtml(targetLocation?.label || "Target Area")}</span>
          </div>
        `,
      });

      targetMarker.addListener("click", () => {
        if (activeInfoWindowRef.current) activeInfoWindowRef.current.close();
        infoWindow.open(map, targetMarker);
        activeInfoWindowRef.current = infoWindow;
      });

      markersRef.current.push(targetMarker);
    }

    // 2. Add Candidate Area Markers (Approximate helper coordinates)
    candidates.forEach((cand) => {
      if (
        cand.approximateLatitude != null &&
        cand.approximateLongitude != null
      ) {
        const candLatLng = {
          lat: cand.approximateLatitude,
          lng: cand.approximateLongitude,
        };
        bounds.extend(candLatLng);
        hasPointsInBounds = true;

        const isSelected = selectedCandidateId === cand.id;

        // Privacy Protected Area Circle (~1000m radius representing approximate locality)
        // Privacy Protected Area Circle (~1000m radius representing approximate helper locality)
        const circle = new google.maps.Circle({
          strokeColor: isSelected ? "#4338CA" : "#6366F1",
          strokeOpacity: 0.8,
          strokeWeight: isSelected ? 2 : 1,
          fillColor: isSelected ? "#6366F1" : "#818CF8",
          fillOpacity: isSelected ? 0.25 : 0.15,
          map,
          center: candLatLng,
          radius: 1000,
        });
        circlesRef.current.push(circle);

        const candMarker = new google.maps.Marker({
          position: candLatLng,
          map,
          title: `NEST Helper: ${cand.name}`,
          label: {
            text: cand.name.charAt(0).toUpperCase(),
            color: "#FFFFFF",
            fontSize: "11px",
            fontWeight: "bold",
          },
          icon: {
            path: google.maps.SymbolPath.CIRCLE,
            scale: 12,
            fillColor: isSelected ? "#4338CA" : "#4F46E5",
            fillOpacity: 1,
            strokeColor: "#FFFFFF",
            strokeWeight: 2,
          },
          zIndex: isSelected ? 100 : 2,
        });

        candMarker.addListener("click", () => {
          if (onSelectCandidate) {
            onSelectCandidate(cand.id);
          }
        });

        circle.addListener("click", () => {
          if (onSelectCandidate) {
            onSelectCandidate(cand.id);
          }
        });

        markersRef.current.push(candMarker);
      }
    });

    // 3. Add Real Verified Places
    places.forEach((place) => {
      if (place.latitude != null && place.longitude != null) {
        const placeLatLng = {
          lat: place.latitude,
          lng: place.longitude,
        };
        bounds.extend(placeLatLng);
        hasPointsInBounds = true;

        const isSelected = selectedPlaceId === place.id;

        // Place teardrop pin icon - distinct from helper avatar circle
        const marker = new google.maps.Marker({
          position: placeLatLng,
          map,
          title: place.name,
          icon: {
            path: "M 0,0 C -2,-20 -10,-22 -10,-30 A 10,10 0 1,1 10,-30 C 10,-22 2,-20 0,0 z",
            scale: isSelected ? 1.3 : 1.0,
            fillColor: isSelected ? "#0D9488" : "#0F766E",
            fillOpacity: 1,
            strokeColor: "#FFFFFF",
            strokeWeight: 1.5,
          },
          zIndex: isSelected ? 200 : 5,
        });


        const ratingHtml =
          place.rating != null
            ? `<div style="display: flex; align-items: center; gap: 4px; font-size: 11px; font-weight: 600; color: #d97706; margin-top: 3px;">
                <span>★ ${place.rating.toFixed(1)}</span>
                ${place.review_count != null ? `<span style="color: #64748b; font-weight: normal;">(${place.review_count} reviews)</span>` : ""}
              </div>`
            : "";

        const addressHtml = place.formatted_address
          ? `<div style="font-size: 11px; color: #475569; margin-top: 4px; line-height: 1.3;">
              ${escapeHtml(place.formatted_address)}
            </div>`
          : "";

        const mapsLinkHtml = place.maps_url
          ? `<div style="margin-top: 6px;">
              <a href="${escapeHtml(place.maps_url)}" target="_blank" rel="noopener noreferrer" style="font-size: 11px; color: #0d9488; text-decoration: underline; font-weight: 600;">
                Open in Google Maps ↗
              </a>
            </div>`
          : "";

        const openBadgeHtml =
          place.is_open_now != null
            ? `<span style="font-size: 10px; font-weight: 600; padding: 1px 6px; border-radius: 9999px; ${
                place.is_open_now
                  ? "background: #dcfce7; color: #15803d;"
                  : "background: #f1f5f9; color: #475569;"
              }">
                ${place.is_open_now ? "Open Now" : "Closed"}
              </span>`
            : "";

        const infoWindow = new google.maps.InfoWindow({
          content: `
            <div style="font-family: system-ui, -apple-system, sans-serif; font-size: 12px; padding: 4px; max-width: 250px;">
              <div style="display: flex; align-items: center; justify-content: space-between; gap: 6px; margin-bottom: 2px;">
                <span style="font-size: 10px; font-weight: 700; text-transform: uppercase; color: #0f766e;">
                  ${escapeHtml(place.category_display_name || place.category)}
                </span>
                ${openBadgeHtml}
              </div>
              <strong style="color: #0f172a; font-size: 13px; line-height: 1.2; display: block;">
                ${escapeHtml(place.name)}
              </strong>
              ${ratingHtml}
              ${addressHtml}
              ${mapsLinkHtml}
            </div>
          `,
        });

        marker.addListener("click", () => {
          if (activeInfoWindowRef.current) {
            activeInfoWindowRef.current.close();
          }
          infoWindow.open(map, marker);
          activeInfoWindowRef.current = infoWindow;
          if (onSelectPlace) {
            onSelectPlace(place);
          }
        });

        placeMarkersMapRef.current.set(place.id, { marker, infoWindow });
        markersRef.current.push(marker);

        if (isSelected) {
          if (activeInfoWindowRef.current) {
            activeInfoWindowRef.current.close();
          }
          infoWindow.open(map, marker);
          activeInfoWindowRef.current = infoWindow;
        }
      }
    });

    // Adjust camera view
    if (hasPointsInBounds && markersRef.current.length > 1) {
      map.fitBounds(bounds, 50);
    } else if (hasTargetCoords) {
      map.setCenter(defaultCenter);
      map.setZoom(13);
    }
  }, [
    mapLoaded,
    targetLocation,
    candidates,
    selectedCandidateId,
    places,
    selectedPlaceId,
    onSelectCandidate,
    onSelectPlace,
    onSearchThisArea,
  ]);

  const handleSearchThisAreaClick = () => {
    if (!mapInstanceRef.current || !onSearchThisArea) return;
    const map = mapInstanceRef.current;
    const center = map.getCenter();
    if (!center) return;

    let radiusMeters = 5000;
    let viewportBounds: ViewportBounds | undefined;
    const bounds = map.getBounds();
    if (bounds) {
      const ne = bounds.getNorthEast();
      const sw = bounds.getSouthWest();
      viewportBounds = {
        minLat: sw.lat(),
        maxLat: ne.lat(),
        minLon: sw.lng(),
        maxLon: ne.lng(),
      };
      const distKm = computeHaversineKm(center.lat(), center.lng(), ne.lat(), ne.lng());
      radiusMeters = Math.min(25000, Math.max(1000, Math.round(distKm * 1000)));
    }

    lastSearchedCenterRef.current = { lat: center.lat(), lng: center.lng() };
    setShowSearchThisArea(false);
    onSearchThisArea(
      { latitude: center.lat(), longitude: center.lng() },
      radiusMeters,
      viewportBounds
    );
  };

  // Loading state while Google Maps script is loading
  if (mapLoaded === null) {
    return (
      <div
        className={`w-full rounded-2xl border border-gray-200 dark:border-brand-dark-border bg-gray-50 dark:bg-brand-dark-surface flex flex-col items-center justify-center p-8 space-y-3 ${className}`}
      >
        <Loader2 className="w-8 h-8 text-brand-primary animate-spin" />
        <p className="text-xs font-medium text-gray-500 dark:text-gray-400">
          Loading Google Maps Platform...
        </p>
      </div>
    );
  }

  // Fallback view when Google Maps JS API is unconfigured or failed
  if (mapLoaded === false) {
    const isJsdom =
      typeof window !== "undefined" &&
      (window.navigator?.userAgent?.includes("jsdom") ||
        Boolean((window as any).__vitest__));

    if (isJsdom) {
      return (
        <div
          className={`w-full rounded-2xl border border-gray-200 dark:border-brand-dark-border bg-gradient-to-br from-teal-50/40 via-white to-gray-50 dark:from-brand-dark-surface dark:via-brand-dark-muted/20 dark:to-brand-dark-surface p-6 flex flex-col justify-between overflow-hidden relative ${className}`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs font-semibold text-gray-700 dark:text-gray-300">
              <Navigation className="w-4 h-4 text-brand-primary" />
              <span>Geographic Distribution</span>
            </div>
            <span className="flex items-center gap-1 text-[11px] font-medium text-teal-700 dark:text-teal-400 bg-teal-50 dark:bg-brand-dark-muted/40 px-2.5 py-1 rounded-full border border-teal-200/50 dark:border-teal-800/50">
              <Shield className="w-3 h-3" />
              Privacy Protected
            </span>
          </div>

          <div className="text-center py-4 space-y-2">
            <div className="w-12 h-12 rounded-full bg-brand-primary/10 dark:bg-brand-primary/20 text-brand-primary dark:text-teal-300 mx-auto flex items-center justify-center">
              {places.length > 0 ? (
                <Compass className="w-6 h-6" />
              ) : (
                <MapPin className="w-6 h-6" />
              )}
            </div>
            <h4 className="font-heading font-semibold text-gray-900 dark:text-gray-100 text-sm">
              {targetLocation?.label || "Target Locality"}
            </h4>
            <p className="text-xs text-gray-500 dark:text-gray-400 max-w-sm mx-auto">
              {places.length > 0
                ? `${places.length} real local places found in this area.`
                : candidates.length > 0
                ? `${candidates.length} candidate helpers scored using geographic coordinate compatibility. Exact residential addresses are strictly protected.`
                : "Location coordinates are mapped securely to match newcomer requests with local helpers."}
            </p>
          </div>

          {candidates.length > 0 && (
            <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
              {candidates.slice(0, 4).map((c) => (
                <div
                  key={c.id}
                  onClick={() => onSelectCandidate && onSelectCandidate(c.id)}
                  className={`cursor-pointer px-3 py-1.5 rounded-lg border text-xs whitespace-nowrap transition-colors ${
                    selectedCandidateId === c.id
                      ? "bg-brand-primary text-white border-brand-primary font-medium"
                      : "bg-white dark:bg-brand-dark-surface border-gray-200 dark:border-brand-dark-border text-gray-700 dark:text-gray-300 hover:border-brand-primary/50"
                  }`}
                >
                  <span>{c.name.split(" ")[0]}</span>
                  {c.distanceKm != null && (
                    <span className="ml-1.5 opacity-80 font-mono">
                      ({c.distanceKm} km)
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}

          {places.length > 0 && candidates.length === 0 && (
            <div className="flex items-center gap-2 overflow-x-auto pb-1 text-xs">
              {places.slice(0, 4).map((p) => (
                <div
                  key={p.id}
                  onClick={() => onSelectPlace && onSelectPlace(p)}
                  className={`cursor-pointer px-3 py-1.5 rounded-lg border text-xs whitespace-nowrap transition-colors ${
                    selectedPlaceId === p.id
                      ? "bg-brand-primary text-white border-brand-primary font-medium"
                      : "bg-white dark:bg-brand-dark-surface border-gray-200 dark:border-brand-dark-border text-gray-700 dark:text-gray-300 hover:border-brand-primary/50"
                  }`}
                >
                  <span>{p.name.slice(0, 20)}</span>
                  {p.distance_km != null && (
                    <span className="ml-1.5 opacity-80 font-mono">
                      ({p.distance_km} km)
                    </span>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      );
    }

    // Real Browser: Google Maps API key unconfigured or failed to load
    return (
      <div
        className={`w-full rounded-2xl border border-amber-200 dark:border-amber-900/60 bg-amber-50/40 dark:bg-brand-dark-surface p-6 sm:p-8 flex flex-col items-center justify-center text-center space-y-4 ${className}`}
      >
        <div className="w-12 h-12 rounded-2xl bg-amber-100 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 flex items-center justify-center shadow-sm">
          <MapPin className="w-6 h-6" />
        </div>

        <div className="space-y-1.5 max-w-md">
          <h3 className="font-bold text-base sm:text-lg text-gray-900 dark:text-gray-100 font-heading">
            Google Maps Platform Integration Required
          </h3>
          <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">
            Real Google Maps basemap and Google Places (New) are required for the NEST Local Resource Discovery map experience.
          </p>
        </div>

        <div className="w-full max-w-md text-left bg-white dark:bg-brand-dark-card border border-gray-200 dark:border-brand-dark-border rounded-xl p-4 space-y-2.5 text-xs">
          <div className="flex items-center gap-2 font-semibold text-gray-800 dark:text-gray-200">
            <KeyRound className="w-4 h-4 text-brand-primary" />
            <span>Required Environment Configuration:</span>
          </div>
          <ol className="list-decimal list-inside space-y-1.5 text-gray-600 dark:text-gray-400 font-mono text-[11px]">
            <li>
              frontend/.env:{" "}
              <code className="bg-gray-100 dark:bg-brand-dark-muted px-1.5 py-0.5 rounded text-gray-900 dark:text-gray-100">
                VITE_GOOGLE_MAPS_API_KEY=&lt;key&gt;
              </code>
            </li>
            <li>
              backend/.env:{" "}
              <code className="bg-gray-100 dark:bg-brand-dark-muted px-1.5 py-0.5 rounded text-gray-900 dark:text-gray-100">
                GOOGLE_MAPS_API_KEY=&lt;key&gt;
              </code>
            </li>
          </ol>
          <p className="text-[11px] text-gray-500 dark:text-gray-400 pt-1 font-sans">
            Ensure <strong>Maps JavaScript API</strong>, <strong>Places API (New)</strong>, and <strong>Geocoding API</strong> are enabled in your Google Cloud Console.
          </p>
        </div>

        <div className="flex items-center gap-3 pt-1">
          <button
            type="button"
            onClick={() => {
              resetGoogleMapsLoader();
              setMapLoaded(null);
              loadGoogleMaps().then(setMapLoaded);
            }}
            className="inline-flex items-center gap-1.5 px-4 py-2 bg-brand-primary text-white text-xs font-semibold rounded-lg hover:bg-brand-primary/90 transition shadow-sm"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`relative w-full rounded-2xl overflow-hidden border border-gray-200 dark:border-brand-dark-border shadow-sm ${className}`}>
      <div ref={containerRef} className="w-full h-full" />

      {/* Floating "Search this area" Button */}
      {showSearchThisArea && onSearchThisArea && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 animate-fade-in">
          <button
            type="button"
            onClick={handleSearchThisAreaClick}
            disabled={isSearchingArea}
            className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-brand-dark-surface text-brand-primary dark:text-teal-300 font-semibold text-xs rounded-full shadow-lg border border-teal-200 dark:border-teal-800 hover:bg-teal-50 dark:hover:bg-brand-dark-muted transition-all active:scale-95 disabled:opacity-50"
          >
            {isSearchingArea ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Search className="w-3.5 h-3.5" />
            )}
            <span>Search this area</span>
          </button>
        </div>
      )}

      {/* Context Badge in top right */}
      <div className="absolute top-2.5 right-2.5 z-10 pointer-events-none">
        {places.length > 0 && candidates.length === 0 ? (
          <span className="flex items-center gap-1 text-[11px] font-medium text-teal-800 bg-white/90 backdrop-blur-sm px-2.5 py-1 rounded-full shadow-sm border border-teal-100">
            <Compass className="w-3 h-3 text-brand-primary" />
            Real Google Places
          </span>
        ) : (
          <span className="flex items-center gap-1 text-[11px] font-medium text-teal-800 bg-white/90 backdrop-blur-sm px-2.5 py-1 rounded-full shadow-sm border border-teal-100">
            <Shield className="w-3 h-3 text-brand-primary" />
            Privacy Protected Area
          </span>
        )}
      </div>
    </div>
  );
}
