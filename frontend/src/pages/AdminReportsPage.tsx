import React, { useState, useEffect, useCallback } from "react";
import {
  ShieldAlert,
  CheckCircle,
  Loader2,
  UserX,
  UserCheck,
  History,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { useToast } from "@/hooks/useToast";
import {
  adminListReports,
  adminUpdateReport,
  adminSuspendUser,
  adminReactivateUser,
  adminListAuditLogs,
} from "@/services/safety";
import type {
  ReportItem,
  ReportStatus,
  ModerationActionItem,
} from "@/types/safety";

export const AdminReportsPage: React.FC = () => {
  const { success: toastSuccess, error: toastError } = useToast();

  const [activeTab, setActiveTab] = useState<ReportStatus | "ALL" | "AUDIT">("OPEN");
  const [reports, setReports] = useState<ReportItem[]>([]);
  const [auditLogs, setAuditLogs] = useState<ModerationActionItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);

  // Resolution note state
  const [activeReportForResolution, setActiveReportForResolution] = useState<{
    report: ReportItem;
    targetStatus: "RESOLVED" | "DISMISSED";
  } | null>(null);
  const [resolutionNote, setResolutionNote] = useState("");

  // Suspension note state
  const [userToSuspend, setUserToSuspend] = useState<ReportItem | null>(null);
  const [suspensionReason, setSuspensionReason] = useState("");

  const fetchReports = useCallback(async () => {
    setIsLoading(true);
    try {
      if (activeTab === "AUDIT") {
        const auditData = await adminListAuditLogs(1, 50);
        setAuditLogs(auditData.actions || []);
      } else {
        const statusParam = activeTab === "ALL" ? undefined : activeTab;
        const data = await adminListReports(statusParam, 1, 50);
        setReports(data.reports || []);
      }
    } catch {
      toastError("Failed to fetch reports. Admin access required.");
    } finally {
      setIsLoading(false);
    }
  }, [activeTab, toastError]);

  useEffect(() => {
    fetchReports();
  }, [fetchReports]);

  const handleStartReview = async (reportId: string) => {
    setActionLoadingId(reportId);
    try {
      const updated = await adminUpdateReport(reportId, {
        status: "UNDER_REVIEW",
        resolution_note: "Admin started investigation.",
      });
      setReports((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      toastSuccess("Report moved to Under Review.");
    } catch {
      toastError("Failed to update report status.");
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleConfirmResolution = async () => {
    if (!activeReportForResolution) return;
    const { report, targetStatus } = activeReportForResolution;
    setActionLoadingId(report.id);

    try {
      const updated = await adminUpdateReport(report.id, {
        status: targetStatus,
        resolution_note: resolutionNote.trim() || undefined,
      });
      setReports((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
      toastSuccess(`Report marked as ${targetStatus}.`);
      setActiveReportForResolution(null);
      setResolutionNote("");
    } catch {
      toastError("Failed to resolve report.");
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleConfirmSuspension = async () => {
    if (!userToSuspend) return;
    const targetUserId = userToSuspend.reported_user_id;
    setActionLoadingId(userToSuspend.id);

    try {
      await adminSuspendUser(
        targetUserId,
        suspensionReason.trim() || "Account suspended following safety report review."
      );
      toastSuccess(`User ${userToSuspend.reported_user?.name || "account"} suspended.`);
      setUserToSuspend(null);
      setSuspensionReason("");
      fetchReports();
    } catch {
      toastError("Failed to suspend user.");
    } finally {
      setActionLoadingId(null);
    }
  };

  const handleReactivateUser = async (userId: string, reportId: string) => {
    setActionLoadingId(reportId);
    try {
      await adminReactivateUser(userId, "Account reinstated by administrator.");
      toastSuccess("User account reactivated.");
      fetchReports();
    } catch {
      toastError("Failed to reactivate user.");
    } finally {
      setActionLoadingId(null);
    }
  };

  const getStatusBadge = (status: ReportStatus) => {
    switch (status) {
      case "OPEN":
        return <Badge variant="accent">Open</Badge>;
      case "UNDER_REVIEW":
        return <Badge variant="primary">Under Review</Badge>;
      case "RESOLVED":
        return <Badge variant="success">Resolved</Badge>;
      case "DISMISSED":
        return <Badge variant="muted">Dismissed</Badge>;
    }
  };

  return (
    <div className="space-y-6 max-w-5xl mx-auto py-2 sm:py-6">
      {/* Header Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <ShieldAlert className="w-7 h-7 text-amber-600 dark:text-amber-400" />
            <h1 className="text-2xl sm:text-3xl font-bold font-heading text-gray-900 dark:text-gray-100">
              Safety & Moderation Dashboard
            </h1>
          </div>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Administrative queue for investigating community reports, enforcing safety, and auditing actions.
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-2 border-b border-gray-200 dark:border-brand-dark-border">
        {(["OPEN", "UNDER_REVIEW", "RESOLVED", "DISMISSED", "ALL", "AUDIT"] as const).map(
          (tab) => {
            const isActive = activeTab === tab;
            return (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-colors ${
                  isActive
                    ? "bg-brand-primary text-white"
                    : "text-gray-600 dark:text-gray-400 hover:text-gray-900 hover:bg-gray-100 dark:hover:bg-brand-dark-muted"
                }`}
              >
                {tab === "OPEN"
                  ? "Open Reports"
                  : tab === "UNDER_REVIEW"
                  ? "Under Review"
                  : tab === "RESOLVED"
                  ? "Resolved"
                  : tab === "DISMISSED"
                  ? "Dismissed"
                  : tab === "ALL"
                  ? "All Reports"
                  : "Audit Trail"}
              </button>
            );
          }
        )}
      </div>

      {/* Main Content */}
      {isLoading ? (
        <Card className="p-12 text-center space-y-4">
          <Loader2 className="w-8 h-8 text-brand-primary animate-spin mx-auto" />
          <p className="text-sm text-gray-500">Loading moderation records...</p>
        </Card>
      ) : activeTab === "AUDIT" ? (
        // Audit Trail View
        <div className="space-y-3">
          {auditLogs.length === 0 ? (
            <EmptyState
              icon={<History className="w-8 h-8 text-gray-400" />}
              title="No Moderation Actions Logged Yet"
              description="Actions taken by administrators will appear here in chronological order."
            />
          ) : (
            auditLogs.map((log) => (
              <Card key={log.id} className="p-4 space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <Badge variant="primary" size="sm">
                      {log.action}
                    </Badge>
                    <span className="text-xs text-gray-400">
                      by {log.admin_name || "Admin"}
                    </span>
                  </div>
                  <span className="text-xs text-gray-400">
                    {new Date(log.created_at).toLocaleString()}
                  </span>
                </div>
                <p className="text-xs text-gray-700 dark:text-gray-300 font-medium">
                  {log.reason}
                </p>
                {log.target_user_name && (
                  <p className="text-[11px] text-gray-500">
                    Target User: {log.target_user_name}
                  </p>
                )}
              </Card>
            ))
          )}
        </div>
      ) : reports.length === 0 ? (
        <EmptyState
          icon={<CheckCircle className="w-8 h-8 text-emerald-500" />}
          title="No Reports in this Queue"
          description="There are currently no reports matching this status filter."
        />
      ) : (
        // Reports Queue
        <div className="space-y-4">
          {reports.map((report) => {
            const isProcessing = actionLoadingId === report.id;

            return (
              <Card key={report.id} className="p-5 space-y-4">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-gray-100 dark:border-brand-dark-border">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      {getStatusBadge(report.status)}
                      <span className="text-xs font-bold text-red-600 dark:text-red-400 px-2 py-0.5 rounded-full bg-red-50 dark:bg-red-950/40">
                        {report.reason}
                      </span>
                    </div>
                    <p className="text-xs text-gray-500">
                      Reported on {new Date(report.created_at).toLocaleString()}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-gray-500">
                      Reporter:{" "}
                      <strong className="text-gray-800 dark:text-gray-200">
                        {report.reporter?.name || "Anonymous"}
                      </strong>
                    </span>
                    <span className="text-gray-300">•</span>
                    <span className="text-gray-500">
                      Reported:{" "}
                      <strong className="text-gray-800 dark:text-gray-200">
                        {report.reported_user?.name || "Target User"}
                      </strong>
                    </span>
                  </div>
                </div>

                {/* Description & Evidence */}
                {report.description && (
                  <div className="space-y-1">
                    <h5 className="text-xs font-semibold text-gray-600 dark:text-gray-400">
                      Report Description:
                    </h5>
                    <p className="text-xs text-gray-800 dark:text-gray-200 bg-gray-50 dark:bg-brand-dark-muted/20 p-3 rounded-xl">
                      {report.description}
                    </p>
                  </div>
                )}

                {report.message_snippet && (
                  <div className="space-y-1">
                    <h5 className="text-xs font-semibold text-amber-700 dark:text-amber-400">
                      Reported Message Content:
                    </h5>
                    <p className="text-xs italic text-gray-700 dark:text-gray-300 bg-amber-50/50 dark:bg-amber-950/20 border border-amber-200/50 p-3 rounded-xl">
                      &ldquo;{report.message_snippet}&rdquo;
                    </p>
                  </div>
                )}

                {report.resolution_note && (
                  <div className="p-3 rounded-xl bg-teal-50 dark:bg-teal-950/20 border border-teal-200 text-xs text-teal-900 dark:text-teal-200">
                    <strong>Resolution Note:</strong> {report.resolution_note}
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-gray-100 dark:border-brand-dark-border">
                  <div className="flex items-center gap-2">
                    {report.status === "OPEN" && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleStartReview(report.id)}
                        disabled={isProcessing}
                      >
                        Start Review
                      </Button>
                    )}
                    {report.status !== "RESOLVED" && (
                      <Button
                        size="sm"
                        variant="primary"
                        onClick={() =>
                          setActiveReportForResolution({
                            report,
                            targetStatus: "RESOLVED",
                          })
                        }
                        disabled={isProcessing}
                        className="bg-emerald-600 hover:bg-emerald-700"
                      >
                        Resolve
                      </Button>
                    )}
                    {report.status !== "DISMISSED" && (
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() =>
                          setActiveReportForResolution({
                            report,
                            targetStatus: "DISMISSED",
                          })
                        }
                        disabled={isProcessing}
                      >
                        Dismiss
                      </Button>
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => setUserToSuspend(report)}
                      disabled={isProcessing}
                      className="text-red-600 hover:bg-red-50 border-red-200"
                    >
                      <UserX className="w-3.5 h-3.5 mr-1" />
                      Suspend User
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        if (report.reported_user_id) {
                          handleReactivateUser(report.reported_user_id, report.id);
                        }
                      }}
                      disabled={isProcessing}
                      className="text-emerald-600 hover:bg-emerald-50 border-emerald-200"
                    >
                      <UserCheck className="w-3.5 h-3.5 mr-1" />
                      Reactivate
                    </Button>
                  </div>
                </div>
              </Card>
            );
          })}
        </div>
      )}

      {/* Resolution Prompt Modal */}
      {activeReportForResolution && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fade-in">
          <div className="bg-white dark:bg-brand-dark-card border border-gray-200 dark:border-brand-dark-border rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-gray-900 dark:text-gray-100 font-heading">
              {activeReportForResolution.targetStatus === "RESOLVED"
                ? "Resolve Report"
                : "Dismiss Report"}
            </h3>
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">
                Resolution Note
              </label>
              <textarea
                value={resolutionNote}
                onChange={(e) => setResolutionNote(e.target.value)}
                rows={3}
                placeholder="Document resolution rationale for the audit log..."
                className="w-full text-xs p-3 rounded-xl border border-gray-200 dark:border-brand-dark-border bg-white dark:bg-brand-dark-card text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-primary"
              />
            </div>
            <div className="flex items-center justify-end gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setActiveReportForResolution(null);
                  setResolutionNote("");
                }}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleConfirmResolution}
              >
                Confirm
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Suspension Confirmation Modal */}
      {userToSuspend && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fade-in">
          <div className="bg-white dark:bg-brand-dark-card border border-gray-200 dark:border-brand-dark-border rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-red-100 text-red-600 flex items-center justify-center shrink-0">
                <UserX className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-base font-bold text-gray-900 dark:text-gray-100 font-heading">
                  Suspend User Account?
                </h3>
                <p className="text-xs text-gray-500">
                  Target: {userToSuspend.reported_user?.name || "User"}
                </p>
              </div>
            </div>

            <p className="text-xs text-gray-600 dark:text-gray-300 leading-relaxed">
              This will deactivate the user account. They will be immediately blocked from making requests, sending messages, or creating connections. Their historical data will be preserved.
            </p>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">
                Suspension Reason <span className="text-red-500">*</span>
              </label>
              <textarea
                value={suspensionReason}
                onChange={(e) => setSuspensionReason(e.target.value)}
                rows={3}
                placeholder="Reason for suspension (recorded in moderation audit log)..."
                className="w-full text-xs p-3 rounded-xl border border-gray-200 dark:border-brand-dark-border bg-white dark:bg-brand-dark-card text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-primary"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setUserToSuspend(null);
                  setSuspensionReason("");
                }}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleConfirmSuspension}
                disabled={!suspensionReason.trim()}
                className="bg-red-600 hover:bg-red-700 text-white"
              >
                Suspend User
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
