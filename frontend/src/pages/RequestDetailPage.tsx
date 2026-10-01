import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { requestsService } from "@/services/requests";
import { intelligenceService } from "@/services/intelligence";
import { createConnection, listConnections } from "@/services/connections";
import { useToast } from "@/hooks/useToast";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { NeedProgressTracker } from "@/components/intelligence/NeedProgressTracker";
import { NeedIntelligenceCard } from "@/components/intelligence/NeedIntelligenceCard";
import { SavedResourcesList } from "@/components/intelligence/SavedResourcesList";
import { ResolveRequestModal } from "@/components/intelligence/ResolveRequestModal";
import { formatDate } from "@/lib/utils";
import { GoogleMap } from "@/components/location/GoogleMap";
import type { NewcomerRequest } from "@/types/request";
import type {
  NeedStatus,
  RequestIntelligenceResponse,
  SavedResourceCreate,
} from "@/types/intelligence";
import type { ConnectionItem } from "@/types/connection";
import {
  Sparkles,
  MapPin,
  Edit3,
  Trash2,
  ArrowLeft,
  Clock,
  MessageSquare,
  Sliders,
  Send,
} from "lucide-react";

export function RequestDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [request, setRequest] = useState<NewcomerRequest | null>(null);
  const [intelligence, setIntelligence] = useState<RequestIntelligenceResponse | null>(null);
  const [connections, setConnections] = useState<ConnectionItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState("");
  const [isUpdating, setIsUpdating] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showResolveModal, setShowResolveModal] = useState(false);

  // Connect helper modal state
  const [connectingHelper, setConnectingHelper] = useState<{ id: string; name: string } | null>(null);
  const [initialMessage, setInitialMessage] = useState("");
  const [isConnecting, setIsConnecting] = useState(false);

  const navigate = useNavigate();
  const { success: toastSuccess, error: toastError } = useToast();

  const loadData = useCallback(async () => {
    if (!id) return;
    setIsLoading(true);
    try {
      const [reqData, intelData, connsData] = await Promise.all([
        requestsService.getRequestById(id),
        intelligenceService.getIntelligence(id).catch(() => null),
        listConnections({ role: "requester" }).catch(() => ({ connections: [] })),
      ]);
      setRequest(reqData);
      setEditText(reqData.raw_text);
      setIntelligence(intelData);
      setConnections(
        (connsData.connections || []).filter((c) => c.request_id === id)
      );
    } catch {
      toastError("Could not find this request.");
      navigate("/requests");
    } finally {
      setIsLoading(false);
    }
  }, [id, navigate, toastError]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !editText.trim()) return;

    setIsUpdating(true);
    try {
      const updated = await requestsService.updateRequest(id, {
        text: editText.trim(),
      });
      setRequest(updated);
      setIsEditing(false);
      toastSuccess("Request updated and re-parsed by backend NLP engine!", "Updated");
      // Reload intelligence
      const intelData = await intelligenceService.getIntelligence(id);
      setIntelligence(intelData);
    } catch {
      toastError("Failed to update request.");
    } finally {
      setIsUpdating(false);
    }
  };

  const handleDelete = async () => {
    if (!id) return;
    try {
      await requestsService.deleteRequest(id);
      toastSuccess("Request deleted.");
      navigate("/requests");
    } catch {
      toastError("Failed to delete request.");
    }
  };

  const handleUpdateNeedProgress = async (
    category: string,
    newStatus: NeedStatus,
    notes?: string
  ) => {
    if (!id) return;
    try {
      const updatedIntel = await intelligenceService.updateNeedProgress(id, {
        category,
        status: newStatus,
        notes,
      });
      setIntelligence(updatedIntel);
      if (request) {
        setRequest({ ...request, status: updatedIntel.status });
      }
      toastSuccess(`Need '${category}' updated to ${newStatus}.`, "Progress Saved");
    } catch {
      toastError("Failed to update need progress.");
    }
  };

  const handleResolveOverallRequest = async (summary: string) => {
    if (!id) return;
    try {
      const updatedIntel = await intelligenceService.resolveRequest(id, summary);
      setIntelligence(updatedIntel);
      if (request) {
        setRequest({ ...request, status: "RESOLVED" });
      }
      toastSuccess("Request successfully marked as RESOLVED!", "Resolved");
    } catch {
      toastError("Failed to resolve request.");
    }
  };

  const handleSaveResource = async (res: SavedResourceCreate) => {
    if (!id) return;
    try {
      await intelligenceService.saveResource(id, res);
      const updatedIntel = await intelligenceService.getIntelligence(id);
      setIntelligence(updatedIntel);
      toastSuccess(`Saved '${res.name}' to this request.`, "Bookmarked");
    } catch {
      toastError("Failed to save resource.");
    }
  };

  const handleDeleteSavedResource = async (placeId: string) => {
    if (!id) return;
    try {
      await intelligenceService.deleteSavedResource(id, placeId);
      const updatedIntel = await intelligenceService.getIntelligence(id);
      setIntelligence(updatedIntel);
      toastSuccess("Removed bookmark from request.", "Bookmark Removed");
    } catch {
      toastError("Failed to remove bookmark.");
    }
  };

  const handleSendConnection = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !connectingHelper) return;
    setIsConnecting(true);
    try {
      await createConnection({
        request_id: id,
        helper_id: connectingHelper.id,
        initial_message: initialMessage.trim() || undefined,
      });
      toastSuccess(`Connection request sent to ${connectingHelper.name}!`, "Connected");
      setConnectingHelper(null);
      setInitialMessage("");
      loadData();
    } catch {
      toastError("Failed to send connection request.");
    } finally {
      setIsConnecting(false);
    }
  };

  if (isLoading || !request) {
    return (
      <div className="max-w-4xl mx-auto py-12 text-center text-sm text-gray-500">
        Loading request intelligence...
      </div>
    );
  }

  const savedPlaceIds = new Set(intelligence?.saved_resources.map((r) => r.place_id) || []);
  const preferences = request.preferences || [];
  const userContext = request.user_context || [];

  const getStatusBadgeVariant = (st: string) => {
    switch (st) {
      case "RESOLVED":
        return "success";
      case "PARTIALLY_RESOLVED":
      case "IN_PROGRESS":
        return "primary";
      default:
        return "muted";
    }
  };

  return (
    <div className="space-y-8 max-w-5xl mx-auto py-2 sm:py-6">
      {/* Top Navigation & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <Link
          to="/requests"
          className="text-xs font-semibold text-brand-primary dark:text-teal-400 flex items-center gap-1 hover:underline min-h-[44px]"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Requests
        </Link>

        <div className="flex items-center gap-2 flex-wrap">
          <Link to={`/results/${request.id}`}>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<Sliders className="w-3.5 h-3.5" />}
              title="Open full hybrid candidate matcher with custom weight sliders and radar charts"
            >
              Advanced Matcher
            </Button>
          </Link>
          <Button
            variant="outline"
            size="sm"
            onClick={() => setIsEditing(!isEditing)}
            leftIcon={<Edit3 className="w-3.5 h-3.5" />}
          >
            {isEditing ? "Cancel Edit" : "Edit Request"}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowDeleteModal(true)}
            className="text-brand-danger hover:bg-red-50 dark:hover:bg-red-950/30"
            leftIcon={<Trash2 className="w-3.5 h-3.5" />}
          >
            Delete
          </Button>
        </div>
      </div>

      {/* Main Request Summary & Status Banner */}
      <Card className="p-6 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 border-b border-gray-100 dark:border-brand-dark-border/60 pb-4">
          <div className="space-y-1">
            <span className="text-xs font-bold uppercase tracking-wider text-gray-400 flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              Submitted {formatDate(request.created_at)}
            </span>
            <h1 className="text-xl sm:text-2xl font-bold font-heading text-gray-900 dark:text-gray-100">
              Request Intelligence Hub
            </h1>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant={getStatusBadgeVariant(intelligence?.status || request.status)} size="md">
              {intelligence?.status || request.status}
            </Badge>
          </div>
        </div>

        {/* Edit or Display Request Text */}
        {isEditing ? (
          <form onSubmit={handleUpdate} className="space-y-4">
            <textarea
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              rows={3}
              className="w-full text-sm p-3 rounded-xl border border-gray-200 dark:border-brand-dark-border bg-white dark:bg-brand-dark-surface focus:outline-none focus:ring-1 focus:ring-brand-primary"
            />
            <div className="flex justify-end gap-2">
              <Button type="button" variant="ghost" size="sm" onClick={() => setIsEditing(false)}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" size="sm" disabled={isUpdating}>
                {isUpdating ? "Saving..." : "Update Request"}
              </Button>
            </div>
          </form>
        ) : (
          <p className="text-sm sm:text-base text-gray-800 dark:text-gray-200 leading-relaxed font-medium">
            "{request.raw_text}"
          </p>
        )}

        {/* Request Context Metadata */}
        <div className="flex flex-wrap gap-2 pt-1 text-xs">
          {request.city && (
            <span className="flex items-center gap-1 bg-gray-50 dark:bg-brand-dark-muted px-2.5 py-1 rounded-lg border border-gray-200 dark:border-brand-dark-border font-medium text-gray-700 dark:text-gray-300">
              <MapPin className="w-3.5 h-3.5 text-red-500" />
              {request.area ? `${request.area}, ` : ""}{request.city}
            </span>
          )}
          {request.budget_amount && (
            <span className="bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 px-2.5 py-1 rounded-lg border border-emerald-200 dark:border-emerald-800 font-semibold">
              Budget: {request.budget_operator || "≤"} ₹{request.budget_amount.toLocaleString("en-IN")} {request.budget_period ? `/${request.budget_period}` : ""}
            </span>
          )}
          {preferences.map((p, idx) => (
            <Badge key={idx} variant="success" size="sm" icon="🌱">
              {p}
            </Badge>
          ))}
          {userContext.map((c, idx) => (
            <Badge key={idx} variant="muted" size="sm" icon="💼">
              {c}
            </Badge>
          ))}
        </div>
      </Card>

      {/* Target Destination Google Map */}
      {(request.target_location?.latitude != null || request.city) && (
        <Card className="p-4 sm:p-5 border border-gray-200 dark:border-brand-dark-border space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
              <MapPin className="w-4 h-4 text-brand-primary" />
              Target Destination Area ({request.target_location?.city || request.city})
            </h3>
            <span className="text-[11px] text-gray-500 dark:text-gray-400 font-medium">
              Geographic Map &middot; Privacy Protected Area
            </span>
          </div>
          <GoogleMap
            targetLocation={{
              latitude: request.target_location?.latitude,
              longitude: request.target_location?.longitude,
              label:
                request.target_location?.formatted_address ||
                [request.target_location?.area || request.area, request.target_location?.city || request.city]
                  .filter(Boolean)
                  .join(", ") ||
                "Target Destination",
            }}
            className="h-64 sm:h-72"
          />
        </Card>
      )}

      {/* Deterministic Action Plan Banner */}
      {intelligence && intelligence.action_plan.length > 0 && (
        <Card className="p-5 bg-teal-50/50 dark:bg-brand-dark-muted/20 border-teal-100 dark:border-brand-dark-border space-y-3">
          <div className="flex items-center gap-2 text-brand-primary dark:text-teal-300 font-bold text-sm">
            <Sparkles className="w-4 h-4 text-amber-500" />
            <span>Recommended Immediate Next Steps</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {intelligence.action_plan.map((step, idx) => (
              <div
                key={idx}
                className="p-3 rounded-xl bg-white dark:bg-brand-dark-surface border border-teal-100 dark:border-brand-dark-border/60 text-xs text-gray-700 dark:text-gray-300 flex items-start gap-2 shadow-2xs"
              >
                <span className="w-5 h-5 rounded-full bg-teal-100 dark:bg-teal-900/60 text-brand-primary dark:text-teal-300 flex items-center justify-center font-bold text-[10px] shrink-0">
                  {idx + 1}
                </span>
                <span className="leading-snug">{step}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Need Resolution Progress Tracker */}
      {intelligence && (
        <NeedProgressTracker
          bundles={intelligence.needs}
          progressPercentage={intelligence.progress_percentage}
          resolvedNeeds={intelligence.resolved_needs}
          totalNeeds={intelligence.total_needs}
          onUpdateStatus={handleUpdateNeedProgress}
          onMarkOverallResolved={() => setShowResolveModal(true)}
          isOverallResolved={intelligence.status === "RESOLVED"}
        />
      )}

      {/* Active Connections on this Request */}
      {connections.length > 0 && (
        <Card className="p-5 space-y-3 border border-gray-200 dark:border-brand-dark-border">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100 flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-brand-primary" />
              Active Interactions for this Request ({connections.length})
            </h4>
            <Link to="/connections" className="text-xs text-brand-primary dark:text-teal-400 font-semibold hover:underline">
              View All Connections
            </Link>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
            {connections.map((c) => (
              <div
                key={c.id}
                className="p-3 rounded-xl border border-gray-100 dark:border-brand-dark-border bg-gray-50/50 dark:bg-brand-dark-muted/20 space-y-2"
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-gray-900 dark:text-gray-100">
                    {c.helper?.name || c.requester?.name || "Helper"}
                  </span>
                  <Badge variant={c.status === "ACCEPTED" ? "success" : "muted"} size="sm">
                    {c.status}
                  </Badge>
                </div>
                <div className="flex items-center justify-between pt-1">
                  <span className="text-[10px] text-gray-400">
                    Connected {formatDate(c.created_at)}
                  </span>
                  {c.status === "ACCEPTED" && (
                    <Link to={`/connections`} className="text-xs text-brand-primary dark:text-teal-400 font-semibold hover:underline">
                      Chat →
                    </Link>
                  )}
                </div>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Need-by-Need Action Bundles */}
      {intelligence && intelligence.needs.length > 0 ? (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-bold font-heading text-gray-900 dark:text-gray-100">
                Actionable Need Bundles
              </h2>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Verified people, community guides, and local places aggregated per requirement.
              </p>
            </div>
          </div>

          {intelligence.needs.map((bundle, idx) => (
            <NeedIntelligenceCard
              key={idx}
              bundle={bundle}
              requestId={request.id}
              savedPlaceIds={savedPlaceIds}
              onSaveResource={handleSaveResource}
              onConnectHelper={(helperId, helperName) =>
                setConnectingHelper({ id: helperId, name: helperName })
              }
            />
          ))}
        </div>
      ) : (
        <Card className="p-8 text-center text-sm text-gray-500">
          No structured needs extracted for this request.
        </Card>
      )}

      {/* Bookmarked / Saved Resources Section */}
      {intelligence && (
        <SavedResourcesList
          resources={intelligence.saved_resources}
          onDeleteResource={handleDeleteSavedResource}
        />
      )}

      {/* Connect Helper Modal */}
      {connectingHelper && (
        <Modal
          isOpen={true}
          onClose={() => setConnectingHelper(null)}
          title={`Connect with ${connectingHelper.name}`}
        >
          <form onSubmit={handleSendConnection} className="space-y-4">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Send an introduction message to {connectingHelper.name} regarding your request. Strangers can only chat once a connection request is accepted.
            </p>
            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">
                Initial Message
              </label>
              <textarea
                value={initialMessage}
                onChange={(e) => setInitialMessage(e.target.value)}
                placeholder={`Hi ${connectingHelper.name.split(" ")[0]}, I saw your profile on NEST and am looking for local guidance with my request...`}
                rows={3}
                required
                className="w-full text-xs p-3 rounded-xl border border-gray-200 dark:border-brand-dark-border bg-white dark:bg-brand-dark-surface focus:outline-none focus:ring-1 focus:ring-brand-primary"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => setConnectingHelper(null)}
                disabled={isConnecting}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                size="sm"
                disabled={isConnecting}
                leftIcon={<Send className="w-3.5 h-3.5" />}
              >
                {isConnecting ? "Sending..." : "Send Request"}
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* Mark Resolved Modal */}
      <ResolveRequestModal
        isOpen={showResolveModal}
        onClose={() => setShowResolveModal(false)}
        onConfirm={handleResolveOverallRequest}
      />

      {/* Delete Request Modal */}
      {showDeleteModal && (
        <Modal
          isOpen={true}
          onClose={() => setShowDeleteModal(false)}
          title="Delete Request"
        >
          <div className="space-y-4">
            <p className="text-sm text-gray-600 dark:text-gray-300">
              Are you sure you want to delete this request? This will cascade and delete associated intelligence records and bookmarks.
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="ghost" size="sm" onClick={() => setShowDeleteModal(false)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                className="bg-brand-danger hover:bg-red-700 text-white"
                onClick={handleDelete}
              >
                Delete Request
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
