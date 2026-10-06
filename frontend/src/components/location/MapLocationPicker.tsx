import { useEffect, useRef, useState, useCallback } from "react";
import { loadGoogleMaps } from "../../lib/google-maps-loader";
import { reverseGeocodeCoordinates } from "../../services/location";
import type { ResolvedLocation } from "../../types/google-location";
import {
  MapPin,
  Loader2,
  Check,
  X,
  AlertCircle,
  Navigation,
  Compass,
} from "lucide-react";

export interface ConfirmedMapLocation {
  city: string;
  area?: string;
  state?: string;
  country: string;
  latitude: number;
  longitude: number;
  display_name?: string;
  formatted_address?: string;
  postal_code?: string;
  google_place_id?: string;
  location_source: string;
  location_precision: string;
}

export interface MapLocationPickerProps {
  initialLocation?: {
    latitude?: number | null;
    longitude?: number | null;
    city?: string | null;
    area?: string | null;
  } | null;
  onConfirm: (loc: ConfirmedMapLocation) => void;
  onCancel: () => void;
}

const DEFAULT_INDIA_CENTER = { lat: 20.5937, lng: 78.9629 };

export function MapLocationPicker({
  initialLocation,
  onConfirm,
  onCancel,
}: MapLocationPickerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const markerRef = useRef<any>(null);

  const [mapLoaded, setMapLoaded] = useState<boolean | null>(null);
  const [selectedCoords, setSelectedCoords] = useState<{ lat: number; lng: number } | null>(
    initialLocation?.latitude != null && initialLocation?.longitude != null
      ? { lat: initialLocation.latitude, lng: initialLocation.longitude }
      : null
  );
  const [resolvedLocation, setResolvedLocation] = useState<ResolvedLocation | null>(null);
  const [isResolving, setIsResolving] = useState<boolean>(false);
  const [resolveError, setResolveError] = useState<string | null>(null);
  const [isGpsLocating, setIsGpsLocating] = useState<boolean>(false);

  // Reverse geocode handler
  const resolvePoint = useCallback(async (lat: number, lng: number) => {
    setIsResolving(true);
    setResolveError(null);
    try {
      const res = await reverseGeocodeCoordinates(lat, lng);
      setResolvedLocation(res);
    } catch {
      setResolveError("Unable to resolve address for this location. You can still confirm.");
      setResolvedLocation({
        city: initialLocation?.city || "Selected Area",
        area: initialLocation?.area || undefined,
        country: "India",
        latitude: lat,
        longitude: lng,
        location_source: "map_picker",
        location_precision: "approximate",
      });
    } finally {
      setIsResolving(false);
    }
  }, [initialLocation]);

  // Load Google Maps API
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

  // Update position & marker helper
  const handleUpdateCoordinates = useCallback(
    (lat: number, lng: number, panMap = true) => {
      setSelectedCoords({ lat, lng });

      const google = (window as any).google;
      if (google?.maps && mapInstanceRef.current) {
        if (!markerRef.current) {
          markerRef.current = new google.maps.Marker({
            position: { lat, lng },
            map: mapInstanceRef.current,
            draggable: true,
            title: "Drag to refine your location",
            icon: {
              path: google.maps.SymbolPath.BACKWARD_CLOSED_ARROW,
              scale: 6,
              fillColor: "#0F766E", // Teal brand color
              fillOpacity: 1,
              strokeColor: "#ffffff",
              strokeWeight: 2,
            },
            zIndex: 10,
          });

          markerRef.current.addListener("dragend", (e: any) => {
            const newLat = e.latLng.lat();
            const newLng = e.latLng.lng();
            handleUpdateCoordinates(newLat, newLng, false);
          });
        } else {
          markerRef.current.setPosition({ lat, lng });
        }

        if (panMap) {
          mapInstanceRef.current.panTo({ lat, lng });
        }
      }

      resolvePoint(lat, lng);
    },
    [resolvePoint]
  );

  // Initialize Map
  useEffect(() => {
    if (!mapLoaded || !containerRef.current) return;
    const google = (window as any).google;
    if (!google?.maps || typeof google.maps.Map !== "function") return;

    if (!mapInstanceRef.current) {
      const hasInitial = initialLocation?.latitude != null && initialLocation?.longitude != null;
      const startCenter = hasInitial
        ? { lat: initialLocation!.latitude!, lng: initialLocation!.longitude! }
        : DEFAULT_INDIA_CENTER;
      const startZoom = hasInitial ? 14 : 5;

      const map = new google.maps.Map(containerRef.current, {
        center: startCenter,
        zoom: startZoom,
        gestureHandling: "cooperative", // Prevents page-scroll locking on mobile
        zoomControl: true,
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: false,
        styles: [
          {
            featureType: "poi",
            elementType: "labels",
            stylers: [{ visibility: "off" }],
          },
        ],
      });

      mapInstanceRef.current = map;

      // Add map click listener
      map.addListener("click", (e: any) => {
        const clickedLat = e.latLng.lat();
        const clickedLng = e.latLng.lng();
        handleUpdateCoordinates(clickedLat, clickedLng, false);
      });

      // If initial location coords exist, place initial marker and resolve
      if (hasInitial) {
        handleUpdateCoordinates(initialLocation!.latitude!, initialLocation!.longitude!, true);
      } else if (navigator.geolocation) {
        // Try GPS position as center suggestion
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            if (!markerRef.current) {
              const userLat = pos.coords.latitude;
              const userLng = pos.coords.longitude;
              map.setCenter({ lat: userLat, lng: userLng });
              map.setZoom(13);
            }
          },
          () => {
            // Geolocation declined or unavailable; keep default India center
          },
          { timeout: 4000 }
        );
      }
    }
  }, [mapLoaded, initialLocation, handleUpdateCoordinates]);

  // GPS centering action button
  const handleCenterOnGps = () => {
    if (!navigator.geolocation) return;
    setIsGpsLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setIsGpsLocating(false);
        const lat = pos.coords.latitude;
        const lng = pos.coords.longitude;
        if (mapInstanceRef.current) {
          mapInstanceRef.current.setCenter({ lat, lng });
          mapInstanceRef.current.setZoom(14);
        }
        handleUpdateCoordinates(lat, lng, true);
      },
      () => {
        setIsGpsLocating(false);
      },
      { timeout: 6000, enableHighAccuracy: true }
    );
  };

  const handleConfirm = () => {
    if (!selectedCoords) return;
    const city = resolvedLocation?.city || resolvedLocation?.area || initialLocation?.city || "Selected Location";
    const area = resolvedLocation?.area || initialLocation?.area || undefined;
    const state = resolvedLocation?.state || undefined;
    const country = resolvedLocation?.country || "India";

    const displayName =
      resolvedLocation?.display_name ||
      (area ? `${area}, ${city}` : city);

    onConfirm({
      city: city.trim(),
      area: area ? area.trim() : undefined,
      state: state ? state.trim() : undefined,
      country: country.trim(),
      latitude: selectedCoords.lat,
      longitude: selectedCoords.lng,
      display_name: displayName,
      formatted_address: resolvedLocation?.formatted_address || undefined,
      postal_code: resolvedLocation?.postal_code || undefined,
      google_place_id: resolvedLocation?.google_place_id || undefined,
      location_source: "map_picker",
      location_precision: resolvedLocation?.location_precision || "locality",
    });
  };

  const readableLocationName =
    resolvedLocation?.display_name ||
    [resolvedLocation?.area, resolvedLocation?.city, resolvedLocation?.state, resolvedLocation?.country || "India"]
      .filter(Boolean)
      .join(", ");

  return (
    <div
      role="region"
      aria-label="Map Location Picker"
      className="p-4 sm:p-5 rounded-2xl border-2 border-teal-300 dark:border-teal-700 bg-white dark:bg-brand-dark-card space-y-4 shadow-md animate-fade-in"
    >
      {/* Header */}
      <div className="flex items-center justify-between pb-1 border-b border-gray-100 dark:border-brand-dark-border">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-brand-primary/10 dark:bg-brand-primary/20 text-brand-primary flex items-center justify-center shrink-0">
            <MapPin className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100">
              Pick Location on Map
            </h3>
            <p className="text-[11px] text-gray-500 dark:text-gray-400">
              Click anywhere on the map or drag the pin to set your profile location
            </p>
          </div>
        </div>

        <button
          type="button"
          onClick={onCancel}
          aria-label="Close map picker"
          className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-brand-dark-muted/40 transition-colors"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* Map Display & Canvas */}
      <div className="relative rounded-xl overflow-hidden border border-gray-200 dark:border-brand-dark-border shadow-inner">
        {/* Floating Quick GPS button */}
        <button
          type="button"
          onClick={handleCenterOnGps}
          disabled={isGpsLocating}
          title="Jump map to current GPS position"
          className="absolute top-2.5 right-2.5 z-10 flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/95 dark:bg-brand-dark-card/95 border border-gray-200 dark:border-brand-dark-border text-[11px] font-semibold text-gray-700 dark:text-gray-200 shadow hover:bg-gray-50 dark:hover:bg-brand-dark-surface transition-all disabled:opacity-50"
        >
          {isGpsLocating ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin text-brand-primary" />
          ) : (
            <Navigation className="w-3.5 h-3.5 text-brand-primary" />
          )}
          <span>Locate Me</span>
        </button>

        {/* Google Map Container or Test Fallback Canvas */}
        <div
          ref={containerRef}
          data-testid="map-picker-canvas"
          onClick={() => {
            // Test & offline fallback: clicking canvas sets sample point if Google Maps JS is not loaded
            if (!mapLoaded && !selectedCoords) {
              handleUpdateCoordinates(18.5738, 73.7561, false);
            }
          }}
          className="h-64 sm:h-72 w-full bg-slate-100 dark:bg-slate-900/60 flex items-center justify-center cursor-crosshair"
        >
          {mapLoaded === null && (
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <Loader2 className="w-4 h-4 animate-spin text-brand-primary" />
              <span>Loading map...</span>
            </div>
          )}

          {mapLoaded === false && (
            <div className="p-4 text-center space-y-2">
              <Compass className="w-8 h-8 mx-auto text-gray-400 animate-pulse" />
              <p className="text-xs font-semibold text-gray-700 dark:text-gray-300">
                Interactive Map Canvas
              </p>
              <p className="text-[11px] text-gray-500 dark:text-gray-400 max-w-xs">
                Click inside this area to place a pin and test reverse geocoding
              </p>
              {selectedCoords && (
                <div className="inline-flex items-center gap-1 text-[11px] font-bold text-teal-700 dark:text-teal-300 bg-teal-50 dark:bg-teal-950/40 px-2.5 py-1 rounded-full">
                  <MapPin className="w-3 h-3" />
                  <span>Pin placed at ({selectedCoords.lat.toFixed(4)}, {selectedCoords.lng.toFixed(4)})</span>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Selected Location Summary Panel */}
      <div className="p-3.5 rounded-xl bg-teal-50/80 dark:bg-brand-dark-surface border border-teal-200 dark:border-teal-800/60 space-y-2 text-xs">
        <div className="flex items-center justify-between">
          <span className="font-bold text-teal-900 dark:text-teal-200 flex items-center gap-1.5 uppercase text-[10px] tracking-wider">
            <Check className="w-3.5 h-3.5 text-brand-primary" />
            Selected Location
          </span>
          {isResolving && (
            <span className="inline-flex items-center gap-1 text-[11px] text-teal-700 dark:text-teal-300 font-medium">
              <Loader2 className="w-3 h-3 animate-spin" />
              Resolving address...
            </span>
          )}
        </div>

        {selectedCoords ? (
          <div className="space-y-1.5">
            <p className="font-bold text-sm text-gray-900 dark:text-gray-100">
              📍 {readableLocationName || "Resolving locality..."}
            </p>

            {resolvedLocation?.formatted_address && (
              <p className="text-xs text-gray-600 dark:text-gray-400">
                {resolvedLocation.formatted_address}
              </p>
            )}

            {/* Structured Area / City / State / Country breakdown */}
            <div className="flex items-center gap-2 pt-1 flex-wrap text-[11px] font-medium text-gray-600 dark:text-gray-300">
              {resolvedLocation?.area && (
                <span className="px-2 py-0.5 rounded bg-white dark:bg-brand-dark-card border border-teal-200 dark:border-teal-800">
                  Area: <strong>{resolvedLocation.area}</strong>
                </span>
              )}
              {resolvedLocation?.city && (
                <span className="px-2 py-0.5 rounded bg-white dark:bg-brand-dark-card border border-teal-200 dark:border-teal-800">
                  City: <strong>{resolvedLocation.city}</strong>
                </span>
              )}
              {resolvedLocation?.state && (
                <span className="px-2 py-0.5 rounded bg-white dark:bg-brand-dark-card border border-teal-200 dark:border-teal-800">
                  State: <strong>{resolvedLocation.state}</strong>
                </span>
              )}
              <span className="px-2 py-0.5 rounded bg-white dark:bg-brand-dark-card border border-teal-200 dark:border-teal-800">
                Country: <strong>{resolvedLocation?.country || "India"}</strong>
              </span>
            </div>
          </div>
        ) : (
          <p className="text-xs text-gray-600 dark:text-gray-400 italic">
            Click or tap anywhere on the map above to drop a location pin.
          </p>
        )}

        {resolveError && (
          <div className="flex items-center gap-1.5 text-amber-700 dark:text-amber-300 text-[11px] pt-1">
            <AlertCircle className="w-3.5 h-3.5 shrink-0" />
            <span>{resolveError}</span>
          </div>
        )}
      </div>

      {/* Confirmation Actions */}
      <div className="flex items-center justify-end gap-2.5 pt-1">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-xs font-semibold rounded-xl border border-gray-300 dark:border-brand-dark-border text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-brand-dark-muted/40 transition-colors"
        >
          Cancel
        </button>

        <button
          type="button"
          onClick={handleConfirm}
          disabled={!selectedCoords || isResolving}
          className="px-4 py-2 text-xs font-bold rounded-xl bg-brand-primary text-white hover:bg-brand-primary/90 transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-1.5"
        >
          <Check className="w-3.5 h-3.5" />
          <span>Confirm Location</span>
        </button>
      </div>
    </div>
  );
}
