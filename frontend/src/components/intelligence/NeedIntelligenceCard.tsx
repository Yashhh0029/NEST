import { useState } from "react";
import { Link } from "react-router-dom";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import type { NeedIntelligenceBundle, SavedResourceCreate } from "@/types/intelligence";
import type { ResourceItem } from "@/types/resource";
import {
  Users,
  MessageSquare,
  MapPin,
  Bookmark,
  BookmarkCheck,
  ChevronRight,
  Star,
} from "lucide-react";

interface NeedIntelligenceCardProps {
  bundle: NeedIntelligenceBundle;
  requestId: string;
  savedPlaceIds: Set<string>;
  onSaveResource: (res: SavedResourceCreate) => Promise<void>;
  onConnectHelper: (helperId: string, helperName: string) => void;
}

export function NeedIntelligenceCard({
  bundle,
  savedPlaceIds,
  onSaveResource,
  onConnectHelper,
}: NeedIntelligenceCardProps) {
  const [activeTab, setActiveTab] = useState<"all" | "people" | "community" | "resources">("all");
  const [savingPlaceId, setSavingPlaceId] = useState<string | null>(null);

  const handleSave = async (res: ResourceItem) => {
    setSavingPlaceId(res.google_place_id);
    try {
      await onSaveResource({
        place_id: res.google_place_id,
        name: res.name,
        category: bundle.category,
        formatted_address: res.formatted_address,
        rating: res.rating,
        user_ratings_total: res.review_count,
        latitude: res.latitude,
        longitude: res.longitude,
      });
    } finally {
      setSavingPlaceId(null);
    }
  };

  return (
    <Card className="p-6 space-y-6 border border-gray-200 dark:border-brand-dark-border">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-gray-100 dark:border-brand-dark-border/60 pb-4">
        <div>
          <span className="text-[11px] font-bold uppercase tracking-wider text-brand-primary dark:text-teal-400">
            Requirement Category: {bundle.category}
          </span>
          <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 capitalize">
            {bundle.item}
          </h3>
        </div>

        {/* Tab Filters */}
        <div className="flex items-center gap-1 bg-gray-100 dark:bg-brand-dark-muted p-1 rounded-xl">
          <button
            type="button"
            onClick={() => setActiveTab("all")}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
              activeTab === "all"
                ? "bg-white dark:bg-brand-dark-surface text-gray-900 dark:text-gray-100 shadow-xs"
                : "text-gray-600 dark:text-gray-400 hover:text-gray-900"
            }`}
          >
            All Recommendations
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("people")}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
              activeTab === "people"
                ? "bg-white dark:bg-brand-dark-surface text-gray-900 dark:text-gray-100 shadow-xs"
                : "text-gray-600 dark:text-gray-400 hover:text-gray-900"
            }`}
          >
            People ({bundle.matched_helpers.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("community")}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
              activeTab === "community"
                ? "bg-white dark:bg-brand-dark-surface text-gray-900 dark:text-gray-100 shadow-xs"
                : "text-gray-600 dark:text-gray-400 hover:text-gray-900"
            }`}
          >
            Community ({bundle.community_questions.length})
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("resources")}
            className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all ${
              activeTab === "resources"
                ? "bg-white dark:bg-brand-dark-surface text-gray-900 dark:text-gray-100 shadow-xs"
                : "text-gray-600 dark:text-gray-400 hover:text-gray-900"
            }`}
          >
            Places ({bundle.local_resources.length})
          </button>
        </div>
      </div>

      {/* Grid of 3 Pillars */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 1. PEOPLE PILLAR */}
        {(activeTab === "all" || activeTab === "people") && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5 text-brand-primary" />
                Community Helpers
              </h4>
              <span className="text-[11px] text-gray-400">pgvector matching</span>
            </div>

            {bundle.matched_helpers.length === 0 ? (
              <div className="p-4 rounded-xl border border-dashed border-gray-200 dark:border-brand-dark-border text-center text-xs text-gray-400">
                No matching helpers found for this need yet.
              </div>
            ) : (
              bundle.matched_helpers.map((helper) => (
                <div
                  key={helper.user_id}
                  className="p-3.5 rounded-xl border border-gray-100 dark:border-brand-dark-border bg-gray-50/50 dark:bg-brand-dark-muted/20 space-y-2.5"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h5 className="text-sm font-bold text-gray-900 dark:text-gray-100">
                        {helper.name}
                      </h5>
                      <p className="text-xs text-gray-500 dark:text-gray-400 line-clamp-1">
                        {helper.headline || "Community Member"}
                      </p>
                    </div>
                    <Badge variant="primary" size="sm">
                      {Math.round((helper.scores?.final_score ?? 0) * 100)}% Match
                    </Badge>
                  </div>

                  {/* Factual Explainability Badges */}
                  <div className="flex flex-wrap gap-1.5 text-[11px] text-gray-600 dark:text-gray-400">
                    {helper.distance_km !== null && helper.distance_km !== undefined && (
                      <span className="flex items-center gap-1 bg-white dark:bg-brand-dark-surface px-2 py-0.5 rounded-md border border-gray-200 dark:border-brand-dark-border">
                        <MapPin className="w-3 h-3 text-red-500" />
                        {helper.distance_km} km away
                      </span>
                    )}
                    {helper.scores?.reputation_score !== null && helper.scores?.reputation_score !== undefined ? (
                      <span className="flex items-center gap-1 bg-white dark:bg-brand-dark-surface px-2 py-0.5 rounded-md border border-gray-200 dark:border-brand-dark-border font-semibold text-amber-600 dark:text-amber-400">
                        <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                        {helper.scores.reputation_score.toFixed(1)} score
                      </span>
                    ) : (
                      <span className="text-gray-400 bg-white dark:bg-brand-dark-surface px-2 py-0.5 rounded-md border border-gray-200 dark:border-brand-dark-border text-[10px]">
                        New member
                      </span>
                    )}
                  </div>

                  <Button
                    size="sm"
                    variant="primary"
                    className="w-full text-xs"
                    onClick={() => onConnectHelper(helper.user_id, helper.name)}
                  >
                    Connect with {helper.name.split(" ")[0]}
                  </Button>
                </div>
              ))
            )}
          </div>
        )}

        {/* 2. COMMUNITY PILLAR */}
        {(activeTab === "all" || activeTab === "community") && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider flex items-center gap-1.5">
                <MessageSquare className="w-3.5 h-3.5 text-blue-500" />
                Community Guides
              </h4>
              <span className="text-[11px] text-gray-400">Verified Q&A</span>
            </div>

            {bundle.community_questions.length === 0 ? (
              <div className="p-4 rounded-xl border border-dashed border-gray-200 dark:border-brand-dark-border text-center text-xs text-gray-400">
                No answered community guides for this need yet.
              </div>
            ) : (
              bundle.community_questions.map((item) => (
                <Link
                  key={item.question.id}
                  to={`/community/${item.question.id}`}
                  className="block p-3.5 rounded-xl border border-gray-100 dark:border-brand-dark-border bg-gray-50/50 dark:bg-brand-dark-muted/20 space-y-2 hover:border-brand-primary/40 transition-all"
                >
                  <div className="flex items-start justify-between gap-2">
                    <h5 className="text-xs font-bold text-gray-900 dark:text-gray-100 line-clamp-2">
                      {item.question.title}
                    </h5>
                    {item.question.has_accepted_answer && (
                      <span className="shrink-0 text-[10px] font-bold text-emerald-600 bg-emerald-50 dark:bg-emerald-950/40 px-1.5 py-0.5 rounded">
                        ✓ Accepted
                      </span>
                    )}
                  </div>

                  {item.top_answer && (
                    <p className="text-[11px] text-gray-600 dark:text-gray-400 line-clamp-2 italic">
                      "{item.top_answer.body}"
                    </p>
                  )}

                  <div className="flex items-center justify-between text-[10px] text-gray-400 pt-1">
                    <span>{item.question.area || item.question.city || "Local"}</span>
                    <span className="flex items-center gap-0.5 text-brand-primary dark:text-teal-400 font-semibold">
                      Read Guide <ChevronRight className="w-3 h-3" />
                    </span>
                  </div>
                </Link>
              ))
            )}
          </div>
        )}

        {/* 3. LOCAL RESOURCES PILLAR */}
        {(activeTab === "all" || activeTab === "resources") && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-bold text-gray-700 dark:text-gray-300 uppercase tracking-wider flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-teal-500" />
                Verified Local Places
              </h4>
              <span className="text-[11px] text-gray-400">Google Places</span>
            </div>

            {bundle.local_resources.length === 0 ? (
              <div className="p-4 rounded-xl border border-dashed border-gray-200 dark:border-brand-dark-border text-center text-xs text-gray-400">
                No local places found in this immediate area.
              </div>
            ) : (
              bundle.local_resources.map((res) => {
                const isSaved = savedPlaceIds.has(res.google_place_id);
                return (
                  <div
                    key={res.google_place_id}
                    className="p-3.5 rounded-xl border border-gray-100 dark:border-brand-dark-border bg-gray-50/50 dark:bg-brand-dark-muted/20 space-y-2"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div>
                        <h5 className="text-xs font-bold text-gray-900 dark:text-gray-100 line-clamp-1">
                          {res.name}
                        </h5>
                        <p className="text-[11px] text-gray-500 dark:text-gray-400 line-clamp-1">
                          {res.formatted_address || "Address in locality"}
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleSave(res)}
                        disabled={savingPlaceId === res.google_place_id}
                        className={`p-1.5 rounded-lg border transition-all ${
                          isSaved
                            ? "bg-teal-50 border-teal-200 text-brand-primary dark:bg-teal-950/40 dark:border-teal-800"
                            : "bg-white border-gray-200 text-gray-500 hover:text-brand-primary dark:bg-brand-dark-surface dark:border-brand-dark-border"
                        }`}
                        title={isSaved ? "Saved to Request" : "Bookmark to Request"}
                      >
                        {isSaved ? (
                          <BookmarkCheck className="w-4 h-4 text-brand-primary" />
                        ) : (
                          <Bookmark className="w-4 h-4" />
                        )}
                      </button>
                    </div>

                    <div className="flex items-center justify-between text-[11px] pt-1 border-t border-gray-100 dark:border-brand-dark-border/40">
                      <span className="text-gray-500">
                        {res.distance_km !== null && res.distance_km !== undefined ? `${res.distance_km} km away` : "Nearby"}
                      </span>
                      {res.rating !== null && res.rating !== undefined ? (
                        <span className="font-semibold text-amber-600 dark:text-amber-400 flex items-center gap-1">
                          ★ {res.rating.toFixed(1)} {res.review_count ? `(${res.review_count})` : ""}
                        </span>
                      ) : (
                        <span className="text-gray-400">Rating unavailable</span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        )}
      </div>
    </Card>
  );
}
