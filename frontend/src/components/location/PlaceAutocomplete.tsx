import { useState, useEffect, useRef } from "react";
import { Search, MapPin, Loader2, X } from "lucide-react";
import { autocompletePlaces } from "../../services/location";
import type { PlaceAutocompletePrediction } from "../../types/google-location";
import { useDebounce } from "../../hooks/useDebounce";

export interface PlaceAutocompleteProps {
  onSelectPrediction: (prediction: PlaceAutocompletePrediction) => void;
  placeholder?: string;
  initialValue?: string;
  disabled?: boolean;
  biasCoords?: { latitude: number; longitude: number } | null;
}

export function PlaceAutocomplete({
  onSelectPrediction,
  placeholder = "Search area, locality, or city (e.g. Whitefield, Bengaluru)...",
  initialValue = "",
  disabled = false,
  biasCoords,
}: PlaceAutocompleteProps) {
  const [query, setQuery] = useState(initialValue);
  const [predictions, setPredictions] = useState<PlaceAutocompletePrediction[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const debouncedQuery = useDebounce(query, 300);

  useEffect(() => {
    setQuery(initialValue);
  }, [initialValue]);

  useEffect(() => {
    let active = true;

    async function fetchPredictions() {
      const clean = debouncedQuery.trim();
      if (clean.length < 2) {
        setPredictions([]);
        setIsOpen(false);
        return;
      }

      setIsLoading(true);
      try {
        const resp = await autocompletePlaces(
          clean,
          undefined,
          biasCoords?.latitude,
          biasCoords?.longitude
        );
        if (active) {
          setPredictions(resp.predictions || []);
          setIsOpen((resp.predictions || []).length > 0);
        }
      } catch (err) {
        if (active) {
          setPredictions([]);
        }
      } finally {
        if (active) {
          setIsLoading(false);
        }
      }
    }

    fetchPredictions();

    return () => {
      active = false;
    };
  }, [debouncedQuery, biasCoords?.latitude, biasCoords?.longitude]);

  // Click outside listener
  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelect = (item: PlaceAutocompletePrediction) => {
    setQuery(item.description);
    setIsOpen(false);
    onSelectPrediction(item);
  };

  const handleClear = () => {
    setQuery("");
    setPredictions([]);
    setIsOpen(false);
  };

  return (
    <div ref={containerRef} className="relative w-full">
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-gray-400 dark:text-gray-500">
          {isLoading ? (
            <Loader2 className="w-4 h-4 animate-spin text-brand-primary" />
          ) : (
            <Search className="w-4 h-4" />
          )}
        </div>

        <input
          type="text"
          value={query}
          disabled={disabled}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => {
            if (predictions.length > 0) setIsOpen(true);
          }}
          placeholder={placeholder}
          className="w-full pl-10 pr-9 py-2.5 bg-white dark:bg-brand-dark-surface border border-gray-300 dark:border-brand-dark-border rounded-xl text-sm font-semibold text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-brand-primary/40 focus:border-brand-primary transition-colors disabled:opacity-50"
        />

        {query && (
          <button
            type="button"
            onClick={handleClear}
            className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Autocomplete Predictions Dropdown */}
      {isOpen && predictions.length > 0 && (
        <div className="absolute z-50 left-0 right-0 mt-1.5 bg-white dark:bg-brand-dark-surface border border-gray-200 dark:border-brand-dark-border rounded-xl shadow-lg overflow-hidden max-h-72 overflow-y-auto">
          {predictions.some((p, i) =>
            predictions.some((other, j) => i !== j && p.main_text.toLowerCase().trim() === other.main_text.toLowerCase().trim())
          ) && (
            <div className="px-3.5 py-2 bg-amber-50 dark:bg-amber-950/40 border-b border-amber-200 dark:border-amber-800/40 text-[11px] font-medium text-amber-800 dark:text-amber-300">
              Multiple places share this name. Please verify the district/area below before selecting.
            </div>
          )}

          {predictions.map((p) => {
            const isDuplicate = predictions.filter(
              (o) => o.main_text.toLowerCase().trim() === p.main_text.toLowerCase().trim()
            ).length > 1;

            return (
              <button
                key={p.place_id}
                type="button"
                onClick={() => handleSelect(p)}
                className="w-full px-4 py-2.5 text-left flex items-start gap-2.5 hover:bg-gray-50 dark:hover:bg-brand-dark-muted/30 transition-colors border-b last:border-b-0 border-gray-100 dark:border-brand-dark-border/40 group"
              >
                <MapPin className="w-4 h-4 text-brand-primary shrink-0 mt-0.5 group-hover:scale-110 transition-transform" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">
                      {p.main_text}
                    </p>
                    {isDuplicate && (
                      <span className="px-1.5 py-0.5 text-[10px] font-semibold bg-amber-100 dark:bg-amber-900/50 text-amber-800 dark:text-amber-300 rounded border border-amber-200 dark:border-amber-800/50">
                        Ambiguous name
                      </span>
                    )}
                  </div>
                  {p.secondary_text ? (
                    <p className="text-xs text-gray-600 dark:text-gray-300 font-medium truncate mt-0.5">
                      📍 {p.secondary_text}
                    </p>
                  ) : p.description ? (
                    <p className="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
                      {p.description}
                    </p>
                  ) : null}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
