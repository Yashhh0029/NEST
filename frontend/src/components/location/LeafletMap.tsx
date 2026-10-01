import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import { Search, Loader2, Compass, Shield } from "lucide-react";
import type { ResourceItem } from "../../types/resource";

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

export interface ViewportBounds {
  minLat: number;
  maxLat: number;
  minLon: number;
  maxLon: number;
}

export interface LeafletMapProps {
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

function createPlaceIcon(name: string, isSelected: boolean) {
  const initial = (name || "P").charAt(0).toUpperCase();
  const bg = isSelected ? "#0D9488" : "#0F766E";
  const border = isSelected ? "#F0FDFA" : "#FFFFFF";
  const size = isSelected ? 34 : 28;
  const ring = isSelected
    ? "box-shadow: 0 0 0 4px rgba(13, 148, 136, 0.45);"
    : "box-shadow: 0 2px 6px rgba(0,0,0,0.3);";

  return L.divIcon({
    className: "nest-leaflet-marker",
    html: `
      <div style="
        width: ${size}px;
        height: ${size}px;
        background-color: ${bg};
        border: 2px solid ${border};
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: bold;
        font-size: ${isSelected ? 13 : 11}px;
        font-family: system-ui, sans-serif;
        ${ring}
        cursor: pointer;
        transition: transform 0.15s ease;
      ">
        ${initial}
      </div>
    `,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
}

function createTargetIcon(label: string) {
  return L.divIcon({
    className: "nest-target-marker",
    html: `
      <div style="
        background-color: #0F766E;
        color: white;
        padding: 4px 10px;
        border-radius: 9999px;
        border: 2px solid white;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        display: flex;
        align-items: center;
        gap: 4px;
        font-size: 11px;
        font-weight: 600;
        font-family: system-ui, sans-serif;
        white-space: nowrap;
        cursor: default;
      ">
        <span>📍 ${escapeHtml(label.slice(0, 24))}</span>
      </div>
    `,
    iconSize: [140, 26],
    iconAnchor: [70, 13],
  });
}

export function LeafletMap({
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
}: LeafletMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markersLayerRef = useRef<L.LayerGroup | null>(null);
  const markersMapRef = useRef<Map<string, { marker: L.Marker; popup: L.Popup }>>(new Map());
  const lastSearchedRef = useRef<{ lat: number; lng: number } | null>(null);
  const [showSearchThisArea, setShowSearchThisArea] = useState(false);

  const hasTarget =
    targetLocation?.latitude != null && targetLocation?.longitude != null;

  // Initialize center baseline
  useEffect(() => {
    if (hasTarget) {
      lastSearchedRef.current = {
        lat: targetLocation!.latitude!,
        lng: targetLocation!.longitude!,
      };
      setShowSearchThisArea(false);
    }
  }, [hasTarget, targetLocation?.latitude, targetLocation?.longitude]);

  // Mount Leaflet Map
  useEffect(() => {
    if (!containerRef.current) return;

    const defaultLat = hasTarget ? targetLocation!.latitude! : 20.5937;
    const defaultLng = hasTarget ? targetLocation!.longitude! : 78.9629;
    const defaultZoom = hasTarget ? 13 : 5;

    if (!mapRef.current) {
      const map = L.map(containerRef.current, {
        center: [defaultLat, defaultLng],
        zoom: defaultZoom,
        zoomControl: true,
        attributionControl: true,
      });

      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> contributors',
      }).addTo(map);

      const markersGroup = L.layerGroup().addTo(map);
      markersLayerRef.current = markersGroup;
      mapRef.current = map;

      map.on("moveend", () => {
        if (!onSearchThisArea) return;
        const center = map.getCenter();
        const last = lastSearchedRef.current;
        if (last) {
          const dist = computeHaversineKm(center.lat, center.lng, last.lat, last.lng);
          if (dist > 0.4) {
            setShowSearchThisArea(true);
          }
        }
      });
    }

    return () => {
      // Clean up map instance on unmount
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
        markersLayerRef.current = null;
      }
    };
  }, []);

  // Update Markers and Viewport
  useEffect(() => {
    if (!mapRef.current || !markersLayerRef.current) return;
    const map = mapRef.current;
    const layer = markersLayerRef.current;

    layer.clearLayers();
    markersMapRef.current.clear();

    const bounds = L.latLngBounds([]);

    // 1. Add Target Origin Pin
    if (hasTarget) {
      const targetLatLng = L.latLng(
        targetLocation!.latitude!,
        targetLocation!.longitude!
      );
      bounds.extend(targetLatLng);

      const label = targetLocation?.label || "Search Target Area";
      const targetMarker = L.marker(targetLatLng, {
        icon: createTargetIcon(label),
        zIndexOffset: 1000,
      });
      targetMarker.bindPopup(`
        <div style="font-family: system-ui, sans-serif; font-size: 12px; padding: 2px;">
          <strong style="color: #0F766E;">🎯 Search Origin</strong><br/>
          <span>${escapeHtml(label)}</span>
        </div>
      `);
      layer.addLayer(targetMarker);
    }

    // 2. Add Helper Candidates (if in Matching view)
    candidates.forEach((cand) => {
      if (
        cand.approximateLatitude != null &&
        cand.approximateLongitude != null
      ) {
        const candLatLng = L.latLng(
          cand.approximateLatitude,
          cand.approximateLongitude
        );
        bounds.extend(candLatLng);

        const isSelected = selectedCandidateId === cand.id;

        // Privacy circle
        const circle = L.circle(candLatLng, {
          radius: 1000,
          color: isSelected ? "#0D9488" : "#64748B",
          weight: isSelected ? 2 : 1,
          fillColor: isSelected ? "#14B8A6" : "#94A3B8",
          fillOpacity: isSelected ? 0.35 : 0.2,
        });
        circle.on("click", () => onSelectCandidate && onSelectCandidate(cand.id));
        layer.addLayer(circle);

        const marker = L.marker(candLatLng, {
          icon: createPlaceIcon(cand.name, isSelected),
          zIndexOffset: isSelected ? 500 : 10,
        });
        marker.on("click", () => onSelectCandidate && onSelectCandidate(cand.id));
        layer.addLayer(marker);
      }
    });

    // 3. Add Real Verified Places
    places.forEach((place) => {
      if (place.latitude != null && place.longitude != null) {
        const placeLatLng = L.latLng(place.latitude, place.longitude);
        bounds.extend(placeLatLng);

        const isSelected = selectedPlaceId === place.id;
        const marker = L.marker(placeLatLng, {
          icon: createPlaceIcon(place.name, isSelected),
          zIndexOffset: isSelected ? 900 : 50,
        });

        const ratingHtml =
          place.rating != null
            ? `<div style="font-size: 11px; font-weight: 600; color: #d97706; margin-bottom: 4px;">
                ★ ${place.rating.toFixed(1)} ${place.review_count ? `(${place.review_count})` : ""}
              </div>`
            : "";

        const addressHtml = place.formatted_address
          ? `<div style="font-size: 11px; color: #475569; margin-bottom: 6px; line-height: 1.3;">
              ${escapeHtml(place.formatted_address)}
            </div>`
          : "";

        const mapsLinkHtml = place.maps_url
          ? `<div style="margin-top: 4px;">
              <a href="${escapeHtml(place.maps_url)}" target="_blank" rel="noopener noreferrer" style="font-size: 11px; color: #0d9488; text-decoration: underline; font-weight: 600;">
                Open in Maps ↗
              </a>
            </div>`
          : "";

        const popupContent = `
          <div style="font-family: system-ui, sans-serif; padding: 4px; min-width: 180px; max-width: 250px; color: #0f172a;">
            <div style="font-size: 10px; font-weight: 700; text-transform: uppercase; color: #0f766e; margin-bottom: 2px;">
              ${escapeHtml(place.category_display_name || place.category)}
            </div>
            <strong style="font-size: 13px; line-height: 1.2; display: block; margin-bottom: 4px;">
              ${escapeHtml(place.name)}
            </strong>
            ${ratingHtml}
            ${addressHtml}
            ${mapsLinkHtml}
          </div>
        `;

        const popup = L.popup({ offset: [0, -14] }).setContent(popupContent);
        marker.bindPopup(popup);

        marker.on("click", () => {
          if (onSelectPlace) {
            onSelectPlace(place);
          }
        });

        layer.addLayer(marker);
        markersMapRef.current.set(place.id, { marker, popup });

        if (isSelected) {
          marker.openPopup();
        }
      }
    });

    // Fit bounds smoothly
    if (bounds.isValid() && (places.length > 1 || candidates.length > 1)) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 16 });
    } else if (hasTarget) {
      map.setView([targetLocation!.latitude!, targetLocation!.longitude!], 13);
    }
  }, [
    targetLocation,
    candidates,
    selectedCandidateId,
    places,
    selectedPlaceId,
    hasTarget,
    onSelectCandidate,
    onSelectPlace,
  ]);

  // Handle selected place synchronization (smooth panTo)
  useEffect(() => {
    if (!mapRef.current || !selectedPlaceId) return;
    const entry = markersMapRef.current.get(selectedPlaceId);
    if (entry) {
      entry.marker.openPopup();
      const place = places.find((p) => p.id === selectedPlaceId);
      if (place && place.latitude != null && place.longitude != null) {
        mapRef.current.panTo([place.latitude, place.longitude], { animate: true });
      }
    }
  }, [selectedPlaceId, places]);

  const handleSearchThisAreaClick = () => {
    if (!mapRef.current || !onSearchThisArea) return;
    const map = mapRef.current;
    const center = map.getCenter();
    const bounds = map.getBounds();
    const ne = bounds.getNorthEast();

    const distKm = computeHaversineKm(center.lat, center.lng, ne.lat, ne.lng);
    const radiusMeters = Math.min(25000, Math.max(1000, Math.round(distKm * 1000)));

    const viewportBounds: ViewportBounds = {
      minLat: bounds.getSouth(),
      maxLat: bounds.getNorth(),
      minLon: bounds.getWest(),
      maxLon: bounds.getEast(),
    };

    lastSearchedRef.current = { lat: center.lat, lng: center.lng };
    setShowSearchThisArea(false);
    onSearchThisArea(
      { latitude: center.lat, longitude: center.lng },
      radiusMeters,
      viewportBounds
    );
  };

  return (
    <div className={`relative w-full rounded-2xl overflow-hidden border border-gray-200 dark:border-brand-dark-border shadow-sm ${className}`}>
      <div ref={containerRef} className="w-full h-full z-0" />

      {/* Floating "Search this area" Button */}
      {showSearchThisArea && onSearchThisArea && (
        <div className="absolute top-4 left-1/2 -translate-x-1/2 z-[1000] animate-fade-in">
          <button
            type="button"
            onClick={handleSearchThisAreaClick}
            disabled={isSearchingArea}
            className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-brand-dark-surface text-brand-primary dark:text-teal-300 font-semibold text-xs rounded-full shadow-xl border border-teal-200 dark:border-teal-800 hover:bg-teal-50 dark:hover:bg-brand-dark-muted transition-all active:scale-95 disabled:opacity-50"
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

      {/* Real Provider Badge */}
      <div className="absolute top-2.5 right-2.5 z-[1000] pointer-events-none">
        {places.length > 0 && candidates.length === 0 ? (
          <span className="flex items-center gap-1 text-[11px] font-medium text-teal-800 bg-white/95 backdrop-blur-sm px-2.5 py-1 rounded-full shadow-md border border-teal-100">
            <Compass className="w-3 h-3 text-brand-primary" />
            Real OpenStreetMap Places
          </span>
        ) : (
          <span className="flex items-center gap-1 text-[11px] font-medium text-teal-800 bg-white/95 backdrop-blur-sm px-2.5 py-1 rounded-full shadow-md border border-teal-100">
            <Shield className="w-3 h-3 text-brand-primary" />
            Privacy Protected Area
          </span>
        )}
      </div>
    </div>
  );
}
