import { useState } from "react";
import type { HelperMatchItem } from "@/types/match";
import { Card } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { BlockConfirmModal } from "../safety/BlockConfirmModal";
import { ReportModal } from "../safety/ReportModal";
import {
  MapPin,
  Sparkles,
  UserPlus,
  CheckCircle2,
  Clock,
  XCircle,
  Loader2,
  Star,
  Flag,
  ShieldAlert,
} from "lucide-react";

export interface HelperCardProps {
  helper?: HelperMatchItem;
  requestId?: string;
  connectionStatus?: "IDLE" | "PENDING" | "ACCEPTED" | "DECLINED" | "CANCELLED" | string;
  onConnect?: (helperId: string) => Promise<void>;
  isConnecting?: boolean;
  onBlocked?: (helperId: string) => void;
}

export function HelperCard({
  helper,
  connectionStatus = "IDLE",
  onConnect,
  isConnecting = false,
  onBlocked,
}: HelperCardProps) {
  const [showBlockModal, setShowBlockModal] = useState(false);
  const [showReportModal, setShowReportModal] = useState(false);
  const [isBlocked, setIsBlocked] = useState(false);

  if (!helper) {
    return (
      <Card className="p-6 border-dashed text-center text-sm text-gray-500 dark:text-gray-400">
        Helper match component will render when real matches are generated.
      </Card>
    );
  }

  if (isBlocked) {
    return (
      <Card className="p-4 border-dashed border-gray-300 dark:border-brand-dark-border bg-gray-50 dark:bg-brand-dark-muted/20 text-center text-xs text-gray-500">
        <span className="font-semibold text-gray-700 dark:text-gray-300">
          {helper.name}
        </span>{" "}
        has been blocked and excluded from future matches.
      </Card>
    );
  }

  const handleConnectClick = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onConnect && !isConnecting && connectionStatus === "IDLE") {
      await onConnect(helper.user_id);
    }
  };

  return (
    <Card hover className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-teal-100 dark:bg-brand-dark-muted/60 text-brand-primary dark:text-teal-300 flex items-center justify-center font-bold text-lg font-heading">
            {helper.name.charAt(0)}
          </div>
          <div>
            <h4 className="font-bold text-gray-900 dark:text-gray-100 font-heading">
              {helper.name}
            </h4>
            <div className="flex items-center gap-2">
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {helper.headline || "Community Helper"}
              </p>
              {helper.is_available_for_help === false && (
                <span className="text-[10px] bg-gray-100 dark:bg-brand-dark-muted px-1.5 py-0.5 rounded text-gray-500 font-medium">
                  Not accepting requests
                </span>
              )}
            </div>
            <div className="mt-1 flex items-center gap-1.5 text-xs">
              {helper.dimension_statuses?.reputation === "ACTIVE" &&
              helper.scores?.reputation_score != null ? (
                <span className="inline-flex items-center gap-1 font-semibold text-amber-600 dark:text-amber-400">
                  <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                  {(1.0 + helper.scores.reputation_score * 4.0).toFixed(1)}
                  <span className="text-gray-400 font-normal">rating</span>
                </span>
              ) : (
                <span className="text-gray-400 text-[11px]">
                  No reviews yet
                </span>
              )}
            </div>
          </div>
        </div>

        {helper.scores?.final_score != null && (
          <div className="text-right">
            <span className="text-lg font-extrabold text-brand-primary dark:text-teal-400 font-heading">
              {Math.round(helper.scores.final_score * 100)}%
            </span>
            <span className="block text-[10px] text-gray-400 uppercase tracking-wider font-semibold">
              Match Score
            </span>
          </div>
        )}
      </div>

      {(helper.area || helper.city) && (
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-gray-600 dark:text-gray-300">
          <div className="flex items-center gap-1.5">
            <MapPin className="w-3.5 h-3.5 text-brand-primary shrink-0" />
            <span>{[helper.area, helper.city].filter(Boolean).join(", ")}</span>
          </div>
          {helper.distance_km != null && (
            <span className="text-gray-400">({helper.distance_km.toFixed(1)} km away)</span>
          )}
          {helper.route_info?.estimated_travel_time_minutes != null && (
            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-teal-800 dark:text-teal-300 bg-teal-50 dark:bg-brand-dark-muted/40 px-2 py-0.5 rounded-md border border-teal-200/50 dark:border-teal-800/40">
              🚗 ~{Math.round(helper.route_info.estimated_travel_time_minutes)} min drive
            </span>
          )}
        </div>
      )}

      {helper.bio && (
        <p className="text-xs text-gray-600 dark:text-gray-300 line-clamp-2">
          {helper.bio}
        </p>
      )}

      {/* Skills */}
      <div className="flex flex-wrap gap-1">
        {helper.skills.map((skill, idx) => (
          <Badge key={idx} variant="primary" size="sm">
            {skill}
          </Badge>
        ))}
      </div>

      {/* Match Reasons */}
      {helper.reasons && helper.reasons.length > 0 && (
        <div className="p-3 rounded-xl bg-teal-50/60 dark:bg-brand-dark-muted/30 border border-teal-100 dark:border-brand-dark-border text-xs space-y-1">
          <div className="flex items-center gap-1 font-semibold text-brand-primary dark:text-teal-300">
            <Sparkles className="w-3 h-3 text-amber-500" />
            Why this match?
          </div>
          {helper.reasons.map((reason, idx) => (
            <p key={idx} className="text-gray-600 dark:text-gray-300">
              • <strong className="text-gray-800 dark:text-gray-200">{reason.title}:</strong>{" "}
              {reason.explanation}
            </p>
          ))}
        </div>
      )}

      {/* Connection Action */}
      <div className="pt-2 flex items-center justify-between">
        <span className="text-[11px] text-gray-400">
          {connectionStatus === "ACCEPTED"
            ? "Connection active"
            : connectionStatus === "PENDING"
            ? "Request pending helper review"
            : "Connect to initiate direct assistance"}
        </span>

        {connectionStatus === "ACCEPTED" ? (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 text-emerald-700 dark:text-emerald-400 text-xs font-semibold border border-emerald-200/60 dark:border-emerald-800/40">
            <CheckCircle2 className="w-3.5 h-3.5" />
            Connected
          </span>
        ) : connectionStatus === "PENDING" ? (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-amber-50 dark:bg-amber-950/30 text-amber-700 dark:text-amber-400 text-xs font-semibold border border-amber-200/60 dark:border-amber-800/40">
            <Clock className="w-3.5 h-3.5" />
            Requested
          </span>
        ) : connectionStatus === "DECLINED" ? (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-gray-100 dark:bg-brand-dark-muted text-gray-500 text-xs font-medium">
            <XCircle className="w-3.5 h-3.5" />
            Declined
          </span>
        ) : (
          <Button
            variant="primary"
            size="sm"
            onClick={handleConnectClick}
            disabled={isConnecting || helper.is_available_for_help === false}
            isLoading={isConnecting}
            leftIcon={
              isConnecting ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <UserPlus className="w-3.5 h-3.5" />
              )
            }
          >
            {isConnecting ? "Sending..." : "Connect"}
          </Button>
        )}
      </div>

      {/* Safety Actions & Modals */}
      <div className="flex items-center justify-end gap-2 pt-1 border-t border-gray-100 dark:border-brand-dark-border/40 text-xs">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setShowReportModal(true);
          }}
          className="inline-flex items-center gap-1 text-[11px] text-gray-400 hover:text-amber-600 dark:hover:text-amber-400 transition-colors"
          title="Report user"
        >
          <Flag className="w-3 h-3" />
          <span>Report</span>
        </button>
        <span className="text-gray-300 dark:text-gray-700">•</span>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setShowBlockModal(true);
          }}
          className="inline-flex items-center gap-1 text-[11px] text-gray-400 hover:text-rose-600 dark:hover:text-rose-400 transition-colors"
          title="Block user"
        >
          <ShieldAlert className="w-3 h-3" />
          <span>Block</span>
        </button>
      </div>

      {showBlockModal && (
        <BlockConfirmModal
          isOpen={showBlockModal}
          targetUserId={helper.user_id}
          targetName={helper.name}
          onClose={() => setShowBlockModal(false)}
          onSuccess={() => {
            setIsBlocked(true);
            onBlocked?.(helper.user_id);
          }}
        />
      )}

      {showReportModal && (
        <ReportModal
          isOpen={showReportModal}
          targetUserId={helper.user_id}
          targetName={helper.name}
          onClose={() => setShowReportModal(false)}
        />
      )}
    </Card>
  );
}
