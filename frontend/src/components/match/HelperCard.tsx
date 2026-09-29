import type { HelperMatchItem } from "@/types/match";
import { Card } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { MapPin, Sparkles, MessageSquare } from "lucide-react";

export interface HelperCardProps {
  helper?: HelperMatchItem;
}

export function HelperCard({ helper }: HelperCardProps) {
  if (!helper) {
    return (
      <Card className="p-6 border-dashed text-center text-sm text-gray-500 dark:text-gray-400">
        Helper match component will render when real matches are generated.
      </Card>
    );
  }

  return (
    <Card hover className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-teal-100 dark:bg-brand-dark-muted/60 text-brand-primary dark:text-teal-300 flex items-center justify-center font-bold text-lg font-heading">
            {helper.name.charAt(0)}
          </div>
          <div>
            <h4 className="font-bold text-gray-900 dark:text-gray-100 font-heading">
              {helper.name}
            </h4>
            <div className="flex items-center gap-2">
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {helper.headline || "Community Helper"}
              </p>
              {helper.is_available_for_help === false && (
                <span className="text-[10px] bg-gray-100 dark:bg-brand-dark-muted px-1.5 py-0.5 rounded text-gray-500 font-medium">
                  Not accepting requests
                </span>
              )}
            </div>
          </div>
        </div>

        {helper.scores?.final_score != null && (
          <div className="text-right">
            <span className="text-lg font-extrabold text-brand-primary dark:text-teal-400 font-heading">
              {Math.round(helper.scores.final_score * 100)}%
            </span>
            <span className="block text-[10px] text-gray-400 uppercase tracking-wider font-semibold">
              Match Score
            </span>
          </div>
        )}
      </div>

      {(helper.area || helper.city) && (
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-gray-600 dark:text-gray-300">
          <div className="flex items-center gap-1.5">
            <MapPin className="w-3.5 h-3.5 text-brand-primary shrink-0" />
            <span>{[helper.area, helper.city].filter(Boolean).join(", ")}</span>
          </div>
          {helper.distance_km != null && (
            <span className="text-gray-400">({helper.distance_km.toFixed(1)} km away)</span>
          )}
          {helper.route_info?.estimated_travel_time_minutes != null && (
            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-teal-800 dark:text-teal-300 bg-teal-50 dark:bg-brand-dark-muted/40 px-2 py-0.5 rounded-md border border-teal-200/50 dark:border-teal-800/40">
              🚗 ~{Math.round(helper.route_info.estimated_travel_time_minutes)} min drive
            </span>
          )}
        </div>
      )}

      {helper.bio && (
        <p className="text-xs text-gray-600 dark:text-gray-300 line-clamp-2">
          {helper.bio}
        </p>
      )}

      {/* Skills */}
      <div className="flex flex-wrap gap-1">
        {helper.skills.map((skill, idx) => (
          <Badge key={idx} variant="primary" size="sm">
            {skill}
          </Badge>
        ))}
      </div>

      {/* Match Reasons */}
      {helper.reasons && helper.reasons.length > 0 && (
        <div className="p-3 rounded-xl bg-teal-50/60 dark:bg-brand-dark-muted/30 border border-teal-100 dark:border-brand-dark-border text-xs space-y-1">
          <div className="flex items-center gap-1 font-semibold text-brand-primary dark:text-teal-300">
            <Sparkles className="w-3 h-3 text-amber-500" />
            Why this match?
          </div>
          {helper.reasons.map((reason, idx) => (
            <p key={idx} className="text-gray-600 dark:text-gray-300">
              • <strong className="text-gray-800 dark:text-gray-200">{reason.title}:</strong>{" "}
              {reason.explanation}
            </p>
          ))}
        </div>
      )}

      <div className="pt-2 flex justify-end">
        <Button variant="outline" size="sm" leftIcon={<MessageSquare className="w-3.5 h-3.5" />}>
          Connect
        </Button>
      </div>
    </Card>
  );
}
