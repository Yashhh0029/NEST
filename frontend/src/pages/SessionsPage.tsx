import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { Calendar, Filter, Clock, AlertCircle } from "lucide-react";
import { sessionService } from "@/services/sessions";
import { refreshCoordinator } from "@/services/refreshCoordinator";
import { RefreshStatus } from "@/components/common/RefreshStatus";
import { SessionCard } from "@/components/session/SessionCard";
import { RescheduleModal } from "@/components/session/RescheduleModal";
import { CardSkeleton } from "@/components/ui/Skeleton";
import { useAuthStore } from "@/store/useAuthStore";
import type { AssistanceSession, SessionReschedule } from "@/types/session";

type FilterTab = "ALL" | "PROPOSED" | "CONFIRMED" | "COMPLETED" | "CANCELLED";

export function SessionsPage() {
  const { user } = useAuthStore();
  const [sessions, setSessions] = useState<AssistanceSession[]>([]);
  const [activeTab, setActiveTab] = useState<FilterTab>("ALL");
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Reschedule Modal state
  const [rescheduleSession, setRescheduleSession] = useState<AssistanceSession | null>(null);

  const fetchSessions = useCallback(async (isBackground = false) => {
    try {
      if (isBackground) {
        setIsRefreshing(true);
      } else {
        setLoading(true);
      }
      setError(null);
      const params = activeTab === "ALL" ? undefined : { status: activeTab };
      const data = await sessionService.listSessions(params);
      setSessions(data);
      setLastUpdated(new Date());
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load assistance sessions.";
      setError(msg);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, [activeTab]);

  useEffect(() => {
    fetchSessions(false);

    const unsubscribe = refreshCoordinator.subscribe((scopes) => {
      if (
        scopes.includes("sessions") ||
        scopes.includes("visibility_visible") ||
        scopes.includes("network_online")
      ) {
        fetchSessions(true);
      }
    }, ["sessions"]);

    const timer = setInterval(() => {
      if (refreshCoordinator.isTabVisible() && refreshCoordinator.isOnline()) {
        fetchSessions(true);
      }
    }, 30000);

    return () => {
      unsubscribe();
      clearInterval(timer);
    };
  }, [fetchSessions]);

  const handleAccept = async (sessionId: string) => {
    await sessionService.acceptSession(sessionId);
    refreshCoordinator.invalidate(["sessions", "notifications"]);
    await fetchSessions(false);
  };

  const handleDecline = async (sessionId: string) => {
    await sessionService.declineSession(sessionId);
    refreshCoordinator.invalidate(["sessions", "notifications"]);
    await fetchSessions(false);
  };

  const handleCancel = async (sessionId: string, reason: string) => {
    await sessionService.cancelSession(sessionId, { reason });
    refreshCoordinator.invalidate(["sessions", "notifications"]);
    await fetchSessions(false);
  };

  const handleComplete = async (sessionId: string) => {
    await sessionService.completeSession(sessionId);
    refreshCoordinator.invalidate(["sessions", "notifications", "reviews"]);
    await fetchSessions(false);
  };

  const handleRescheduleSubmit = async (sessionId: string, payload: SessionReschedule) => {
    await sessionService.rescheduleSession(sessionId, payload);
    refreshCoordinator.invalidate(["sessions", "notifications"]);
    await fetchSessions(false);
  };

  const handleDownloadIcs = async (sessionId: string, title: string) => {
    await sessionService.downloadCalendarIcs(sessionId, title);
  };

  const currentUserId = user?.id || "";

  return (
    <div className="max-w-4xl mx-auto py-4 sm:py-6 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold font-heading text-gray-900 flex items-center gap-2">
            <Calendar className="w-6 h-6 text-indigo-600" />
            Assistance Sessions
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Coordinate in-person and remote assistance sessions with confirmed newcomers and helpers.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <RefreshStatus
            lastUpdated={lastUpdated}
            isRefreshing={isRefreshing}
            onRefresh={() => fetchSessions(false)}
          />
          <Link
            to="/profile/availability"
            className="inline-flex items-center gap-1.5 px-3.5 py-2 text-sm font-medium text-indigo-700 bg-indigo-50 hover:bg-indigo-100 rounded-lg transition"
          >
            <Clock className="w-4 h-4" />
            Availability Settings
          </Link>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-sm text-red-700">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex border-b border-gray-200 overflow-x-auto pb-1 gap-1">
        {(["ALL", "PROPOSED", "CONFIRMED", "COMPLETED", "CANCELLED"] as FilterTab[]).map((tab) => {
          const isSelected = activeTab === tab;
          const label =
            tab === "ALL"
              ? "All Sessions"
              : tab === "PROPOSED"
              ? "Pending Proposals"
              : tab === "CONFIRMED"
              ? "Confirmed"
              : tab === "COMPLETED"
              ? "Completed"
              : "Cancelled";
          return (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition whitespace-nowrap flex items-center gap-1.5 ${
                isSelected
                  ? "bg-indigo-50 text-indigo-700 border-b-2 border-indigo-600 font-semibold"
                  : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
              }`}
            >
              <Filter className="w-3.5 h-3.5" />
              {label}
            </button>
          );
        })}
      </div>

      {/* Session list */}
      {loading ? (
        <div className="space-y-4">
          <CardSkeleton />
          <CardSkeleton />
        </div>
      ) : sessions.length === 0 ? (
        <div className="text-center py-12 bg-white rounded-xl border border-gray-200 p-8 space-y-3">
          <Calendar className="w-12 h-12 text-gray-300 mx-auto" />
          <h3 className="text-base font-semibold text-gray-800">No assistance sessions found</h3>
          <p className="text-sm text-gray-500 max-w-sm mx-auto">
            {activeTab === "ALL"
              ? "You don't have any assistance sessions yet. Once connected, propose a session from a connection or chat."
              : `No sessions found matching '${activeTab.toLowerCase()}'.`}
          </p>
          <Link
            to="/connections"
            className="inline-block mt-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition"
          >
            View Active Connections
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {sessions.map((sess) => (
            <SessionCard
              key={sess.id}
              session={sess}
              currentUserId={currentUserId}
              onAccept={handleAccept}
              onDecline={handleDecline}
              onCancel={handleCancel}
              onComplete={handleComplete}
              onRescheduleClick={(s) => setRescheduleSession(s)}
              onDownloadIcs={handleDownloadIcs}
            />
          ))}
        </div>
      )}

      {/* Reschedule Modal */}
      {rescheduleSession && (
        <RescheduleModal
          sessionId={rescheduleSession.id}
          isOpen={true}
          onClose={() => setRescheduleSession(null)}
          onSubmit={handleRescheduleSubmit}
        />
      )}
    </div>
  );
}
export default SessionsPage;
