import { useEffect, useRef, useState } from "react";
import { loadGoogleMaps } from "../../lib/google-maps-loader";
import { MapPin, Shield, Navigation } from "lucide-react";

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
  className?: string;
}

export function GoogleMap({
  targetLocation,
  candidates = [],
  selectedCandidateId,
  onSelectCandidate,
  className = "h-72 sm:h-96",
}: GoogleMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<any>(null);
  const markersRef = useRef<any[]>([]);
  const circlesRef = useRef<any[]>([]);
  const [mapLoaded, setMapLoaded] = useState<boolean | null>(null);

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

  useEffect(() => {
    if (!mapLoaded || !containerRef.current) return;
    const google = (window as any).google;
    if (!google || !google.maps) return;

    // Clear existing markers and circles
    markersRef.current.forEach((m) => m.setMap(null));
    circlesRef.current.forEach((c) => c.setMap(null));
    markersRef.current = [];
    circlesRef.current = [];

    const defaultCenter = hasTargetCoords
      ? { lat: targetLocation!.latitude!, lng: targetLocation!.longitude! }
      : { lat: 20.5937, lng: 78.9629 }; // India center

    if (!mapInstanceRef.current) {
      mapInstanceRef.current = new google.maps.Map(containerRef.current, {
        center: defaultCenter,
        zoom: hasTargetCoords ? 12 : 5,
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
    }

    const map = mapInstanceRef.current;
    const bounds = new google.maps.LatLngBounds();

    // 1. Add Request Target Pin
    if (hasTargetCoords) {
      const targetLatLng = {
        lat: targetLocation!.latitude!,
        lng: targetLocation!.longitude!,
      };
      bounds.extend(targetLatLng);

      const targetMarker = new google.maps.Marker({
        position: targetLatLng,
        map,
        title: targetLocation?.label || "Request Target Destination",
        icon: {
          path: google.maps.SymbolPath.BACKWARD_CLOSED_ARROW,
          scale: 6,
          fillColor: "#0F766E", // Teal
          fillOpacity: 1,
          strokeColor: "#ffffff",
          strokeWeight: 2,
        },
      });

      const infoWindow = new google.maps.InfoWindow({
        content: `
          <div style="font-family: sans-serif; font-size: 12px; padding: 4px;">
            <strong style="color: #0F766E;">🎯 Target Location</strong><br/>
            <span>${targetLocation?.label || "Requested Area"}</span>
          </div>
        `,
      });

      targetMarker.addListener("click", () => {
        infoWindow.open(map, targetMarker);
      });

      markersRef.current.push(targetMarker);
    }

    // 2. Add Candidate Area Markers (Approximate coordinates)
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

        const isSelected = selectedCandidateId === cand.id;

        // Privacy Protected Area Circle (~1000m radius representing approximate locality)
        const circle = new google.maps.Circle({
          strokeColor: isSelected ? "#0D9488" : "#64748B",
          strokeOpacity: 0.8,
          strokeWeight: isSelected ? 2 : 1,
          fillColor: isSelected ? "#14B8A6" : "#94A3B8",
          fillOpacity: isSelected ? 0.35 : 0.2,
          map,
          center: candLatLng,
          radius: 1000,
        });
        circlesRef.current.push(circle);

        const candMarker = new google.maps.Marker({
          position: candLatLng,
          map,
          title: cand.name,
          label: {
            text: cand.name.charAt(0).toUpperCase(),
            color: "#FFFFFF",
            fontSize: "11px",
            fontWeight: "bold",
          },
          icon: {
            path: google.maps.SymbolPath.CIRCLE,
            scale: 12,
            fillColor: isSelected ? "#0F766E" : "#475569",
            fillOpacity: 1,
            strokeColor: "#FFFFFF",
            strokeWeight: 2,
          },
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

    if (hasTargetCoords && markersRef.current.length > 1) {
      map.fitBounds(bounds, 50);
    } else if (hasTargetCoords) {
      map.setCenter(defaultCenter);
      map.setZoom(13);
    }
  }, [mapLoaded, targetLocation, candidates, selectedCandidateId]);

  // Fallback view when Google Maps JS API is unconfigured or failed
  if (mapLoaded === false) {
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
            <MapPin className="w-6 h-6" />
          </div>
          <h4 className="font-heading font-semibold text-gray-900 dark:text-gray-100 text-sm">
            {targetLocation?.label || "Target Locality"}
          </h4>
          <p className="text-xs text-gray-500 dark:text-gray-400 max-w-sm mx-auto">
            {candidates.length > 0
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
      </div>
    );
  }

  return (
    <div className={`relative w-full rounded-2xl overflow-hidden border border-gray-200 dark:border-brand-dark-border shadow-sm ${className}`}>
      <div ref={containerRef} className="w-full h-full" />
      <div className="absolute top-2.5 right-2.5 z-10 pointer-events-none">
        <span className="flex items-center gap-1 text-[11px] font-medium text-teal-800 bg-white/90 backdrop-blur-sm px-2.5 py-1 rounded-full shadow-sm border border-teal-100">
          <Shield className="w-3 h-3 text-brand-primary" />
          Privacy Protected Area
        </span>
      </div>
    </div>
  );
}
