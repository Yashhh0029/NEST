import type { ExtractedRequest } from "@/types/request";
import type { LocalPreviewItem } from "@/lib/nlp-preview";
import { Badge } from "../ui/Badge";
import { Sparkles } from "lucide-react";

export interface UnderstandingChipsProps {
  extracted?: ExtractedRequest | null;
  previewItems?: LocalPreviewItem[];
  isPreview?: boolean;
}

export function UnderstandingChips({
  extracted,
  previewItems = [],
  isPreview = false,
}: UnderstandingChipsProps) {
  // If we have authoritative extracted results from backend
  if (extracted) {
    const hasItems =
      extracted.location.city ||
      extracted.location.area ||
      extracted.needs.length > 0 ||
      extracted.budget?.amount != null ||
      extracted.preferences.length > 0;

    if (!hasItems) return null;

    return (
      <div
        aria-live="polite"
        className="space-y-2 p-3.5 rounded-xl bg-teal-50/70 dark:bg-brand-dark-muted/30 border border-teal-100 dark:border-brand-dark-border"
      >
        <div className="flex items-center justify-between text-xs font-semibold text-brand-primary dark:text-teal-300">
          <span className="flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5" />
            What NEST Extracted
          </span>
          {isPreview && (
            <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300">
              Backend Parsed
            </span>
          )}
        </div>

        <div className="flex flex-wrap gap-2 pt-1">
          {/* Location */}
          {extracted.location.area && (
            <Badge variant="primary" icon="📍">
              {extracted.location.area}
            </Badge>
          )}
          {extracted.location.city && (
            <Badge variant="primary" icon="🏙️">
              {extracted.location.city}
            </Badge>
          )}

          {/* Needs */}
          {extracted.needs.map((need, idx) => (
            <Badge key={`need-${idx}`} variant="neutral" icon="🏠">
              {need.item}
            </Badge>
          ))}

          {/* Budget */}
          {extracted.budget?.amount != null && (
            <Badge variant="accent" icon="💰">
              {extracted.budget.operator === "<=" ? "under " : ""}
              ₹{extracted.budget.amount.toLocaleString("en-IN")}
              {extracted.budget.period ? ` / ${extracted.budget.period}` : ""}
            </Badge>
          )}

          {/* Preferences */}
          {extracted.preferences.map((pref, idx) => (
            <Badge key={`pref-${idx}`} variant="success" icon="🌱">
              {pref}
            </Badge>
          ))}

          {/* User Context */}
          {extracted.user_context?.map((ctx, idx) => (
            <Badge key={`ctx-${idx}`} variant="muted" icon="💼">
              {ctx}
            </Badge>
          ))}
        </div>
      </div>
    );
  }

  // Fallback to local instant preview regex items
  if (previewItems.length > 0) {
    return (
      <div
        aria-live="polite"
        className="space-y-2 p-3.5 rounded-xl bg-gray-50 dark:bg-brand-dark-card/50 border border-dashed border-gray-200 dark:border-brand-dark-border"
      >
        <div className="flex items-center justify-between text-xs font-semibold text-gray-500 dark:text-gray-400">
          <span className="flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-amber-500" />
            Live Understanding
          </span>
          <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-gray-200 dark:bg-brand-dark-muted/60 text-gray-600 dark:text-gray-400">
            Preview
          </span>
        </div>

        <div className="flex flex-wrap gap-2 pt-1">
          {previewItems.map((item) => (
            <Badge
              key={item.id}
              variant={
                item.type === "location"
                  ? "primary"
                  : item.type === "budget"
                  ? "accent"
                  : item.type === "preference"
                  ? "success"
                  : "neutral"
              }
              icon={item.icon}
            >
              {item.label}
            </Badge>
          ))}
        </div>
      </div>
    );
  }

  return null;
}
