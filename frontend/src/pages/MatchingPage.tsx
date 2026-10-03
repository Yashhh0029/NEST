import { useState, useEffect, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { matchingService } from "@/services/matching";
import { listConnections, createConnection } from "@/services/connections";
import type { ConnectionItem } from "@/types/connection";
import { useToast } from "@/hooks/useToast";
import type {
  HelperMatchItem,
  MatchingResultResponse,
  MatchScoreWeights,
} from "@/types/match";
import { WeightSliders } from "@/components/match/WeightSliders";
import { RadarPanel } from "@/components/match/RadarPanel";
import { HelperCard } from "@/components/match/HelperCard";
import { GoogleMap } from "@/components/location/GoogleMap";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ArrowLeft, Sparkles, Loader2, Users, Sliders, Compass } from "lucide-react";

const DEFAULT_WEIGHTS: MatchScoreWeights = {
  semantic: 0.40,
  location: 0.25,
  experience: 0.15,
  reputation: 0.10,
  availability: 0.10,
};

export function MatchingPage() {
  const { requestId } = useParams<{ requestId: string }>();
  const { success: toastSuccess, error: toastError } = useToast();

  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<MatchingResultResponse | null>(null);
  const [selectedHelper, setSelectedHelper] = useState<HelperMatchItem | null>(null);
  const [weights, setWeights] = useState<MatchScoreWeights>(DEFAULT_WEIGHTS);
  const [isRecalculating, setIsRecalculating] = useState<boolean>(false);
  const [connections, setConnections] = useState<ConnectionItem[]>([]);
  const [connectingHelperId, setConnectingHelperId] = useState<string | null>(null);

  const fetchConnections = useCallback(async () => {
    try {
      const res = await listConnections({ role: "requester" });
      setConnections(res.connections || []);
    } catch {
      // Non-critical background fetch failure
    }
  }, []);

  useEffect(() => {
    fetchConnections();
  }, [fetchConnections]);

  const handleConnect = async (helperId: string) => {
    if (!requestId) return;
    setConnectingHelperId(helperId);
    try {
      const newConn = await createConnection({
        request_id: requestId,
        helper_id: helperId,
      });
      setConnections((prev) => [...prev, newConn]);
      toastSuccess("Connection request sent to helper!");
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response
              ?.data?.detail
          : null;
      toastError(msg || "Failed to send connection request.");
    } finally {
      setConnectingHelperId(null);
    }
  };

  const fetchMatches = useCallback(
    async (weightsToUse: MatchScoreWeights, isInitial = false) => {
      if (!requestId) return;
      if (isInitial) setLoading(true);
      else setIsRecalculating(true);
      setError(null);

      try {
        const res = await matchingService.findMatches({
          request_id: requestId,
          weights: weightsToUse,
          limit: 10,
          max_distance_km: 4.0,
        });
        setData(res);
        if (res.matches.length > 0) {
          // Keep current selection if still present in matches, else select top match
          setSelectedHelper((prev) => {
            if (prev) {
              const stillPresent = res.matches.find((m) => m.user_id === prev.user_id);
              if (stillPresent) return stillPresent;
            }
            return res.matches[0];
          });
        } else {
          setSelectedHelper(null);
        }
      } catch (err: unknown) {
        const msg =
          err && typeof err === "object" && "response" in err
            ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
            : null;
        setError(msg || "Failed to load matching candidates. Ensure this request exists and belongs to you.");
      } finally {
        setLoading(false);
        setIsRecalculating(false);
      }
    },
    [requestId]
  );

  useEffect(() => {
    fetchMatches(DEFAULT_WEIGHTS, true);
  }, [fetchMatches]);

  const handleWeightsChange = (newWeights: MatchScoreWeights) => {
    setWeights(newWeights);
    fetchMatches(newWeights, false);
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto py-2 sm:py-6">
      <div className="flex items-center justify-between">
        <Link
          to={requestId ? `/requests/${requestId}` : "/requests"}
          className="text-xs font-semibold text-brand-primary dark:text-teal-400 flex items-center gap-1 hover:underline min-h-[44px]"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Request
        </Link>
        {isRecalculating && (
          <span className="text-xs text-brand-primary dark:text-teal-400 flex items-center gap-1 font-medium animate-pulse">
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
            Recalculating pgvector & location scores...
          </span>
        )}
      </div>

      {/* Header Banner */}
      <div className="space-y-1">
        <div className="flex items-center gap-2">
          <Sparkles className="w-6 h-6 text-brand-primary dark:text-teal-400" />
          <h1 className="text-2xl font-extrabold font-heading text-gray-900 dark:text-gray-100">
            Hybrid Helper Matches
          </h1>
        </div>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Ranked using PostgreSQL pgvector cosine similarity, real GPS coordinates, and profile tenure.
        </p>
      </div>

      {/* Local Resources Discovery Banner */}
      {requestId && (
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-4 rounded-xl border border-teal-200 dark:border-teal-900/60 bg-teal-50/50 dark:bg-teal-950/20">
          <div className="flex items-start sm:items-center gap-3">
            <div className="p-2 rounded-lg bg-teal-100 dark:bg-teal-900/50 text-brand-primary dark:text-teal-400 shrink-0">
              <Compass className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100">
                Looking for nearby places & services?
              </h4>
              <p className="text-xs text-gray-600 dark:text-gray-400">
                Discover real PGs, food, healthcare, transit, and more around this request&apos;s destination.
              </p>
            </div>
          </div>
          <Link
            to={`/resources?request_id=${requestId}`}
            className="shrink-0 px-4 py-2 text-xs font-semibold rounded-lg bg-brand-primary text-white hover:bg-brand-primary/90 transition shadow-sm inline-flex items-center gap-1.5 min-h-[36px]"
          >
            <Compass className="w-3.5 h-3.5" />
            Discover Local Resources
          </Link>
        </div>
      )}

      {loading ? (
        <Card className="p-12 text-center space-y-4">
          <Loader2 className="w-8 h-8 text-brand-primary animate-spin mx-auto" />
          <p className="text-sm text-gray-600 dark:text-gray-300">
            Evaluating database candidates via pgvector cosine distance...
          </p>
        </Card>
      ) : error ? (
        <Card className="p-8 text-center space-y-3 border-red-200 dark:border-red-900/40 bg-red-50/50 dark:bg-red-950/20">
          <p className="text-sm font-semibold text-red-700 dark:text-red-400">{error}</p>
          <button
            onClick={() => fetchMatches(weights, true)}
            className="text-xs text-brand-primary font-bold hover:underline"
          >
            Retry Matching Query
          </button>
        </Card>
      ) : (
        <>
          {/* Controls: Weight Sliders & Radar Panel */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <WeightSliders
              initialWeights={weights}
              onWeightsChange={handleWeightsChange}
              disabled={isRecalculating}
            />
            <RadarPanel
              scores={selectedHelper?.scores}
              dimensionStatuses={selectedHelper?.dimension_statuses}
              disabled={!selectedHelper}
            />
          </div>

          {/* Google Maps Geographic Distribution */}
          {data && (
            <GoogleMap
              targetLocation={{
                latitude: data.target_location?.latitude,
                longitude: data.target_location?.longitude,
                label:
                  [data.target_location?.area, data.target_location?.city].filter(Boolean).join(", ") ||
                  "Target Destination",
              }}
              candidates={data.matches.map((m) => ({
                id: m.user_id,
                name: m.name,
                approximateLatitude: m.approximate_latitude,
                approximateLongitude: m.approximate_longitude,
                area: m.area,
                city: m.city,
                distanceKm: m.distance_km,
                score: m.scores.final_score,
              }))}
              selectedCandidateId={selectedHelper?.user_id}
              onSelectCandidate={(id) => {
                const found = data.matches.find((m) => m.user_id === id);
                if (found) setSelectedHelper(found);
              }}
            />
          )}

          {/* Results Listing */}
          <div className="space-y-4 pt-4 border-t border-gray-100 dark:border-brand-dark-border/60">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Users className="w-5 h-5 text-brand-primary" />
                <h3 className="text-lg font-bold font-heading text-gray-900 dark:text-gray-100">
                  Recommended Helpers ({data?.matches.length ?? 0})
                </h3>
              </div>
              {data && (
                <span className="text-xs text-gray-400">
                  {data.total_candidates_evaluated} candidates evaluated
                </span>
              )}
            </div>

            {data?.matches.length === 0 ? (
              <EmptyState
                icon={<Sliders className="w-8 h-8 text-gray-400" />}
                title="No Community Helpers Found Yet"
                description="Currently no other users in the database match your criteria. When community helpers in your area register with matching skills, they will appear here automatically."
              />
            ) : (
              <div className="grid grid-cols-1 gap-4">
                {data?.matches.map((helper) => {
                  const isSelected = selectedHelper?.user_id === helper.user_id;
                  const existingConn = connections.find(
                    (c) =>
                      c.helper_id === helper.user_id &&
                      (c.request_id === requestId ||
                        c.status === "ACCEPTED" ||
                        c.status === "PENDING")
                  );
                  const connStatus = existingConn?.status || "IDLE";

                  return (
                    <div
                      key={helper.user_id}
                      onClick={() => setSelectedHelper(helper)}
                      className={`cursor-pointer rounded-2xl transition-all ${
                        isSelected
                          ? "ring-2 ring-brand-primary shadow-md"
                          : "hover:opacity-90"
                      }`}
                    >
                      <HelperCard
                        helper={helper}
                        requestId={requestId}
                        connectionStatus={connStatus}
                        onConnect={handleConnect}
                        isConnecting={connectingHelperId === helper.user_id}
                      />
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
