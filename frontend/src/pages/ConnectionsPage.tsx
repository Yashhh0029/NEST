import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import { useAuthStore } from "@/store/useAuthStore";
import {
  listConnections,
  updateConnectionStatus,
} from "@/services/connections";
import {
  completeConnection,
  getConnectionReviews,
} from "@/services/reviews";
import type { ConnectionItem } from "@/types/connection";
import type { ReviewItem } from "@/types/review";
import { ReviewModal } from "@/components/review/ReviewModal";
import { useToast } from "@/hooks/useToast";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { CardSkeleton } from "@/components/ui/Skeleton";
import {
  Users,
  Inbox,
  Send,
  CheckCircle2,
  XCircle,
  Clock,
  MapPin,
  FileText,
  Calendar,
  MessageSquare,
  Star,
  Check,
} from "lucide-react";

type TabType = "incoming" | "sent" | "active";

export function ConnectionsPage() {
  const { user } = useAuthStore();
  const { success: toastSuccess, error: toastError } = useToast();

  const [activeTab, setActiveTab] = useState<TabType>("incoming");
  const [connections, setConnections] = useState<ConnectionItem[]>([]);
  const [reviewsMap, setReviewsMap] = useState<Record<string, ReviewItem[]>>({});
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const [isReviewModalOpen, setIsReviewModalOpen] = useState<boolean>(false);
  const [selectedConnection, setSelectedConnection] = useState<ConnectionItem | null>(null);

  const fetchReviewsForCompleted = useCallback(async (conns: ConnectionItem[]) => {
    const completedConns = conns.filter((c) => c.status === "COMPLETED");
    const reviewsEntries = await Promise.all(
      completedConns.map(async (c) => {
        try {
          const res = await getConnectionReviews(c.id);
          const list = Array.isArray(res) ? res : ((res as unknown as { reviews?: ReviewItem[] })?.reviews || []);
          return [c.id, list] as const;
        } catch {
          return [c.id, []] as const;
        }
      })
    );
    setReviewsMap(Object.fromEntries(reviewsEntries));
  }, []);

  const fetchConnections = useCallback(async () => {
    setIsLoading(true);
    try {
      const data = await listConnections();
      const list = data.connections || [];
      setConnections(list);
      await fetchReviewsForCompleted(list);
    } catch {
      toastError("Failed to load connections. Please refresh.");
    } finally {
      setIsLoading(false);
    }
  }, [toastError, fetchReviewsForCompleted]);

  useEffect(() => {
    fetchConnections();
  }, [fetchConnections]);

  const handleComplete = async (connectionId: string) => {
    setActionLoadingId(connectionId);
    try {
      const updated = await completeConnection(connectionId);
      setConnections((prev) =>
        prev.map((c) => (c.id === connectionId ? updated : c))
      );
      toastSuccess("Interaction completed! You can now leave a review.");
      setSelectedConnection(updated);
      setIsReviewModalOpen(true);
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response
              ?.data?.detail
          : null;
      toastError(msg || "Failed to complete connection.");
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleAction = async (
    connectionId: string,
    action: "accept" | "decline" | "cancel"
  ) => {
    setActionLoadingId(connectionId);
    try {
      const updated = await updateConnectionStatus(connectionId, action);
      setConnections((prev) =>
        prev.map((c) => (c.id === connectionId ? updated : c))
      );
      if (action === "accept") {
        toastSuccess("Connection accepted! You can now collaborate.");
      } else if (action === "decline") {
        toastSuccess("Request declined.");
      } else if (action === "cancel") {
        toastSuccess("Request cancelled.");
      }
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response
              ?.data?.detail
          : null;
      toastError(msg || `Failed to ${action} connection.`);
    } finally {
      setActionLoadingId(null);
    }
  };

  const incomingPending = connections.filter(
    (c) => c.helper_id === user?.id && c.status === "PENDING"
  );
  const sentPending = connections.filter(
    (c) => c.requester_id === user?.id && c.status === "PENDING"
  );
  const activeConnections = connections.filter(
    (c) => c.status === "ACCEPTED" || c.status === "COMPLETED"
  );

  return (
    <div className="space-y-6 max-w-4xl mx-auto py-2 sm:py-6">
      {/* Page Header */}
      <div className="space-y-1">
        <h1 className="text-2xl sm:text-3xl font-bold font-heading text-gray-900 dark:text-gray-100 flex items-center gap-2">
          <Users className="w-7 h-7 text-brand-primary" />
          Connections
        </h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Manage your incoming helper requests, sent invitations, and active community connections.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 dark:border-brand-dark-border space-x-1 overflow-x-auto no-scrollbar">
        <button
          onClick={() => setActiveTab("incoming")}
          className={`px-4 py-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 min-h-[44px] whitespace-nowrap shrink-0 ${
            activeTab === "incoming"
              ? "border-brand-primary text-brand-primary dark:text-teal-400"
              : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 hover:border-gray-300"
          }`}
        >
          <Inbox className="w-4 h-4" />
          <span>Incoming</span>
          {incomingPending.length > 0 && (
            <span className="ml-1 px-2 py-0.5 text-xs font-bold bg-brand-primary text-white rounded-full">
              {incomingPending.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("sent")}
          className={`px-4 py-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 min-h-[44px] whitespace-nowrap shrink-0 ${
            activeTab === "sent"
              ? "border-brand-primary text-brand-primary dark:text-teal-400"
              : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 hover:border-gray-300"
          }`}
        >
          <Send className="w-4 h-4" />
          <span>Sent</span>
          {sentPending.length > 0 && (
            <span className="ml-1 px-2 py-0.5 text-xs font-medium bg-gray-100 dark:bg-brand-dark-muted text-gray-700 dark:text-gray-300 rounded-full">
              {sentPending.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab("active")}
          className={`px-4 py-3 text-sm font-semibold border-b-2 transition-all flex items-center gap-2 min-h-[44px] whitespace-nowrap shrink-0 ${
            activeTab === "active"
              ? "border-brand-primary text-brand-primary dark:text-teal-400"
              : "border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400 hover:border-gray-300"
          }`}
        >
          <CheckCircle2 className="w-4 h-4" />
          <span>Active</span>
          {activeConnections.length > 0 && (
            <span className="ml-1 px-2 py-0.5 text-xs font-bold bg-emerald-100 text-emerald-800 dark:bg-emerald-950/60 dark:text-emerald-300 rounded-full">
              {activeConnections.length}
            </span>
          )}
        </button>
      </div>

      {/* Tab Contents */}
      {isLoading ? (
        <div className="space-y-4">
          <CardSkeleton />
          <CardSkeleton />
        </div>
      ) : activeTab === "incoming" ? (
        incomingPending.length === 0 ? (
          <EmptyState
            icon={<Inbox className="w-8 h-8 text-gray-400" />}
            title="No Incoming Requests"
            description="When newcomers find your profile in hybrid matching and reach out for assistance, their connection requests will appear here."
          />
        ) : (
          <div className="space-y-4">
            {incomingPending.map((conn) => (
              <Card key={conn.id} className="space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <div className="w-12 h-12 rounded-xl bg-teal-100 dark:bg-brand-dark-muted/60 text-brand-primary dark:text-teal-300 flex items-center justify-center font-bold text-lg font-heading">
                      {conn.requester?.name?.charAt(0) || "U"}
                    </div>
                    <div>
                      <h3 className="font-bold text-gray-900 dark:text-gray-100 font-heading">
                        {conn.requester?.name || "Community Member"}
                      </h3>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {conn.requester?.headline || "Newcomer"}
                      </p>
                      {(conn.requester?.city || conn.requester?.area) && (
                        <div className="flex items-center gap-1 text-xs text-gray-500 mt-0.5">
                          <MapPin className="w-3.5 h-3.5 text-brand-primary" />
                          <span>
                            {[conn.requester.area, conn.requester.city]
                              .filter(Boolean)
                              .join(", ")}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border border-amber-200/50">
                    <Clock className="w-3.5 h-3.5" />
                    Pending Your Response
                  </span>
                </div>

                {/* Request Context */}
                {conn.request && (
                  <div className="p-3.5 rounded-xl bg-gray-50 dark:bg-brand-dark-muted/30 border border-gray-100 dark:border-brand-dark-border text-xs space-y-1.5">
                    <div className="flex items-center justify-between text-gray-500">
                      <span className="font-semibold flex items-center gap-1 text-gray-700 dark:text-gray-300">
                        <FileText className="w-3.5 h-3.5 text-brand-primary" />
                        Regarding Request:
                      </span>
                      <Link
                        to={`/requests/${conn.request_id}`}
                        className="text-brand-primary hover:underline font-medium"
                      >
                        View Request Details
                      </Link>
                    </div>
                    <p className="text-gray-800 dark:text-gray-200 italic">
                      "{conn.request.raw_text}"
                    </p>
                  </div>
                )}

                {/* Initial Message */}
                {conn.initial_message && (
                  <div className="p-3 rounded-xl bg-teal-50/50 dark:bg-teal-950/20 border border-teal-100 dark:border-teal-900/30 text-xs">
                    <span className="font-semibold text-brand-primary dark:text-teal-300 block mb-0.5">
                      Message from Requester:
                    </span>
                    <p className="text-gray-700 dark:text-gray-300">
                      {conn.initial_message}
                    </p>
                  </div>
                )}

                {/* Timestamps & Actions */}
                <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-gray-100 dark:border-brand-dark-border">
                  <span className="text-[11px] text-gray-400 flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    Received {new Date(conn.created_at).toLocaleDateString()}
                  </span>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleAction(conn.id, "decline")}
                      disabled={actionLoadingId === conn.id}
                    >
                      <XCircle className="w-4 h-4 mr-1 text-gray-500" />
                      Decline
                    </Button>
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => handleAction(conn.id, "accept")}
                      disabled={actionLoadingId === conn.id}
                      isLoading={actionLoadingId === conn.id}
                    >
                      <CheckCircle2 className="w-4 h-4 mr-1" />
                      Accept Connection
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )
      ) : activeTab === "sent" ? (
        sentPending.length === 0 ? (
          <EmptyState
            icon={<Send className="w-8 h-8 text-gray-400" />}
            title="No Pending Sent Requests"
            description="When you discover community helpers on the hybrid matching page and send a connection request, you can monitor their responses here."
          />
        ) : (
          <div className="space-y-4">
            {sentPending.map((conn) => (
              <Card key={conn.id} className="space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <div className="w-12 h-12 rounded-xl bg-teal-100 dark:bg-brand-dark-muted/60 text-brand-primary dark:text-teal-300 flex items-center justify-center font-bold text-lg font-heading">
                      {conn.helper?.name?.charAt(0) || "H"}
                    </div>
                    <div>
                      <h3 className="font-bold text-gray-900 dark:text-gray-100 font-heading">
                        {conn.helper?.name || "Community Helper"}
                      </h3>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {conn.helper?.headline || "Local Guide"}
                      </p>
                      {(conn.helper?.city || conn.helper?.area) && (
                        <div className="flex items-center gap-1 text-xs text-gray-500 mt-0.5">
                          <MapPin className="w-3.5 h-3.5 text-brand-primary" />
                          <span>
                            {[conn.helper.area, conn.helper.city]
                              .filter(Boolean)
                              .join(", ")}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border border-amber-200/50">
                    <Clock className="w-3.5 h-3.5" />
                    Awaiting Response
                  </span>
                </div>

                {conn.request && (
                  <div className="p-3.5 rounded-xl bg-gray-50 dark:bg-brand-dark-muted/30 border border-gray-100 dark:border-brand-dark-border text-xs space-y-1">
                    <span className="font-semibold text-gray-700 dark:text-gray-300 block">
                      Associated Request:
                    </span>
                    <p className="text-gray-800 dark:text-gray-200 italic line-clamp-2">
                      "{conn.request.raw_text}"
                    </p>
                  </div>
                )}

                <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-gray-100 dark:border-brand-dark-border">
                  <span className="text-[11px] text-gray-400 flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    Sent {new Date(conn.created_at).toLocaleDateString()}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleAction(conn.id, "cancel")}
                    disabled={actionLoadingId === conn.id}
                    isLoading={actionLoadingId === conn.id}
                  >
                    Cancel Request
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )
      ) : activeConnections.length === 0 ? (
        <EmptyState
          icon={<CheckCircle2 className="w-8 h-8 text-gray-400" />}
          title="No Active Connections Yet"
          description="Once an incoming request is accepted or a community helper accepts your invitation, active mutual connections will be displayed here."
        />
      ) : (
        <div className="space-y-4">
          {activeConnections.map((conn) => {
            const isMeRequester = conn.requester_id === user?.id;
            const partner = isMeRequester ? conn.helper : conn.requester;
            const roleLabel = isMeRequester ? "Helper" : "Newcomer";

            return (
              <Card key={conn.id} className="space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <div className="w-12 h-12 rounded-xl bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 flex items-center justify-center font-bold text-lg font-heading">
                      {partner?.name?.charAt(0) || "C"}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-bold text-gray-900 dark:text-gray-100 font-heading">
                          {partner?.name || "Connected Member"}
                        </h3>
                        <Badge variant="primary" size="sm">
                          {roleLabel}
                        </Badge>
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {partner?.headline || "Active Member"}
                      </p>
                      {(partner?.city || partner?.area) && (
                        <div className="flex items-center gap-1 text-xs text-gray-500 mt-0.5">
                          <MapPin className="w-3.5 h-3.5 text-brand-primary" />
                          <span>
                            {[partner.area, partner.city]
                              .filter(Boolean)
                              .join(", ")}
                          </span>
                        </div>
                      )}
                    </div>
                  </div>

                  {conn.status === "COMPLETED" ? (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 border border-blue-200/50">
                      <CheckCircle2 className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
                      Completed
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-200/50">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                      Connected
                    </span>
                  )}
                </div>

                {conn.request && (
                  <div className="p-3.5 rounded-xl bg-gray-50 dark:bg-brand-dark-muted/30 border border-gray-100 dark:border-brand-dark-border text-xs space-y-1">
                    <span className="font-semibold text-gray-700 dark:text-gray-300 block">
                      Connected for Request:
                    </span>
                    <p className="text-gray-800 dark:text-gray-200 italic line-clamp-2">
                      "{conn.request.raw_text}"
                    </p>
                  </div>
                )}

                <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-t border-gray-100 dark:border-brand-dark-border">
                  <span className="text-[11px] text-gray-400 flex items-center gap-1">
                    <Calendar className="w-3 h-3" />
                    {conn.status === "COMPLETED"
                      ? `Completed on ${new Date(conn.completed_at || conn.updated_at).toLocaleDateString()}`
                      : `Connected since ${
                          conn.accepted_at
                            ? new Date(conn.accepted_at).toLocaleDateString()
                            : new Date(conn.updated_at).toLocaleDateString()
                        }`}
                  </span>
                  <div className="flex items-center gap-2">
                    {conn.status === "COMPLETED" ? (
                      <>
                        <Link to={`/chat/${conn.id}`}>
                          <Button variant="outline" size="sm">
                            <MessageSquare className="w-4 h-4 mr-1.5" />
                            Chat History
                          </Button>
                        </Link>
                        {(() => {
                          const raw = reviewsMap[conn.id];
                          const connRevs = Array.isArray(raw)
                            ? raw
                            : ((raw as unknown as { reviews?: ReviewItem[] })?.reviews || []);
                          const hasReviewed = connRevs.some((r) => r.reviewer_id === user?.id);
                          return hasReviewed ? (
                            <span className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 px-2.5 py-1 rounded-full border border-emerald-200/50">
                              <Check className="w-3.5 h-3.5" />
                              Review Submitted
                            </span>
                          ) : (
                            <Button
                              variant="primary"
                              size="sm"
                              onClick={() => {
                                setSelectedConnection(conn);
                                setIsReviewModalOpen(true);
                              }}
                            >
                              <Star className="w-4 h-4 mr-1.5 text-amber-300 fill-amber-300" />
                              Review {roleLabel}
                            </Button>
                          );
                        })()}
                      </>
                    ) : (
                      <>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleComplete(conn.id)}
                          disabled={actionLoadingId === conn.id}
                          isLoading={actionLoadingId === conn.id}
                        >
                          <CheckCircle2 className="w-4 h-4 mr-1.5 text-emerald-600" />
                          Complete Interaction
                        </Button>
                        <Link to={`/chat/${conn.id}`}>
                          <Button variant="primary" size="sm">
                            <MessageSquare className="w-4 h-4 mr-1.5" />
                            Message
                          </Button>
                        </Link>
                      </>
                    )}
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {isReviewModalOpen && selectedConnection && (
        <ReviewModal
          isOpen={isReviewModalOpen}
          onClose={() => {
            setIsReviewModalOpen(false);
            setSelectedConnection(null);
          }}
          connectionId={selectedConnection.id}
          partnerName={
            (selectedConnection.requester_id === user?.id
              ? selectedConnection.helper?.name
              : selectedConnection.requester?.name) || "Partner"
          }
          onSuccess={async () => {
            try {
              const res = await getConnectionReviews(selectedConnection.id);
              const list = Array.isArray(res) ? res : ((res as unknown as { reviews?: ReviewItem[] })?.reviews || []);
              setReviewsMap((prev) => ({
                ...prev,
                [selectedConnection.id]: list,
              }));
            } catch {
              // Ignore
            }
          }}
        />
      )}
    </div>
  );
}
