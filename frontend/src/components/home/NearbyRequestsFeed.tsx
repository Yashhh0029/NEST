import { useState } from "react";
import { Link } from "react-router-dom";
import { requestsService } from "@/services/requests";
import { createConnection } from "@/services/connections";
import { refreshCoordinator } from "@/services/refreshCoordinator";
import { useAutoRefresh } from "@/hooks/useAutoRefresh";
import { RefreshStatus } from "@/components/common/RefreshStatus";
import { useToast } from "@/hooks/useToast";
import type { NearbyRequestItem } from "@/types/request";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Skeleton } from "@/components/ui/Skeleton";
import { Stagger, StaggerItem } from "@/components/motion";
import {
  MapPin,
  IndianRupee,
  HeartHandshake,
  CheckCircle2,
  Calendar,
  Send,
  Loader2,
  Compass,
  Sparkles,
  AlertCircle,
} from "lucide-react";

export function NearbyRequestsFeed() {
  const [offerReq, setOfferReq] = useState<NearbyRequestItem | null>(null);
  const [initialMessage, setInitialMessage] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { success, error } = useToast();

  const {
    data: requests = [],
    isLoading: loading,
    isRefreshing,
    isOffline,
    error: refreshError,
    lastUpdated,
    newItemsCount,
    applyNewItems,
    refreshNow,
  } = useAutoRefresh<NearbyRequestItem[]>({
    queryKey: "nearby_requests",
    fetchFn: (signal) => requestsService.getNearbyRequests(undefined, signal),
    interval: 45000, // 45s smart auto-refresh
    scopes: ["nearby_requests", "requests"],
    stageNewItems: true,
    detectNewItems: (prev, next) => {
      const prevIds = new Set(prev.map((r) => r.id));
      return next.filter((r) => !prevIds.has(r.id)).length;
    },
  });

  const handleSendOffer = async () => {
    if (!offerReq) return;
    setIsSubmitting(true);
    try {
      await createConnection({
        request_id: offerReq.id,
        helper_id: "", // Current helper is inferred by backend
        initial_message: initialMessage.trim() || undefined,
      });
      success(`You offered to help ${offerReq.requester_name}. They have been notified.`, "Offer Sent!");
      setOfferReq(null);
      setInitialMessage("");
      // Scoped instant invalidation
      refreshCoordinator.invalidate(["connections", "nearby_requests", "notifications"]);
      await refreshNow();
    } catch (err: any) {
      error(err.response?.data?.detail || "Please try again.", "Could not send offer");
    } finally {
      setIsSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-6 w-48 rounded-lg" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Skeleton className="h-44 rounded-2xl" />
          <Skeleton className="h-44 rounded-2xl" />
        </div>
      </div>
    );
  }

  const isLocationRequired = Boolean(
    refreshError &&
      typeof refreshError === "object" &&
      "response" in refreshError &&
      ((refreshError as any).response?.status === 400 || (refreshError as any).response?.status === 403) &&
      String((refreshError as any).response?.data?.detail || "").toLowerCase().includes("location")
  );

  if (isLocationRequired) {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-teal-100 dark:bg-teal-950/80 text-teal-700 dark:text-teal-300">
              <MapPin className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-lg font-bold font-heading text-slate-900 dark:text-white">
                Help Requests Near You
              </h2>
            </div>
          </div>
        </div>

        <Card className="p-8 text-center space-y-4 rounded-3xl border-teal-200/70 dark:border-teal-900/40 bg-teal-50/30 dark:bg-teal-950/20 backdrop-blur-sm">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-teal-100 dark:bg-teal-900/60 text-teal-700 dark:text-teal-300 flex items-center justify-center font-bold text-xl shadow-sm">
            <MapPin className="w-7 h-7" />
          </div>
          <div className="space-y-1.5 max-w-md mx-auto">
            <h3 className="text-base font-bold font-heading text-slate-900 dark:text-white">
              Set Up Your Location to Discover Requests
            </h3>
            <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
              To discover open newcomer requests in your neighborhood and ensure relevant, privacy-safe community matching, please configure your primary profile location.
            </p>
          </div>
          <div className="pt-2">
            <Link to="/profile/edit#location">
              <Button size="sm" variant="primary" className="gap-2">
                <MapPin className="w-3.5 h-3.5" />
                <span>Configure Profile Location</span>
              </Button>
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  // API FAILURE STATE (when initial load failed or no cached data exists)
  if (refreshError && requests.length === 0) {
    const errorMsg =
      (refreshError as any).response?.data?.detail ||
      (refreshError as any).message ||
      "We encountered an issue retrieving open requests in your area. Please retry.";

    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-teal-100 dark:bg-teal-950/80 text-teal-700 dark:text-teal-300">
              <HeartHandshake className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-lg font-bold font-heading text-slate-900 dark:text-white">
                Help Requests Near You
              </h2>
            </div>
          </div>
          <RefreshStatus
            lastUpdated={lastUpdated}
            isRefreshing={isRefreshing}
            isOffline={isOffline}
            error={refreshError}
            onRefresh={refreshNow}
          />
        </div>

        <Card className="p-8 text-center space-y-4 rounded-3xl border-rose-200/80 dark:border-rose-900/40 bg-rose-50/30 dark:bg-rose-950/20 backdrop-blur-sm">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-rose-100 dark:bg-rose-900/60 text-rose-600 dark:text-rose-400 flex items-center justify-center font-bold text-xl shadow-xs">
            <AlertCircle className="w-7 h-7" />
          </div>
          <div className="space-y-1.5 max-w-md mx-auto">
            <h3 className="text-base font-bold font-heading text-slate-900 dark:text-white">
              Couldn't Load Requests
            </h3>
            <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
              {errorMsg}
            </p>
          </div>
          <div className="pt-2">
            <Button
              variant="primary"
              size="sm"
              onClick={refreshNow}
              disabled={isRefreshing}
              className="gap-2"
            >
              {isRefreshing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
              <span>{isRefreshing ? "Retrying…" : "Retry Loading Requests"}</span>
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  // SUCCESS WITH ZERO RESULTS (strictly when API succeeded and returned 0 items)
  if (requests.length === 0) {
    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-1.5 rounded-lg bg-teal-100 dark:bg-teal-950/80 text-teal-700 dark:text-teal-300">
              <HeartHandshake className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-lg font-bold font-heading text-slate-900 dark:text-white">
                Help Requests Near You
              </h2>
            </div>
          </div>
          <RefreshStatus
            lastUpdated={lastUpdated}
            isRefreshing={isRefreshing}
            isOffline={isOffline}
            error={refreshError}
            onRefresh={refreshNow}
          />
        </div>

        <Card className="p-8 text-center space-y-4 rounded-3xl border-slate-200 dark:border-slate-800 bg-white/60 dark:bg-slate-900/60 backdrop-blur-sm">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-teal-50 dark:bg-teal-950/60 text-teal-600 dark:text-teal-400 flex items-center justify-center font-bold text-xl">
            <Compass className="w-7 h-7" />
          </div>
          <div className="space-y-1.5 max-w-md mx-auto">
            <h3 className="text-base font-bold font-heading text-slate-900 dark:text-white">
              No Open Requests in Your Area Right Now
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
              When newcomers in your neighborhood submit accommodation, transport, or relocation needs, they will appear here automatically.
            </p>
          </div>
          <div className="pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={refreshNow}
              disabled={isRefreshing}
              className="gap-2"
            >
              {isRefreshing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
              <span>{isRefreshing ? "Refreshing…" : "Refresh Feed"}</span>
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-teal-100 dark:bg-teal-950/80 text-teal-700 dark:text-teal-300">
            <HeartHandshake className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-lg font-bold font-heading text-slate-900 dark:text-white">
              Help Requests Near You
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Newcomers seeking local advice matched to your neighborhood and background.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5 self-start sm:self-center">
          <RefreshStatus
            lastUpdated={lastUpdated}
            isRefreshing={isRefreshing}
            isOffline={isOffline}
            error={refreshError}
            onRefresh={refreshNow}
          />
          <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-teal-50 dark:bg-teal-950/60 text-teal-700 dark:text-teal-300 border border-teal-200 dark:border-teal-800">
            {requests.length} open
          </span>
        </div>
      </div>

      {/* Subtle New Requests Available Indicator */}
      {newItemsCount > 0 && (
        <button
          type="button"
          onClick={applyNewItems}
          className="w-full py-2.5 px-4 rounded-2xl bg-teal-600 hover:bg-teal-700 text-white text-xs font-bold shadow-sm transition flex items-center justify-center gap-2 cursor-pointer animate-in fade-in slide-in-from-top-1"
        >
          <Sparkles className="w-3.5 h-3.5 animate-pulse" />
          <span>{newItemsCount} new request{newItemsCount > 1 ? "s" : ""} nearby · Click to show</span>
        </button>
      )}

      <Stagger className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {requests.map((item) => (
          <StaggerItem key={item.id}>
            <Card hover className="p-5 rounded-2xl bg-white dark:bg-slate-900 border-slate-200/90 dark:border-slate-800 flex flex-col justify-between h-full space-y-4">
              <div className="space-y-3">
                {/* Header: Requester Name & Location */}
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <h3 className="font-bold text-sm text-slate-900 dark:text-white flex items-center gap-1.5">
                      <span>{item.requester_name}</span>
                      <span className="text-xs font-normal text-slate-400">needs guidance</span>
                    </h3>
                    <div className="flex flex-col gap-0.5 mt-1 text-xs">
                      {(item.display_name || item.area || item.city || item.formatted_address) && (
                        <div className="flex items-center gap-1 text-slate-700 dark:text-slate-300 font-medium">
                          <MapPin className="w-3 h-3 text-teal-600 shrink-0" />
                          <span>
                            {item.formatted_address?.replace(/, India$/, "") ||
                              Array.from(new Set([item.display_name, item.area, item.city, item.state]))
                                .filter(Boolean)
                                .join(", ") ||
                              item.city}
                          </span>
                        </div>
                      )}
                      <div>
                        {(!item.location_precision ||
                          [
                            "approximate",
                            "locality",
                            "neighborhood",
                            "sublocality",
                            "sublocality_level_1",
                            "sublocality_level_2",
                            "administrative_area",
                            "country",
                          ].includes(item.location_precision.toLowerCase())) ? (
                          <span className="inline-flex items-center text-[11px] font-medium text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/40 px-2 py-0.5 rounded border border-amber-200/60 dark:border-amber-900/40">
                            Nearby · approximate target area
                          </span>
                        ) : item.distance_km !== null && item.distance_km !== undefined ? (
                          <span className="font-semibold text-teal-700 dark:text-teal-400">
                            • {item.distance_km} km away
                          </span>
                        ) : null}
                      </div>
                    </div>
                  </div>

                  <span className="text-[11px] text-slate-400 shrink-0">
                    {new Date(item.created_at).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                    })}
                  </span>
                </div>

                {/* Raw request text quote */}
                <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-300 line-clamp-3 leading-relaxed bg-slate-50 dark:bg-slate-950/40 p-3 rounded-xl border border-slate-100 dark:border-slate-800/80 italic">
                  "{item.raw_text}"
                </p>

                {/* Extracted category pills */}
                <div className="flex flex-wrap gap-1.5">
                  {(item.needs || []).map((n, idx) => (
                    <span
                      key={idx}
                      className="px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-amber-50 dark:bg-amber-950/60 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-300"
                    >
                      {n}
                    </span>
                  ))}
                  {item.budget_amount && (
                    <span className="px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-300 flex items-center gap-0.5">
                      <IndianRupee className="w-2.5 h-2.5" />
                      {item.budget_amount.toLocaleString()}
                      {item.budget_period ? ` / ${item.budget_period}` : ""}
                    </span>
                  )}
                  {item.preferred_date && (
                    <span className="px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800 text-indigo-800 dark:text-indigo-300 flex items-center gap-0.5">
                      <Calendar className="w-2.5 h-2.5" />
                      {item.preferred_date}
                    </span>
                  )}
                </div>

                {/* Truthful Match Reasons */}
                {(item.match_reasons || []).length > 0 && (
                  <div className="space-y-1 pt-1">
                    {(item.match_reasons || []).slice(0, 2).map((reason, idx) => (
                      <div
                        key={idx}
                        className="text-[11px] text-teal-700 dark:text-teal-400 font-medium flex items-center gap-1.5"
                      >
                        <CheckCircle2 className="w-3 h-3 text-teal-600 shrink-0" />
                        <span>{reason}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Action Button */}
              <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between gap-3">
                <span className="text-[11px] text-slate-400">
                  {item.is_time_flexible ? "Flexible timing" : "Specific timing requested"}
                </span>
                <Button
                  size="sm"
                  onClick={() => setOfferReq(item)}
                  className="gap-1.5 font-semibold"
                >
                  <HeartHandshake className="w-3.5 h-3.5" />
                  <span>Offer Help</span>
                </Button>
              </div>
            </Card>
          </StaggerItem>
        ))}
      </Stagger>

      {/* Offer Help Modal */}
      {offerReq && (
        <Modal
          isOpen={!!offerReq}
          onClose={() => setOfferReq(null)}
          title={`Offer Help to ${offerReq.requester_name}`}
        >
          <div className="space-y-4">
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Introduce yourself and let {offerReq.requester_name} know how you can help them navigate their request in{" "}
              {offerReq.city || "your city"}.
            </p>

            <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs text-slate-700 dark:text-slate-300 italic">
              "{offerReq.raw_text}"
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                Introduction Message (Optional):
              </label>
              <textarea
                value={initialMessage}
                onChange={(e) => setInitialMessage(e.target.value)}
                rows={3}
                placeholder="Hi, I've lived in this area for 3 years. I know good PGs and can help you with transit!"
                className="w-full px-3 py-2 text-xs rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-950 focus:outline-none focus:ring-2 focus:ring-teal-500"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button variant="ghost" size="sm" onClick={() => setOfferReq(null)}>
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={handleSendOffer}
                disabled={isSubmitting}
                className="gap-2"
              >
                {isSubmitting ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Send className="w-3.5 h-3.5" />
                )}
                <span>Send Offer</span>
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
