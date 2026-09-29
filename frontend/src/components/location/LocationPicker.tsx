import { useState } from "react";
import { Navigation, ChevronDown, ChevronUp, Check, AlertCircle, Loader2 } from "lucide-react";
import { PlaceAutocomplete } from "./PlaceAutocomplete";
import { getPlaceDetails, reverseGeocodeCoordinates } from "../../services/location";
import type { PlaceAutocompletePrediction } from "../../types/google-location";
import type { LocationCreateOrUpdatePayload } from "../../types/profile";

export interface LocationPickerProps {
  value: LocationCreateOrUpdatePayload;
  onChange: (loc: LocationCreateOrUpdatePayload) => void;
  disabled?: boolean;
}

export function LocationPicker({
  value,
  onChange,
  disabled = false,
}: LocationPickerProps) {
  const [isLocating, setIsLocating] = useState(false);
  const [geoError, setGeoError] = useState<string | null>(null);
  const [showManualFields, setShowManualFields] = useState(false);

  const handleSelectPrediction = async (prediction: PlaceAutocompletePrediction) => {
    try {
      const details = await getPlaceDetails(prediction.place_id);
      onChange({
        city: details.city || prediction.main_text,
        area: details.area || undefined,
        state: details.state || undefined,
        country: details.country || "India",
        latitude: details.latitude != null ? details.latitude : undefined,
        longitude: details.longitude != null ? details.longitude : undefined,
        google_place_id: details.google_place_id || prediction.place_id,
        formatted_address: details.formatted_address || prediction.description,
        postal_code: details.postal_code || undefined,
        location_source: details.location_source || "google_places",
        location_precision: details.location_precision || "locality",
      });
      setGeoError(null);
    } catch (err) {
      // Fallback: use prediction text directly
      onChange({
        city: prediction.main_text,
        area: prediction.secondary_text || undefined,
        country: "India",
        location_source: "manual",
        location_precision: "locality",
      });
    }
  };

  const handleUseCurrentLocation = () => {
    if (!navigator.geolocation) {
      setGeoError("Geolocation is not supported by your browser.");
      return;
    }

    setIsLocating(true);
    setGeoError(null);

    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        try {
          const lat = pos.coords.latitude;
          const lon = pos.coords.longitude;
          const resolved = await reverseGeocodeCoordinates(lat, lon);

          onChange({
            city: resolved.city || "Unknown City",
            area: resolved.area || undefined,
            state: resolved.state || undefined,
            country: resolved.country || "India",
            latitude: lat,
            longitude: lon,
            google_place_id: resolved.google_place_id || undefined,
            formatted_address: resolved.formatted_address || undefined,
            postal_code: resolved.postal_code || undefined,
            location_source: "browser_geolocation",
            location_precision: "rooftop",
          });
        } catch (err) {
          setGeoError("Failed to resolve current coordinates. Please search manually.");
        } finally {
          setIsLocating(false);
        }
      },
      (err) => {
        setIsLocating(false);
        if (err.code === err.PERMISSION_DENIED) {
          setGeoError("Location access was denied. You can search or enter your city manually.");
        } else {
          setGeoError("Could not retrieve current location. Please enter manually.");
        }
      },
      { timeout: 10000, enableHighAccuracy: true }
    );
  };

  const hasLocation = Boolean(value.city);

  return (
    <div className="space-y-3">
      {/* Search Input with Autocomplete */}
      <div>
        <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider mb-1.5">
          Search Location in India
        </label>
        <PlaceAutocomplete
          onSelectPrediction={handleSelectPrediction}
          initialValue={value.formatted_address || [value.area, value.city].filter(Boolean).join(", ")}
          disabled={disabled}
        />
      </div>

      {/* Geolocation Button */}
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={handleUseCurrentLocation}
          disabled={disabled || isLocating}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 dark:border-brand-dark-border bg-white dark:bg-brand-dark-surface hover:bg-gray-50 dark:hover:bg-brand-dark-muted/40 text-gray-700 dark:text-gray-300 transition-colors disabled:opacity-50"
        >
          {isLocating ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin text-brand-primary" />
          ) : (
            <Navigation className="w-3.5 h-3.5 text-brand-primary" />
          )}
          <span>{isLocating ? "Detecting GPS..." : "Use My Current Location"}</span>
        </button>

        <button
          type="button"
          onClick={() => setShowManualFields(!showManualFields)}
          className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 transition-colors"
        >
          <span>{showManualFields ? "Hide manual fields" : "Manual entry"}</span>
          {showManualFields ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>
      </div>

      {geoError && (
        <div className="flex items-center gap-2 p-2.5 rounded-lg bg-amber-50 dark:bg-amber-950/20 text-amber-800 dark:text-amber-300 text-xs border border-amber-200 dark:border-amber-800/40">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{geoError}</span>
        </div>
      )}

      {/* Selected Location Summary Chip */}
      {hasLocation && (
        <div className="p-3 rounded-xl bg-teal-50/70 dark:bg-brand-dark-muted/20 border border-teal-200/60 dark:border-brand-dark-border flex items-center justify-between gap-3 text-xs">
          <div className="flex items-start gap-2.5 min-w-0">
            <div className="w-6 h-6 rounded-full bg-brand-primary/10 dark:bg-brand-primary/20 text-brand-primary flex items-center justify-center shrink-0 mt-0.5">
              <Check className="w-3.5 h-3.5" />
            </div>
            <div className="min-w-0">
              <p className="font-semibold text-gray-900 dark:text-gray-100 truncate">
                {value.formatted_address || [value.area, value.city, value.state].filter(Boolean).join(", ")}
              </p>
              <div className="flex items-center gap-2 mt-0.5 text-[11px] text-gray-500 dark:text-gray-400">
                <span className="capitalize">Source: {value.location_source?.replace("_", " ") || "Manual"}</span>
                {value.latitude != null && value.longitude != null && (
                  <span className="font-mono text-[10px] text-teal-700 dark:text-teal-400">
                    ({value.latitude.toFixed(2)}°, {value.longitude.toFixed(2)}°)
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Location Details Inputs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
        <div>
          <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
            City <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            aria-label="City *"
            value={value.city || ""}
            disabled={disabled}
            onChange={(e) => onChange({ ...value, city: e.target.value, location_source: "manual" })}
            placeholder="e.g. Pune, Bengaluru, Nagpur"
            className="w-full px-3 py-2 bg-white dark:bg-brand-dark-surface border border-gray-300 dark:border-brand-dark-border rounded-lg text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-brand-primary"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
            Area / Neighborhood
          </label>
          <input
            type="text"
            aria-label="Area / Neighborhood"
            value={value.area || ""}
            disabled={disabled}
            onChange={(e) => onChange({ ...value, area: e.target.value })}
            placeholder="e.g. Kothrud, Whitefield, Dharampeth"
            className="w-full px-3 py-2 bg-white dark:bg-brand-dark-surface border border-gray-300 dark:border-brand-dark-border rounded-lg text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-brand-primary"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
            State
          </label>
          <input
            type="text"
            aria-label="State"
            value={value.state || ""}
            disabled={disabled}
            onChange={(e) => onChange({ ...value, state: e.target.value })}
            placeholder="e.g. Maharashtra, Karnataka"
            className="w-full px-3 py-2 bg-white dark:bg-brand-dark-surface border border-gray-300 dark:border-brand-dark-border rounded-lg text-xs text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-brand-primary"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
            Country
          </label>
          <input
            type="text"
            aria-label="Country"
            value={value.country || "India"}
            disabled
            className="w-full px-3 py-2 bg-gray-100 dark:bg-brand-dark-muted/30 border border-gray-200 dark:border-brand-dark-border rounded-lg text-xs text-gray-600 dark:text-gray-400 cursor-not-allowed"
          />
        </div>
      </div>
    </div>
  );
}
