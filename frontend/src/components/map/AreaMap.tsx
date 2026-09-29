import { Card } from "../ui/Card";
import { MapPin, Shield } from "lucide-react";

export interface AreaMapProps {
  centerLat?: number | null;
  centerLng?: number | null;
  areaName?: string;
  cityName?: string;
}

export function AreaMap({
  centerLat,
  centerLng,
  areaName,
  cityName,
}: AreaMapProps) {
  const hasCoordinates = centerLat != null && centerLng != null;

  return (
    <Card className="space-y-3">
      <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
        <span className="flex items-center gap-1.5 font-semibold text-gray-700 dark:text-gray-300">
          <MapPin className="w-4 h-4 text-brand-primary" />
          Approximate Neighborhood Area
        </span>
        <span className="flex items-center gap-1 text-[11px] text-teal-700 dark:text-teal-400 bg-teal-50 dark:bg-brand-dark-muted/40 px-2 py-0.5 rounded-full">
          <Shield className="w-3 h-3" />
          Privacy Protected
        </span>
      </div>

      <div className="relative w-full h-48 sm:h-64 rounded-xl bg-teal-50/50 dark:bg-brand-dark-muted/20 border border-gray-200 dark:border-brand-dark-border flex flex-col items-center justify-center text-center p-4 overflow-hidden">
        {/* Subtle grid pattern background */}
        <div
          className="absolute inset-0 opacity-15"
          style={{
            backgroundImage:
              "radial-gradient(#0F766E 1px, transparent 1px), radial-gradient(#0F766E 1px, transparent 1px)",
            backgroundSize: "20px 20px",
            backgroundPosition: "0 0, 10px 10px",
          }}
        />

        <div className="relative z-10 space-y-2 max-w-xs">
          <div className="w-12 h-12 rounded-full bg-brand-primary/10 dark:bg-brand-primary/20 text-brand-primary dark:text-teal-300 mx-auto flex items-center justify-center animate-pulse">
            <MapPin className="w-6 h-6" />
          </div>

          <h4 className="font-heading font-bold text-gray-900 dark:text-gray-100 text-sm">
            {[areaName, cityName].filter(Boolean).join(", ") || "Location Preview"}
          </h4>

          {hasCoordinates ? (
            <p className="text-xs text-gray-500 dark:text-gray-400 font-mono">
              Center: {centerLat.toFixed(3)}, {centerLng.toFixed(3)}
            </p>
          ) : (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Exact addresses are never plotted to protect user security. Leaflet maps will display 2-5km radius boundaries.
            </p>
          )}
        </div>
      </div>
    </Card>
  );
}
