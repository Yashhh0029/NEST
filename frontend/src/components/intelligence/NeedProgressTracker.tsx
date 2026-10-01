import { useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import type { NeedIntelligenceBundle, NeedStatus } from "@/types/intelligence";
import { CheckCircle2 } from "lucide-react";

interface NeedProgressTrackerProps {
  bundles: NeedIntelligenceBundle[];
  progressPercentage: number;
  resolvedNeeds: number;
  totalNeeds: number;
  onUpdateStatus: (category: string, newStatus: NeedStatus, notes?: string) => Promise<void>;
  onMarkOverallResolved: () => void;
  onResolveIndependently?: () => void;
  isOverallResolved: boolean;
  hasAcceptedHelper?: boolean;
}

export function NeedProgressTracker({
  bundles,
  progressPercentage,
  resolvedNeeds,
  totalNeeds,
  onUpdateStatus,
  onMarkOverallResolved,
  onResolveIndependently,
  isOverallResolved,
  hasAcceptedHelper = false,
}: NeedProgressTrackerProps) {
  const [selectedBundle, setSelectedBundle] = useState<NeedIntelligenceBundle | null>(null);
  const [targetStatus, setTargetStatus] = useState<NeedStatus>("RESOLVED");
  const [notes, setNotes] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const getStatusBadge = (status: NeedStatus) => {
    switch (status) {
      case "RESOLVED":
        return <Badge variant="success" icon="✓">RESOLVED</Badge>;
      case "RESOLUTION_PENDING":
        return <Badge variant="primary" icon="⏳">PENDING CONFIRMATION</Badge>;
      case "CONNECTED":
        return <Badge variant="primary" icon="🤝">CONNECTED</Badge>;
      case "EXPLORING":
        return <Badge variant="muted" icon="🔍">EXPLORING</Badge>;
      default:
        return <Badge variant="muted" icon="⭕">UNRESOLVED</Badge>;
    }
  };

  const handleOpenStatusModal = (bundle: NeedIntelligenceBundle) => {
    setSelectedBundle(bundle);
    setTargetStatus(bundle.status === "RESOLVED" ? "EXPLORING" : "RESOLVED");
    setNotes("");
  };

  const handleConfirmStatus = async () => {
    if (!selectedBundle) return;
    setIsSubmitting(true);
    try {
      await onUpdateStatus(selectedBundle.category, targetStatus, notes.trim() || undefined);
      setSelectedBundle(null);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="bg-white dark:bg-brand-dark-surface p-5 rounded-2xl border border-gray-100 dark:border-brand-dark-border shadow-sm space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-bold text-gray-900 dark:text-gray-100">
              Need Resolution Progress
            </h4>
            <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-teal-50 dark:bg-teal-950/40 text-brand-primary dark:text-teal-300">
              {resolvedNeeds} of {totalNeeds} Resolved ({progressPercentage}%)
            </span>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            Track and confirm real resolution on each requirement individually.
          </p>
        </div>

        {!isOverallResolved && (
          <Button
            size="sm"
            variant="outline"
            onClick={hasAcceptedHelper ? onMarkOverallResolved : (onResolveIndependently || onMarkOverallResolved)}
            leftIcon={<CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />}
          >
            {hasAcceptedHelper
              ? "Confirm Request Resolved"
              : onResolveIndependently
              ? "Resolved Independently"
              : "Mark Request Resolved"}
          </Button>
        )}
      </div>

      {/* Progress Bar */}
      <div className="w-full bg-gray-100 dark:bg-brand-dark-muted rounded-full h-2.5 overflow-hidden">
        <div
          className="bg-brand-primary dark:bg-teal-400 h-2.5 rounded-full transition-all duration-500"
          style={{ width: `${Math.max(progressPercentage, 4)}%` }}
        />
      </div>

      {/* Need Chips */}
      <div className="flex flex-wrap gap-2 pt-1">
        {bundles.map((bundle, idx) => (
          <button
            key={idx}
            type="button"
            onClick={() => handleOpenStatusModal(bundle)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-gray-200 dark:border-brand-dark-border bg-gray-50/50 dark:bg-brand-dark-muted/20 hover:border-brand-primary/40 dark:hover:border-teal-400/40 transition-colors text-left"
          >
            <span className="text-xs font-semibold text-gray-800 dark:text-gray-200 capitalize">
              {bundle.item}
            </span>
            {getStatusBadge(bundle.status)}
          </button>
        ))}
      </div>

      {/* Interactive Status Update Modal */}
      {selectedBundle && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedBundle(null)}
          title={`Update Status: ${selectedBundle.item}`}
        >
          <div className="space-y-4">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Select the honest status for this requirement. A connection or chat indicates progress, but only you can confirm when your need is genuinely resolved.
            </p>

            <div className="space-y-2">
              <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">
                Available Lifecycle Statuses
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {(
                  hasAcceptedHelper
                    ? (["UNRESOLVED", "EXPLORING", "CONNECTED", "RESOLUTION_PENDING", "RESOLVED"] as NeedStatus[])
                    : (["UNRESOLVED", "EXPLORING"] as NeedStatus[])
                ).map((st) => (
                  <button
                    key={st}
                    type="button"
                    onClick={() => setTargetStatus(st)}
                    className={`px-3 py-2 rounded-lg text-xs font-semibold border transition-all text-center ${
                      targetStatus === st
                        ? "border-brand-primary bg-teal-50 dark:bg-teal-950/40 text-brand-primary dark:text-teal-300"
                        : "border-gray-200 dark:border-brand-dark-border bg-white dark:bg-brand-dark-surface text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-brand-dark-muted"
                    }`}
                  >
                    {st.replace("_", " ")}
                  </button>
                ))}
              </div>
              {!hasAcceptedHelper && (
                <p className="text-[11px] text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/30 p-2.5 rounded-lg border border-amber-200/60 dark:border-amber-800/40">
                  CONNECTED and RESOLUTION PENDING require an accepted helper connection. To close this request on your own, use the <strong>Resolved Independently</strong> button.
                </p>
              )}
            </div>

            <div className="space-y-1">
              <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">
                Optional Notes
              </label>
              <input
                type="text"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="e.g. Found PG via community recommendations"
                className="w-full text-xs px-3 py-2 rounded-lg border border-gray-200 dark:border-brand-dark-border bg-white dark:bg-brand-dark-surface focus:outline-none focus:ring-1 focus:ring-brand-primary"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setSelectedBundle(null)}
                disabled={isSubmitting}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={handleConfirmStatus}
                disabled={isSubmitting}
              >
                {isSubmitting ? "Saving..." : "Save Progress"}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
}
