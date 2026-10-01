import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "../ui/Button";
import { UnderstandingChips } from "./UnderstandingChips";
import { extractLocalPreview, type LocalPreviewItem } from "@/lib/nlp-preview";
import { requestsService } from "@/services/requests";
import { reverseGeocodeCoordinates } from "@/services/location";
import { useDebounce } from "@/hooks/useDebounce";
import { useToast } from "@/hooks/useToast";
import type { ExtractedRequest } from "@/types/request";
import { Send, Sparkles, Navigation, MapPin, Loader2 } from "lucide-react";

interface CurrentGeoLocation {
  city: string;
  area?: string;
  state?: string;
  latitude: number;
  longitude: number;
}

export function RequestBox() {
  const [text, setText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localPreviews, setLocalPreviews] = useState<LocalPreviewItem[]>([]);
  const [backendExtracted, setBackendExtracted] = useState<ExtractedRequest | null>(null);

  // Dual location: Current physical location vs Target destination
  const [currentGeo, setCurrentGeo] = useState<CurrentGeoLocation | null>(null);
  const [isLocating, setIsLocating] = useState(false);
  const [geoError, setGeoError] = useState<string | null>(null);

  const debouncedText = useDebounce(text, 400);
  const navigate = useNavigate();
  const { error: toastError, success: toastSuccess } = useToast();

  // Instant local regex preview
  useEffect(() => {
    if (text.trim().length >= 3) {
      setLocalPreviews(extractLocalPreview(text));
    } else {
      setLocalPreviews([]);
      setBackendExtracted(null);
    }
  }, [text]);

  // Debounced authoritative backend parse call
  useEffect(() => {
    let isCancelled = false;

    if (debouncedText.trim().length >= 10) {
      requestsService
        .parseRequestText(debouncedText)
        .then((res) => {
          if (!isCancelled && res.extracted) {
            setBackendExtracted(res.extracted);
          }
        })
        .catch(() => {
          // If parse fails or offline, local preview remains visible
        });
    } else {
      setBackendExtracted(null);
    }

    return () => {
      isCancelled = true;
    };
  }, [debouncedText]);

  const handleDetectLocation = () => {
    if (!navigator.geolocation) {
      setGeoError("Browser does not support geolocation.");
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
          setCurrentGeo({
            city: resolved.city || "Current City",
            area: resolved.area || undefined,
            state: resolved.state || undefined,
            latitude: lat,
            longitude: lon,
          });
        } catch {
          setCurrentGeo({
            city: "Detected Location",
            latitude: pos.coords.latitude,
            longitude: pos.coords.longitude,
          });
        } finally {
          setIsLocating(false);
        }
      },
      (err) => {
        setIsLocating(false);
        if (err.code === err.PERMISSION_DENIED) {
          setGeoError("Location access was denied. Mention your city in your request.");
        } else {
          setGeoError("Could not retrieve current location.");
        }
      },
      { timeout: 8000, enableHighAccuracy: true }
    );
  };

  const targetCity = backendExtracted?.location?.city || localPreviews.find((p) => p.type === "location")?.label;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanText = text.trim();
    if (!cleanText) {
      toastError("Please enter your request before finding help.");
      return;
    }

    setIsSubmitting(true);
    try {
      const created = await requestsService.createRequest({
        text: cleanText,
        target_city: backendExtracted?.location?.city || undefined,
        target_area: backendExtracted?.location?.area || undefined,
      });
      toastSuccess("Request created successfully! Finding community matches...");
      navigate(`/requests/${created.id}`);
    } catch (err: unknown) {
      const errorMsg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : "Failed to create request. Please check your connection.";
      toastError(typeof errorMsg === "string" ? errorMsg : "Request creation failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="relative rounded-card bg-white dark:bg-brand-dark-card border border-gray-200/80 dark:border-brand-dark-border p-4 md:p-6 shadow-soft focus-within:ring-2 focus-within:ring-brand-primary focus-within:border-brand-primary transition-all">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
          <label
            htmlFor="natural-request-input"
            className="block text-base md:text-lg font-bold font-heading text-gray-900 dark:text-gray-100 flex items-center gap-2"
          >
            <Sparkles className="w-5 h-5 text-amber-500" />
            What do you need help with?
          </label>

          {/* Browser Geolocation Trigger */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleDetectLocation}
              disabled={isLocating}
              className="inline-flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 hover:text-teal-600 dark:hover:text-teal-400 py-1 px-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/80 transition-colors cursor-pointer"
              title="Detect physical current location via browser GPS"
            >
              {isLocating ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin text-brand-primary" />
              ) : (
                <Navigation className="w-3.5 h-3.5 text-brand-primary" />
              )}
              <span>{currentGeo ? `Current: ${currentGeo.city}` : "Detect Current Location (GPS)"}</span>
            </button>
          </div>
        </div>

        <textarea
          id="natural-request-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="I'm moving to Whitefield for my first IT job. I need a PG under ₹10,000 and affordable vegetarian food."
          rows={4}
          className="w-full bg-transparent resize-none border-0 p-0 text-base md:text-lg text-gray-900 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-0 leading-relaxed"
        />

        {/* Dual Location Relocation Journey Preview */}
        {currentGeo && targetCity && (
          <div className="mt-3 py-2 px-3 rounded-xl bg-teal-50/70 dark:bg-teal-950/40 border border-teal-200/80 dark:border-teal-900/60 flex items-center justify-between gap-2 text-xs">
            <div className="flex items-center gap-1.5 text-teal-900 dark:text-teal-200 font-medium">
              <MapPin className="w-4 h-4 text-brand-primary shrink-0" />
              <span>
                <strong>Relocation Journey:</strong> Current: <span className="underline">{currentGeo.city}</span> → Destination: <span className="font-bold underline">{targetCity}</span>
              </span>
            </div>
            <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-teal-100 dark:bg-teal-900/70 text-teal-800 dark:text-teal-200 shrink-0">
              Pre-Arrival Mode
            </span>
          </div>
        )}

        {geoError && (
          <p className="mt-2 text-xs text-amber-600 dark:text-amber-400">
            {geoError}
          </p>
        )}

        {/* Understanding Chips area */}
        <div className="mt-4 pt-4 border-t border-gray-100 dark:border-brand-dark-border/50">
          <UnderstandingChips
            extracted={backendExtracted}
            previewItems={localPreviews}
            isPreview={true}
          />
        </div>

        <div className="mt-4 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Describe naturally: mention location, budget, dietary habits, or commute needs.
          </p>

          <Button
            type="submit"
            isLoading={isSubmitting}
            disabled={!text.trim()}
            size="md"
            rightIcon={<Send className="w-4 h-4" />}
            className="w-full sm:w-auto"
          >
            Find Help
          </Button>
        </div>
      </div>
    </form>
  );
}
