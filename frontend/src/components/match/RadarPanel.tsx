import type { DimensionStatuses, MatchScores } from "@/types/match";
import { Card } from "../ui/Card";
import { Activity, AlertCircle } from "lucide-react";

export interface RadarPanelProps {
  scores?: MatchScores;
  dimensionStatuses?: DimensionStatuses;
  disabled?: boolean;
}

export function RadarPanel({ scores, dimensionStatuses, disabled = false }: RadarPanelProps) {
  const dimensions = [
    {
      key: "semantic",
      label: "Semantic Relevance",
      value: scores?.semantic_score ?? null,
      status: dimensionStatuses?.semantic ?? "ACTIVE",
      desc: "pgvector cosine similarity with request need embedding",
    },
    {
      key: "location",
      label: "Location Proximity",
      value: scores?.location_score ?? null,
      status: dimensionStatuses?.location ?? "ACTIVE",
      desc: "Haversine distance decay from real GPS coordinates",
    },
    {
      key: "experience",
      label: "Experience & Tenure",
      value: scores?.experience_score ?? null,
      status: dimensionStatuses?.experience ?? "ACTIVE",
      desc: "Profile tenure & verified skill proficiencies",
    },
    {
      key: "reputation",
      label: "Community Reputation",
      value: scores?.reputation_score ?? null,
      status: dimensionStatuses?.reputation ?? "UNAVAILABLE",
      desc: "Reviews & peer ratings (Scheduled for Phase 7)",
    },
    {
      key: "availability",
      label: "Live Availability",
      value: scores?.availability_score ?? null,
      status: dimensionStatuses?.availability ?? "UNAVAILABLE",
      desc: "Calendar scheduling engine (Scheduled for Phase 6)",
    },
  ];

  return (
    <Card className="space-y-4">
      <div className="flex items-center gap-2">
        <Activity className="w-5 h-5 text-brand-primary" />
        <h4 className="font-bold font-heading text-gray-900 dark:text-gray-100">
          Match Dimension Analysis
        </h4>
      </div>

      {disabled || !scores ? (
        <div className="py-6 text-center text-xs text-gray-500 dark:text-gray-400 border border-dashed rounded-xl p-4">
          Detailed radar scores will appear once real matches are generated.
        </div>
      ) : (
        <div className="space-y-3.5 pt-2">
          {dimensions.map((dim) => {
            const isUnavailable = dim.status === "UNAVAILABLE" || dim.value === null;

            return (
              <div key={dim.key} className="space-y-1">
                <div className="flex justify-between text-xs items-center">
                  <span className="font-medium text-gray-700 dark:text-gray-300">
                    {dim.label}
                  </span>
                  {isUnavailable ? (
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 font-semibold border border-amber-200 dark:border-amber-900/60 flex items-center gap-1">
                      <AlertCircle className="w-3 h-3" />
                      UNAVAILABLE
                    </span>
                  ) : (
                    <span className="font-mono text-gray-900 dark:text-gray-100 font-bold">
                      {Math.round((dim.value ?? 0) * 100)}%
                    </span>
                  )}
                </div>

                {isUnavailable ? (
                  <div className="w-full bg-gray-100 dark:bg-brand-dark-muted/20 h-2 rounded-full overflow-hidden border border-dashed border-gray-200 dark:border-brand-dark-border" />
                ) : (
                  <div className="w-full bg-gray-100 dark:bg-brand-dark-muted/40 h-2 rounded-full overflow-hidden">
                    <div
                      className="bg-brand-primary h-full rounded-full transition-all duration-300"
                      style={{ width: `${Math.max(0, Math.min(100, (dim.value ?? 0) * 100))}%` }}
                    />
                  </div>
                )}
                <p className="text-[10px] text-gray-400">{dim.desc}</p>
              </div>
            );
          })}

          {scores.final_score != null && (
            <div className="pt-3 border-t border-gray-100 dark:border-brand-dark-border/60 flex items-center justify-between">
              <div>
                <span className="text-sm font-bold text-gray-900 dark:text-gray-100 block">
                  Composite Match Score
                </span>
                <span className="text-[11px] text-gray-400">
                  Mathematically normalized over active dimensions
                </span>
              </div>
              <span className="text-2xl font-extrabold text-brand-primary dark:text-teal-400 font-heading">
                {Math.round(scores.final_score * 100)}%
              </span>
            </div>
          )}
        </div>
      )}
    </Card>
  );
}
