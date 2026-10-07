import { useState } from "react";
import { Link } from "react-router-dom";
import { requestsService } from "@/services/requests";
import { refreshCoordinator } from "@/services/refreshCoordinator";
import { useAutoRefresh } from "@/hooks/useAutoRefresh";
import { RefreshStatus } from "@/components/common/RefreshStatus";
import { useToast } from "@/hooks/useToast";
import { RequestCard } from "@/components/request/RequestCard";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { EmptyState } from "@/components/ui/EmptyState";
import { CardSkeleton } from "@/components/ui/Skeleton";
import type { NewcomerRequest } from "@/types/request";
import { PlusCircle, FileText, Trash2, AlertCircle, Loader2 } from "lucide-react";

export function RequestsPage() {
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const { success: toastSuccess, error: toastError } = useToast();

  const {
    data: requests = [],
    setData: setRequests,
    isLoading,
    isRefreshing,
    isOffline,
    error: refreshError,
    lastUpdated,
    refreshNow,
  } = useAutoRefresh<NewcomerRequest[]>({
    queryKey: "my_requests",
    fetchFn: (signal) => requestsService.getMyRequests(signal),
    interval: 45000,
    scopes: ["requests"],
    onError: () => toastError("Could not load requests. Please retry."),
  });

  const confirmDelete = async () => {
    if (!deleteTargetId) return;

    setIsDeleting(true);
    try {
      await requestsService.deleteRequest(deleteTargetId);
      setRequests((prev) => (prev ? prev.filter((r) => r.id !== deleteTargetId) : []));
      toastSuccess("Request deleted successfully.");
      setDeleteTargetId(null);
      // Invalidate requests & nearby feeds immediately
      refreshCoordinator.invalidate(["requests", "nearby_requests"]);
    } catch {
      toastError("Failed to delete request.");
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto py-2 sm:py-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold font-heading text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <FileText className="w-6 h-6 text-brand-primary" />
            Your Requests
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            View, track, or edit your community assistance requests.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <RefreshStatus
            lastUpdated={lastUpdated}
            isRefreshing={isRefreshing}
            isOffline={isOffline}
            error={refreshError}
            onRefresh={refreshNow}
          />
          <Link to="/home">
            <Button leftIcon={<PlusCircle className="w-4 h-4" />}>New Request</Button>
          </Link>
        </div>
      </div>

      {/* Loading Skeleton */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <CardSkeleton />
          <CardSkeleton />
        </div>
      ) : refreshError && requests.length === 0 ? (
        <Card className="p-8 text-center space-y-4 rounded-3xl border-rose-200/80 dark:border-rose-900/40 bg-rose-50/30 dark:bg-rose-950/20 backdrop-blur-sm">
          <div className="w-14 h-14 mx-auto rounded-2xl bg-rose-100 dark:bg-rose-900/60 text-rose-600 dark:text-rose-400 flex items-center justify-center font-bold text-xl shadow-xs">
            <AlertCircle className="w-7 h-7" />
          </div>
          <div className="space-y-1.5 max-w-md mx-auto">
            <h3 className="text-base font-bold font-heading text-slate-900 dark:text-white">
              Couldn't Load Requests
            </h3>
            <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
              {(refreshError as any)?.response?.data?.detail ||
                refreshError.message ||
                "Failed to retrieve your assistance requests. Please retry."}
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
      ) : requests.length === 0 ? (
        <EmptyState
          icon={<FileText className="w-8 h-8" />}
          title="No requests created yet"
          description="Have questions about PG accommodation, local tiffins, or city transit? Create your first request!"
          actionLabel="Describe What You Need"
          onAction={() => (window.location.href = "/home")}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {requests.map((req) => (
            <RequestCard
              key={req.id}
              request={req}
              onDelete={(id) => setDeleteTargetId(id)}
            />
          ))}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={deleteTargetId !== null}
        onClose={() => setDeleteTargetId(null)}
        title="Delete Request"
        description="Are you sure you want to permanently remove this request? This action cannot be undone."
      >
        <div className="flex justify-end gap-3 pt-4">
          <Button
            variant="outline"
            onClick={() => setDeleteTargetId(null)}
            disabled={isDeleting}
          >
            Cancel
          </Button>
          <Button
            variant="danger"
            isLoading={isDeleting}
            onClick={confirmDelete}
            leftIcon={<Trash2 className="w-4 h-4" />}
          >
            Delete Permanently
          </Button>
        </div>
      </Modal>
    </div>
  );
}
