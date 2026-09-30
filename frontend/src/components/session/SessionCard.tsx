import React, { useState } from "react";
import {
  Calendar,
  Clock,
  MapPin,
  Video,
  CheckCircle,
  XCircle,
  RotateCcw,
  Download,
  AlertTriangle,
  ExternalLink,
} from "lucide-react";
import type { AssistanceSession } from "@/types/session";

interface Props {
  session: AssistanceSession;
  currentUserId: string;
  onAccept?: (sessionId: string) => Promise<void>;
  onDecline?: (sessionId: string) => Promise<void>;
  onCancel?: (sessionId: string, reason: string) => Promise<void>;
  onComplete?: (sessionId: string) => Promise<void>;
  onRescheduleClick?: (session: AssistanceSession) => void;
  onDownloadIcs?: (sessionId: string, title: string) => Promise<void>;
}

export const SessionCard: React.FC<Props> = ({
  session,
  currentUserId,
  onAccept,
  onDecline,
  onCancel,
  onComplete,
  onRescheduleClick,
  onDownloadIcs,
}) => {
  const [cancelling, setCancelling] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [actionLoading, setActionLoading] = useState(false);

  const isProposer = session.proposer_id === currentUserId;
  const isRecipient = session.recipient_id === currentUserId;

  const canAccept =
    isRecipient &&
    (session.status === "PROPOSED" || session.status === "RESCHEDULE_PROPOSED");

  const canReschedule =
    session.status === "CONFIRMED" || session.status === "PROPOSED";

  const canCancel =
    session.status === "PROPOSED" ||
    session.status === "RESCHEDULE_PROPOSED" ||
    session.status === "CONFIRMED";

  const isRequesterDone = !!session.requester_completed_at;
  const isHelperDone = !!session.helper_completed_at;

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(undefined, {
        weekday: "short",
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return isoString;
    }
  };

  const formatTime = (isoString: string) => {
    try {
      const d = new Date(isoString);
      return d.toLocaleTimeString(undefined, {
        hour: "2-digit",
        minute: "2-digit",
      });
    } catch {
      return "";
    }
  };

  const getStatusBadge = () => {
    switch (session.status) {
      case "CONFIRMED":
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-green-100 text-green-800">Confirmed</span>;
      case "PROPOSED":
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-blue-100 text-blue-800">Proposal Pending</span>;
      case "RESCHEDULE_PROPOSED":
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-amber-100 text-amber-800">Reschedule Pending</span>;
      case "COMPLETED":
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-purple-100 text-purple-800">Completed</span>;
      case "CANCELLED":
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800">Cancelled</span>;
      case "DECLINED":
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-red-100 text-red-800">Declined</span>;
      default:
        return <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-gray-100 text-gray-800">{session.status}</span>;
    }
  };

  const handleAction = async (fn?: () => Promise<unknown> | void | undefined) => {
    if (!fn) return;
    try {
      setActionLoading(true);
      await fn();
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-5 hover:border-gray-300 transition space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h4 className="font-semibold text-gray-900 text-base flex items-center gap-2">
            {session.modality === "IN_PERSON" ? (
              <MapPin className="w-4 h-4 text-indigo-600 flex-shrink-0" />
            ) : (
              <Video className="w-4 h-4 text-indigo-600 flex-shrink-0" />
            )}
            {session.title}
          </h4>
          <p className="text-xs text-gray-500 mt-0.5">
            {isProposer ? "You proposed this session" : "You were invited to this session"}
          </p>
        </div>
        {getStatusBadge()}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm text-gray-700 bg-gray-50 p-3 rounded-lg">
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-gray-400 flex-shrink-0" />
          <span>{formatDate(session.scheduled_start)}</span>
        </div>
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-gray-400 flex-shrink-0" />
          <span>
            {formatTime(session.scheduled_start)} ({session.duration_minutes} mins, {session.timezone})
          </span>
        </div>
        {session.modality === "IN_PERSON" ? (
          <div className="sm:col-span-2 flex items-start gap-2">
            <MapPin className="w-4 h-4 text-gray-400 flex-shrink-0 mt-0.5" />
            <div className="text-xs text-gray-600">
              <span className="font-semibold text-gray-800">{session.meeting_place_name || "Public Venue"}</span>
              {session.meeting_place_address && <p>{session.meeting_place_address}</p>}
            </div>
          </div>
        ) : (
          <div className="sm:col-span-2 flex items-center gap-2">
            <Video className="w-4 h-4 text-gray-400 flex-shrink-0" />
            {session.meeting_url ? (
              <a
                href={session.meeting_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-indigo-600 hover:underline flex items-center gap-1 font-medium"
              >
                Join Secure Meeting Room <ExternalLink className="w-3 h-3" />
              </a>
            ) : (
              <span className="text-xs text-gray-500 italic">
                Meeting link encrypted — will be revealed upon session confirmation
              </span>
            )}
          </div>
        )}
      </div>

      {/* Dual Completion Indicator for Confirmed or Completed */}
      {(session.status === "CONFIRMED" || session.status === "COMPLETED") && (
        <div className="border-t border-gray-100 pt-3">
          <div className="text-xs font-semibold text-gray-600 mb-1.5 flex items-center justify-between">
            <span>Dual-Confirmation Status:</span>
            {session.status === "COMPLETED" && (
              <span className="text-purple-700 font-bold">Both Parties Confirmed Complete</span>
            )}
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div
              className={`p-2 rounded flex items-center gap-1.5 ${
                isRequesterDone ? "bg-green-50 text-green-700 font-medium" : "bg-gray-50 text-gray-500"
              }`}
            >
              {isRequesterDone ? <CheckCircle className="w-3.5 h-3.5" /> : <Clock className="w-3.5 h-3.5" />}
              Requester: {isRequesterDone ? "Marked Complete" : "Pending Confirmation"}
            </div>
            <div
              className={`p-2 rounded flex items-center gap-1.5 ${
                isHelperDone ? "bg-green-50 text-green-700 font-medium" : "bg-gray-50 text-gray-500"
              }`}
            >
              {isHelperDone ? <CheckCircle className="w-3.5 h-3.5" /> : <Clock className="w-3.5 h-3.5" />}
              Helper: {isHelperDone ? "Marked Complete" : "Pending Confirmation"}
            </div>
          </div>
        </div>
      )}

      {/* Cancellation Reason if cancelled */}
      {session.status === "CANCELLED" && session.cancellation_reason && (
        <div className="p-2.5 bg-red-50 text-red-800 text-xs rounded border border-red-100 flex items-start gap-1.5">
          <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
          <span>Reason: {session.cancellation_reason}</span>
        </div>
      )}

      {/* Cancellation Input Box */}
      {cancelling && (
        <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg space-y-2">
          <label className="block text-xs font-semibold text-gray-700">
            Mandatory Cancellation Reason:
          </label>
          <input
            type="text"
            value={cancelReason}
            onChange={(e) => setCancelReason(e.target.value)}
            placeholder="Please specify why you are cancelling..."
            className="w-full border border-gray-300 rounded px-2.5 py-1.5 text-xs text-gray-900 bg-white"
          />
          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={() => setCancelling(false)}
              className="px-2.5 py-1 text-xs text-gray-600 hover:bg-gray-200 rounded"
            >
              Back
            </button>
            <button
              type="button"
              disabled={!cancelReason.trim() || actionLoading}
              onClick={() =>
                handleAction(async () => {
                  if (onCancel) await onCancel(session.id, cancelReason);
                  setCancelling(false);
                })
              }
              className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded disabled:opacity-50"
            >
              Confirm Cancellation
            </button>
          </div>
        </div>
      )}

      {/* Action Buttons */}
      {!cancelling && (
        <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-gray-100">
          <div className="flex items-center gap-2">
            {canAccept && (
              <>
                <button
                  type="button"
                  disabled={actionLoading}
                  onClick={() => handleAction(() => onAccept?.(session.id))}
                  className="inline-flex items-center gap-1 px-3 py-1.5 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-semibold transition disabled:opacity-50"
                >
                  <CheckCircle className="w-3.5 h-3.5" />
                  Accept
                </button>
                <button
                  type="button"
                  disabled={actionLoading}
                  onClick={() => handleAction(() => onDecline?.(session.id))}
                  className="inline-flex items-center gap-1 px-3 py-1.5 bg-red-50 hover:bg-red-100 text-red-700 rounded-lg text-xs font-semibold transition disabled:opacity-50"
                >
                  <XCircle className="w-3.5 h-3.5" />
                  Decline
                </button>
              </>
            )}

            {session.status === "CONFIRMED" && (
              <button
                type="button"
                disabled={actionLoading}
                onClick={() => handleAction(() => onComplete?.(session.id))}
                className="inline-flex items-center gap-1 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold transition disabled:opacity-50"
              >
                <CheckCircle className="w-3.5 h-3.5" />
                Mark Complete
              </button>
            )}

            {session.status === "CONFIRMED" && onDownloadIcs && (
              <button
                type="button"
                onClick={() => onDownloadIcs(session.id, session.title)}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-xs font-medium transition"
                title="Download RFC 5545 iCalendar file"
              >
                <Download className="w-3.5 h-3.5" />
                Add to Calendar
              </button>
            )}
          </div>

          <div className="flex items-center gap-2">
            {canReschedule && onRescheduleClick && (
              <button
                type="button"
                onClick={() => onRescheduleClick(session)}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 text-indigo-600 hover:bg-indigo-50 rounded-lg text-xs font-medium transition"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                Reschedule
              </button>
            )}

            {canCancel && onCancel && (
              <button
                type="button"
                onClick={() => setCancelling(true)}
                className="inline-flex items-center gap-1 px-2.5 py-1.5 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg text-xs font-medium transition"
              >
                Cancel
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
