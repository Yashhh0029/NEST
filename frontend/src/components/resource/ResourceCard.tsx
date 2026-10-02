import React from "react";
import {
  MapPin,
  Star,
  ExternalLink,
  Clock,
  Phone,
  Globe,
  Sparkles,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import type { ResourceItem } from "@/types/resource";

interface ResourceCardProps {
  resource: ResourceItem;
  onSelect?: (resource: ResourceItem) => void;
  isSelected?: boolean;
}

export const ResourceCard: React.FC<ResourceCardProps> = ({
  resource,
  onSelect,
  isSelected = false,
}) => {
  // If no maps_url returned by provider, construct safe fallback Google Maps search link
  const mapsDestinationUrl =
    resource.maps_url ||
    `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(
      `${resource.name} ${resource.formatted_address || ""}`
    )}`;

  return (
    <Card
      hover
      className={`space-y-4 transition-all ${
        isSelected
          ? "ring-2 ring-brand-primary shadow-md border-brand-primary"
          : ""
      }`}
      onClick={() => onSelect && onSelect(resource)}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="font-bold text-base sm:text-lg text-gray-950 dark:text-white font-heading">
              {resource.name}
            </h3>
            <Badge variant="primary" size="sm">
              {resource.category_display_name}
            </Badge>
            {resource.price_level && (
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border border-emerald-300/50">
                {resource.price_level}
              </span>
            )}
            {resource.is_open_now !== null && (
              <span
                className={`text-[10px] font-semibold px-2 py-0.5 rounded-full inline-flex items-center gap-1 ${
                  resource.is_open_now
                    ? "bg-emerald-50 dark:bg-emerald-950/40 text-emerald-800 dark:text-emerald-300 border border-emerald-300/50"
                    : "bg-gray-100 dark:bg-brand-dark-muted text-gray-700 dark:text-gray-300"
                }`}
              >
                <Clock className="w-3 h-3" />
                {resource.is_open_now ? "Open Now" : "Closed"}
              </span>
            )}
          </div>

          {resource.formatted_address && (
            <p className="text-xs text-gray-700 dark:text-gray-300 font-medium flex items-start gap-1">
              <MapPin className="w-3.5 h-3.5 text-brand-primary shrink-0 mt-0.5" />
              <span>{resource.formatted_address}</span>
            </p>
          )}
        </div>

        {/* Rating & Distance summary */}
        <div className="text-right shrink-0">
          {resource.distance_km != null && (
            <span className="inline-block text-xs font-bold text-gray-800 dark:text-gray-200 bg-gray-100 dark:bg-brand-dark-muted px-2.5 py-1 rounded-lg">
              {resource.distance_km < 1
                ? `${Math.round(resource.distance_km * 1000)} m away`
                : `${resource.distance_km.toFixed(1)} km away`}
            </span>
          )}

          <div className="mt-1 flex items-center justify-end gap-1 text-xs">
            {resource.rating != null ? (
              <span className="inline-flex items-center gap-1 font-bold text-amber-700 dark:text-amber-400">
                <Star className="w-3.5 h-3.5 fill-amber-500 text-amber-500" />
                {resource.rating.toFixed(1)}
                {resource.review_count != null && (
                  <span className="text-gray-600 dark:text-gray-400 font-medium">
                    ({resource.review_count})
                  </span>
                )}
              </span>
            ) : (
              <span className="text-gray-500 dark:text-gray-400 text-[11px] font-medium">
                Rating unavailable
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Ranking Reasons */}
      {resource.ranking_reasons && resource.ranking_reasons.length > 0 && (
        <div className="p-2.5 rounded-xl bg-teal-50/50 dark:bg-brand-dark-muted/20 border border-teal-100 dark:border-brand-dark-border/50 text-xs text-gray-800 dark:text-gray-200 space-y-1">
          <div className="flex items-center gap-1 font-bold text-brand-primary dark:text-teal-400 text-[11px]">
            <Sparkles className="w-3 h-3 text-amber-500" />
            Why this place?
          </div>
          <p className="line-clamp-2 text-[11px] font-medium text-gray-700 dark:text-gray-300">
            {resource.ranking_reasons.join(" • ")}
          </p>
        </div>
      )}

      {/* Actions */}
      <div className="pt-2 flex flex-wrap items-center justify-between gap-2 border-t border-gray-100 dark:border-brand-dark-border text-xs">
        <div className="flex items-center gap-3 text-gray-700 dark:text-gray-300 font-medium">
          {resource.phone_number && (
            <a
              href={`tel:${resource.phone_number}`}
              className="hover:text-brand-primary flex items-center gap-1 transition-colors"
              title="Call phone number"
            >
              <Phone className="w-3.5 h-3.5" />
              <span>{resource.phone_number}</span>
            </a>
          )}
          {resource.website_url && (
            <a
              href={resource.website_url}
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-brand-primary flex items-center gap-1 transition-colors"
              title="Visit official website"
            >
              <Globe className="w-3.5 h-3.5" />
              <span>Website</span>
            </a>
          )}
        </div>

        <a
          href={mapsDestinationUrl}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
        >
          <Button variant="outline" size="sm" className="gap-1.5">
            <span>Open in Maps</span>
            <ExternalLink className="w-3.5 h-3.5" />
          </Button>
        </a>
      </div>
    </Card>
  );
};
