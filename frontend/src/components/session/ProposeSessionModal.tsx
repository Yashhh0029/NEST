import React, { useState } from "react";
import { X, Calendar, Clock, MapPin, Video, AlertCircle } from "lucide-react";
import type { SessionCreate, SessionModality } from "@/types/session";

interface Props {
  requestId: string;
  recipientId: string;
  recipientName?: string;
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (payload: SessionCreate) => Promise<void>;
}

export const ProposeSessionModal: React.FC<Props> = ({
  requestId,
  recipientId,
  recipientName = "Helper",
  isOpen,
  onClose,
  onSubmit,
}) => {
  const [title, setTitle] = useState("Assistance Session");
  const [modality, setModality] = useState<SessionModality>("IN_PERSON");
  const [dateStr, setDateStr] = useState("");
  const [timeStr, setTimeStr] = useState("10:00");
  const [duration, setDuration] = useState<number>(60);
  const [meetingPlaceId, setMeetingPlaceId] = useState("");
  const [meetingUrl, setMeetingUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!title.trim()) {
      setError("Please provide a title for the session.");
      return;
    }
    if (!dateStr) {
      setError("Please select a date for the session.");
      return;
    }

    const scheduledDate = new Date(`${dateStr}T${timeStr}:00`);
    if (isNaN(scheduledDate.getTime())) {
      setError("Invalid date or time selected.");
      return;
    }
    if (scheduledDate.getTime() < Date.now()) {
      setError("Scheduled time must be in the future.");
      return;
    }

    if (modality === "IN_PERSON") {
      if (!meetingPlaceId.trim()) {
        setError("Please enter a Google Places ID or select an approved public meeting venue.");
        return;
      }
    } else {
      if (!meetingUrl.trim() || !meetingUrl.startsWith("https://")) {
        setError("Please provide a secure HTTPS meeting URL (e.g. Google Meet, Zoom, MS Teams).");
        return;
      }
    }

    try {
      setSubmitting(true);
      const payload: SessionCreate = {
        request_id: requestId,
        recipient_id: recipientId,
        title: title.trim(),
        modality,
        scheduled_start: scheduledDate.toISOString(),
        duration_minutes: duration,
        meeting_place_id: modality === "IN_PERSON" ? meetingPlaceId.trim() : null,
        meeting_url: modality === "REMOTE" ? meetingUrl.trim() : null,
      };
      await onSubmit(payload);
      onClose();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to propose assistance session.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div className="flex items-center gap-2">
            <Calendar className="w-5 h-5 text-indigo-600" />
            <h3 className="font-bold text-gray-900 text-lg">Propose Assistance Session</h3>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-sm text-red-700">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Session Title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Apartment Viewing / Area Orientation"
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 outline-none"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Modality
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setModality("IN_PERSON")}
                className={`py-2 px-3 rounded-lg border text-sm font-medium flex items-center justify-center gap-2 transition ${
                  modality === "IN_PERSON"
                    ? "border-indigo-600 bg-indigo-50 text-indigo-700"
                    : "border-gray-200 hover:bg-gray-50 text-gray-700"
                }`}
              >
                <MapPin className="w-4 h-4" />
                In-Person Venue
              </button>
              <button
                type="button"
                onClick={() => setModality("REMOTE")}
                className={`py-2 px-3 rounded-lg border text-sm font-medium flex items-center justify-center gap-2 transition ${
                  modality === "REMOTE"
                    ? "border-indigo-600 bg-indigo-50 text-indigo-700"
                    : "border-gray-200 hover:bg-gray-50 text-gray-700"
                }`}
              >
                <Video className="w-4 h-4" />
                Remote Video / Call
              </button>
            </div>
          </div>

          {modality === "IN_PERSON" ? (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Public Meeting Place (Google Place ID)
              </label>
              <input
                type="text"
                value={meetingPlaceId}
                onChange={(e) => setMeetingPlaceId(e.target.value)}
                placeholder="Google Place ID of approved cafe, library, or transit hub"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 outline-none"
                required
              />
              <p className="text-xs text-gray-500 mt-1">
                Safety policy: In-person sessions must occur at approved public venues within 25 km of the request area.
              </p>
            </div>
          ) : (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Secure Meeting URL (HTTPS)
              </label>
              <input
                type="url"
                value={meetingUrl}
                onChange={(e) => setMeetingUrl(e.target.value)}
                placeholder="https://meet.google.com/..."
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 outline-none"
                required
              />
              <p className="text-xs text-gray-500 mt-1">
                Privacy policy: The URL is encrypted and will be visible to {recipientName} once confirmed.
              </p>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="propose-date" className="block text-sm font-medium text-gray-700 mb-1">
                Date
              </label>
              <input
                id="propose-date"
                type="date"
                value={dateStr}
                min={new Date().toISOString().split("T")[0]}
                onChange={(e) => setDateStr(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 outline-none"
                required
              />
            </div>
            <div>
              <label htmlFor="propose-time" className="block text-sm font-medium text-gray-700 mb-1">
                Start Time
              </label>
              <input
                id="propose-time"
                type="time"
                value={timeStr}
                onChange={(e) => setTimeStr(e.target.value)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-900 focus:ring-2 focus:ring-indigo-500 outline-none"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-1.5">
              <Clock className="w-4 h-4 text-gray-500" />
              Duration
            </label>
            <select
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value))}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-900 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
            >
              <option value={30}>30 Minutes</option>
              <option value={45}>45 Minutes</option>
              <option value={60}>60 Minutes (1 Hour)</option>
              <option value={90}>90 Minutes (1.5 Hours)</option>
              <option value={120}>120 Minutes (2 Hours)</option>
            </select>
          </div>

          <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-100 rounded-lg transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-5 py-2 text-sm font-medium bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg transition disabled:opacity-50"
            >
              {submitting ? "Proposing..." : "Send Proposal"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
