import { useState } from "react";
import { Button } from "@/components/ui/Button";
import type { SavedResource } from "@/types/intelligence";
import { Bookmark, MapPin, Trash2, Star } from "lucide-react";

interface SavedResourcesListProps {
  resources: SavedResource[];
  onDeleteResource: (placeId: string) => Promise<void>;
}

export function SavedResourcesList({
  resources,
  onDeleteResource,
}: SavedResourcesListProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleDelete = async (placeId: string) => {
    setDeletingId(placeId);
    try {
      await onDeleteResource(placeId);
    } finally {
      setDeletingId(null);
    }
  };

  if (resources.length === 0) {
    return (
      <div className="p-8 text-center rounded-2xl border border-dashed border-gray-200 dark:border-brand-dark-border space-y-2">
        <Bookmark className="w-6 h-6 text-gray-400 mx-auto" />
        <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
          No Saved Places Yet
        </h4>
        <p className="text-xs text-gray-500 dark:text-gray-400 max-w-sm mx-auto">
          Bookmark helpful PGs, tiffin centers, or transit points from your recommendations above to keep them accessible here.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100 flex items-center gap-1.5">
          <Bookmark className="w-4 h-4 text-brand-primary" />
          Bookmarked Places for this Request ({resources.length})
        </h4>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {resources.map((res) => (
          <div
            key={res.id}
            className="p-4 rounded-xl border border-gray-100 dark:border-brand-dark-border bg-white dark:bg-brand-dark-surface shadow-xs space-y-2.5"
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-brand-primary dark:text-teal-400">
                  {res.category}
                </span>
                <h5 className="text-sm font-bold text-gray-900 dark:text-gray-100 line-clamp-1">
                  {res.name}
                </h5>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="text-gray-400 hover:text-brand-danger p-1 h-auto"
                onClick={() => handleDelete(res.place_id)}
                disabled={deletingId === res.place_id}
                title="Remove Bookmark"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </Button>
            </div>

            {res.formatted_address && (
              <p className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1 line-clamp-1">
                <MapPin className="w-3 h-3 shrink-0" />
                {res.formatted_address}
              </p>
            )}

            {res.notes && (
              <p className="text-xs text-gray-700 dark:text-gray-300 bg-gray-50 dark:bg-brand-dark-muted/40 p-2 rounded-lg italic">
                "{res.notes}"
              </p>
            )}

            <div className="flex items-center justify-between text-xs text-gray-500 pt-1 border-t border-gray-100 dark:border-brand-dark-border/40">
              {res.rating !== null && res.rating !== undefined ? (
                <span className="font-semibold text-amber-600 dark:text-amber-400 flex items-center gap-1 text-[11px]">
                  <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                  {res.rating.toFixed(1)} {res.user_ratings_total ? `(${res.user_ratings_total} reviews)` : ""}
                </span>
              ) : (
                <span className="text-[11px] text-gray-400">Rating unavailable</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
