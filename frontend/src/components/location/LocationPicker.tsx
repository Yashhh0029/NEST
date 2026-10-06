import { useState } from "react";
import { Navigation, ChevronDown, ChevronUp, Check, AlertCircle, Loader2, MapPin } from "lucide-react";
import { PlaceAutocomplete } from "./PlaceAutocomplete";
import { GoogleMap } from "./GoogleMap";
import { MapLocationPicker } from "./MapLocationPicker";
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
  const [pendingDetectedLocation, setPendingDetectedLocation] = useState<LocationCreateOrUpdatePayload | null>(null);
  const [gpsAccuracy, setGpsAccuracy] = useState<number | null>(null);
  const [showMapPicker, setShowMapPicker] = useState(false);
  const [showManualFields, setShowManualFields] = useState(
    Boolean(value.city || value.area || value.location_source === "manual")
  );

  const handleSelectPrediction = async (prediction: PlaceAutocompletePrediction) => {
    try {
      const details = await getPlaceDetails(prediction.place_id);
      const displayName = details.name || details.display_name || prediction.main_text;
      const formattedAddress = details.formatted_address || prediction.description;
      onChange({
        city: details.city || prediction.main_text,
        area: details.area || undefined,
        state: details.state || undefined,
        country: details.country || "India",
        latitude: details.latitude != null ? details.latitude : undefined,
        longitude: details.longitude != null ? details.longitude : undefined,
        google_place_id: details.google_place_id || prediction.place_id,
        display_name: displayName,
        formatted_address: formattedAddress,
        postal_code: details.postal_code || undefined,
        private_unit: value.private_unit,
        location_source: details.location_source || "google_places",
        location_precision: details.location_precision || "locality",
      });
      setPendingDetectedLocation(null);
      setGeoError(null);
    } catch (err) {
      // Fallback: use prediction text directly
      onChange({
        city: prediction.main_text,
        area: prediction.secondary_text || undefined,
        display_name: prediction.main_text,
        country: "India",
        private_unit: value.private_unit,
        location_source: "manual",
        location_precision: "locality",
      });
      setPendingDetectedLocation(null);
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
          const accuracy = pos.coords.accuracy ? Math.round(pos.coords.accuracy) : null;
          setGpsAccuracy(accuracy);
          const resolved = await reverseGeocodeCoordinates(lat, lon);

          const resolvedCity = resolved.city || resolved.area || "Selected Location";

          // Require explicit user confirmation before applying detected GPS location
          setPendingDetectedLocation({
            city: resolvedCity,
            area: resolved.area || undefined,
            state: resolved.state || undefined,
            country: resolved.country || "India",
            latitude: lat,
            longitude: lon,
            google_place_id: resolved.google_place_id || undefined,
            formatted_address: resolved.formatted_address || undefined,
            display_name: (resolved.name || resolved.display_name || resolved.area || resolved.city) || undefined,
            postal_code: resolved.postal_code || undefined,
            private_unit: value.private_unit,
            location_source: "browser_geolocation",
            location_precision: resolved.location_precision || "rooftop",
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
  const primaryDisplay = value.display_name || value.area || value.city;
  const secondaryDisplay = value.display_name && value.display_name !== value.area && value.display_name !== value.city
    ? [value.area, value.city, value.state, value.country || "India"].filter(Boolean).join(", ")
    : (value.area
      ? [value.city, value.state, value.country || "India"].filter(Boolean).join(", ")
      : [value.state, value.country || "India"].filter(Boolean).join(", "));

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
          biasCoords={
            value.latitude != null && value.longitude != null
              ? { latitude: value.latitude, longitude: value.longitude }
              : null
          }
        />
      </div>

      {/* Geolocation & Map Picker Buttons */}
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
          data-testid="pick-on-map-button"
          onClick={() => setShowMapPicker((prev) => !prev)}
          disabled={disabled}
          className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-all disabled:opacity-50 cursor-pointer ${
            showMapPicker
              ? "border-teal-600 bg-teal-50 dark:bg-brand-dark-surface text-brand-primary dark:text-teal-300 ring-1 ring-teal-500 shadow-xs"
              : "border-gray-200 dark:border-brand-dark-border bg-white dark:bg-brand-dark-surface hover:bg-gray-50 dark:hover:bg-brand-dark-muted/40 text-gray-700 dark:text-gray-300"
          }`}
        >
          <MapPin className="w-3.5 h-3.5 text-brand-primary" />
          <span>{showMapPicker ? "Close Map" : "Pick on Map"}</span>
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

      {/* Interactive Map Location Picker */}
      {showMapPicker && (
        <MapLocationPicker
          initialLocation={{
            latitude: value.latitude,
            longitude: value.longitude,
            city: value.city,
            area: value.area,
          }}
          onConfirm={(picked) => {
            onChange({
              city: picked.city,
              area: picked.area,
              state: picked.state,
              country: picked.country || "India",
              latitude: picked.latitude,
              longitude: picked.longitude,
              google_place_id: picked.google_place_id,
              display_name: picked.display_name,
              formatted_address: picked.formatted_address,
              postal_code: picked.postal_code,
              private_unit: value.private_unit,
              location_source: picked.location_source,
              location_precision: picked.location_precision,
            });
            setShowMapPicker(false);
          }}
          onCancel={() => setShowMapPicker(false)}
        />
      )}

      {geoError && (
        <div className="flex items-center gap-2 p-2.5 rounded-lg bg-amber-50 dark:bg-amber-950/20 text-amber-800 dark:text-amber-300 text-xs border border-amber-200 dark:border-amber-800/40">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{geoError}</span>
        </div>
      )}

      {/* Explicit Confirmation Dialog for Current GPS Detected Location */}
      {pendingDetectedLocation && (
        <div className="p-4 rounded-xl border border-teal-300 dark:border-teal-700 bg-teal-50/90 dark:bg-brand-dark-card space-y-3 shadow-sm animate-fade-in">
          <div className="flex items-center gap-2">
            <Navigation className="w-4 h-4 text-brand-primary animate-pulse" />
            <h4 className="text-xs font-bold uppercase tracking-wider text-teal-900 dark:text-teal-200">
              Current Location Detected via Device GPS
            </h4>
          </div>
          <div className="text-xs space-y-1.5 text-gray-800 dark:text-gray-200 bg-white dark:bg-brand-dark-surface p-3 rounded-lg border border-teal-200 dark:border-teal-800">
            <p className="font-bold text-sm text-gray-900 dark:text-white">
              📍 {pendingDetectedLocation.display_name || pendingDetectedLocation.area || pendingDetectedLocation.city}
            </p>
            {pendingDetectedLocation.formatted_address && (
              <p className="text-xs text-gray-600 dark:text-gray-400">
                {pendingDetectedLocation.formatted_address}
              </p>
            )}
            <div className="flex items-center gap-3 pt-1 text-[11px] text-gray-600 dark:text-gray-300 font-mono flex-wrap">
              {gpsAccuracy != null && (
                <span className="font-semibold text-teal-800 dark:text-teal-300">
                  Accuracy: ±{gpsAccuracy} m
                </span>
              )}
              {pendingDetectedLocation.latitude != null && (
                <span>
                  Coordinates: {pendingDetectedLocation.latitude.toFixed(6)}, {pendingDetectedLocation.longitude?.toFixed(6)}
                </span>
              )}
              <span>City: {pendingDetectedLocation.city}</span>
              {pendingDetectedLocation.area && <span>Area: {pendingDetectedLocation.area}</span>}
              {pendingDetectedLocation.postal_code && <span>PIN: {pendingDetectedLocation.postal_code}</span>}
            </div>
          </div>
          <div className="flex items-center gap-2 pt-0.5">
            <button
              type="button"
              onClick={() => {
                onChange(pendingDetectedLocation);
                setPendingDetectedLocation(null);
              }}
              className="px-3.5 py-1.5 text-xs font-bold rounded-lg bg-brand-primary text-white hover:bg-brand-primary/90 transition-colors shadow-sm"
            >
              Use this location
            </button>
            <button
              type="button"
              onClick={() => setPendingDetectedLocation(null)}
              className="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-300 dark:border-brand-dark-border text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-brand-dark-muted/40 transition-colors"
            >
              Change / Cancel
            </button>
          </div>
        </div>
      )}

      {/* Selected Location Summary Chip */}
      {hasLocation && (
        <div className="p-3.5 rounded-xl bg-teal-50/80 dark:bg-brand-dark-card border border-teal-200/80 dark:border-brand-dark-border flex items-center justify-between gap-3 text-xs shadow-sm">
          <div className="flex items-start gap-2.5 min-w-0">
            <div className="w-6 h-6 rounded-full bg-brand-primary/10 dark:bg-brand-primary/20 text-brand-primary flex items-center justify-center shrink-0 mt-0.5">
              <Check className="w-3.5 h-3.5" />
            </div>
            <div className="min-w-0">
              <p className="font-bold text-gray-900 dark:text-gray-100 truncate text-sm">
                {primaryDisplay}
                {secondaryDisplay && (
                  <span className="text-xs font-normal text-gray-600 dark:text-gray-400 ml-1.5">
                    • {secondaryDisplay}
                  </span>
                )}
              </p>
              <div className="flex items-center gap-2 mt-0.5 text-[11px] text-gray-600 dark:text-gray-300 flex-wrap">
                <span className="capitalize font-medium">Source: {value.location_source?.replace("_", " ") || "Manual"}</span>
                <span className="capitalize font-medium px-1.5 py-0.2 rounded bg-teal-100/70 dark:bg-teal-900/30 text-teal-800 dark:text-teal-300 text-[10px]">
                  Precision: {value.location_precision || "locality"}
                </span>
                {value.latitude != null && value.longitude != null && (
                  <span className="font-mono text-[10px] text-teal-800 dark:text-teal-300 font-semibold">
                    ({value.latitude.toFixed(4)}°, {value.longitude.toFixed(4)}°)
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Exact Selected Google Place Identity */}
      {(value.display_name || value.google_place_id) && (
        <div className="p-3.5 rounded-xl bg-teal-50/50 dark:bg-brand-dark-card border border-teal-200 dark:border-teal-800/60 space-y-2.5">
          <div className="flex items-center justify-between gap-1 flex-wrap">
            <span className="text-xs font-bold text-teal-800 dark:text-teal-300 flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5 text-brand-primary shrink-0" />
              Preserved Google Place Identity
            </span>
            {value.google_place_id && (
              <span className="text-[10px] font-mono text-gray-500 dark:text-gray-400 truncate max-w-[150px]">
                ID: {value.google_place_id.slice(0, 14)}...
              </span>
            )}
          </div>
          <div>
            <label className="block text-xs font-bold text-gray-800 dark:text-gray-200 mb-1">
              Selected Place / Building / Society Name
            </label>
            <input
              type="text"
              aria-label="Selected Place Name"
              value={value.display_name || ""}
              disabled={disabled}
              onChange={(e) => onChange({ ...value, display_name: e.target.value })}
              placeholder="e.g. Megapolis Mystic, Hinjewadi"
              className="w-full px-3 py-2 bg-white dark:bg-brand-dark-surface border border-teal-300 dark:border-teal-700/60 rounded-lg text-sm font-semibold text-gray-900 dark:text-gray-100 placeholder:text-gray-400 focus:outline-none focus:ring-1 focus:ring-brand-primary"
            />
          </div>
          {value.formatted_address && (
            <div>
              <label className="block text-[11px] font-medium text-gray-600 dark:text-gray-400 mb-0.5">
                Full Formatted Address
              </label>
              <input
                type="text"
                aria-label="Formatted Address"
                value={value.formatted_address || ""}
                disabled={disabled}
                onChange={(e) => onChange({ ...value, formatted_address: e.target.value })}
                className="w-full px-3 py-1.5 bg-white dark:bg-brand-dark-surface border border-gray-300 dark:border-brand-dark-border rounded-lg text-xs font-medium text-gray-800 dark:text-gray-200 placeholder:text-gray-400 focus:outline-none focus:ring-1 focus:ring-brand-primary"
              />
            </div>
          )}
        </div>
      )}

      {/* Live Google Map Preview with Pin */}
      {value.latitude != null && value.longitude != null && (
        <div className="rounded-xl overflow-hidden border border-gray-200 dark:border-brand-dark-border shadow-sm">
          <GoogleMap
            targetLocation={{
              latitude: value.latitude,
              longitude: value.longitude,
              label: value.display_name || [value.area, value.city].filter(Boolean).join(", "),
            }}
            className="h-44 sm:h-52 w-full"
          />
        </div>
      )}

      {/* Location Details Inputs (Shown only when manual entry toggled) */}
      {showManualFields && (
        <div className="space-y-3 pt-1 border-t border-gray-100 dark:border-brand-dark-border/40">
          <p className="text-[11px] text-amber-700 dark:text-amber-400">
            For accurate distance calculations and nearby matching, please select your location from the search bar above.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-bold text-gray-800 dark:text-gray-200 mb-1">
                City <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                aria-label="City *"
                value={value.city || ""}
                disabled={disabled}
                onChange={(e) => onChange({ ...value, city: e.target.value, location_source: "manual" })}
                placeholder="e.g. Pune, Bengaluru, Nagpur"
                className="w-full px-3 py-2 bg-white dark:bg-brand-dark-card border border-gray-300 dark:border-brand-dark-border rounded-lg text-sm font-semibold text-gray-900 dark:text-gray-100 placeholder:text-gray-400 focus:outline-none focus:ring-1 focus:ring-brand-primary"
              />
            </div>

            <div>
              <label className="block text-xs font-bold text-gray-800 dark:text-gray-200 mb-1">
                Area / Neighborhood
              </label>
              <input
                type="text"
                aria-label="Area / Neighborhood"
                value={value.area || ""}
                disabled={disabled}
                onChange={(e) => onChange({ ...value, area: e.target.value })}
                placeholder="e.g. Kothrud, Whitefield, Dharampeth"
                className="w-full px-3 py-2 bg-white dark:bg-brand-dark-card border border-gray-300 dark:border-brand-dark-border rounded-lg text-sm font-semibold text-gray-900 dark:text-gray-100 placeholder:text-gray-400 focus:outline-none focus:ring-1 focus:ring-brand-primary"
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
                className="w-full px-3 py-2 bg-white dark:bg-brand-dark-card border border-gray-300 dark:border-brand-dark-border rounded-lg text-xs font-medium text-gray-900 dark:text-gray-100 placeholder:text-gray-400 focus:outline-none focus:ring-1 focus:ring-brand-primary"
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
                className="w-full px-3 py-2 bg-gray-100 dark:bg-brand-dark-muted/40 border border-gray-200 dark:border-brand-dark-border rounded-lg text-xs font-medium text-gray-700 dark:text-gray-300 cursor-not-allowed"
              />
            </div>
          </div>
        </div>
      )}

      {/* Optional Private Unit / Flat Input */}
      <div>
        <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
          Flat / House / Suite <span className="text-[10px] text-gray-500 font-normal">(Private — not shared with others)</span>
        </label>
        <input
          type="text"
          aria-label="Private Unit"
          value={value.private_unit || ""}
          disabled={disabled}
          onChange={(e) => onChange({ ...value, private_unit: e.target.value })}
          placeholder="e.g. Flat 402, Building B (Optional, kept private)"
          className="w-full px-3 py-2 bg-white dark:bg-brand-dark-card border border-gray-300 dark:border-brand-dark-border rounded-lg text-xs font-medium text-gray-900 dark:text-gray-100 placeholder:text-gray-400 focus:outline-none focus:ring-1 focus:ring-brand-primary"
        />
      </div>
    </div>
  );
}
