import React, { useState } from "react";
import { Settings, Check, AlertCircle, Globe } from "lucide-react";
import type { PublicAvailabilityProfile, UpdateCapacityPayload } from "@/types/availability";

interface Props {
  initialCapacity: PublicAvailabilityProfile;
  onSave: (payload: UpdateCapacityPayload) => Promise<void>;
}

export const CapacityControls: React.FC<Props> = ({ initialCapacity, onSave }) => {
  const [timezone, setTimezone] = useState(
    initialCapacity.helper_timezone || initialCapacity.timezone || "Asia/Kolkata"
  );
  const [maxWeeklySessions, setMaxWeeklySessions] = useState<number | string>(
    initialCapacity.max_weekly_sessions ?? 3
  );
  const [isAccepting, setIsAccepting] = useState<boolean>(
    initialCapacity.accepting_sessions ?? (initialCapacity.current_status !== "NOT_ACCEPTING")
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    try {
      setSaving(true);
      const payload: UpdateCapacityPayload = {
        helper_timezone: timezone,
        timezone,
        max_weekly_sessions: maxWeeklySessions === "" ? null : Number(maxWeeklySessions),
        accepting_sessions: isAccepting,
      };
      await onSave(payload);
      setSuccess(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to update capacity preferences.";
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Settings className="w-5 h-5 text-indigo-600" />
            Assistance Capacity & Timezone
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            Control how many sessions you can take on and prevent scheduling burnout.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-gray-500">Live Status:</span>
          <span
            className={`px-2.5 py-1 rounded-full text-xs font-semibold ${
              initialCapacity.current_status === "AVAILABLE"
                ? "bg-green-100 text-green-800"
                : initialCapacity.current_status === "AT_CAPACITY"
                ? "bg-yellow-100 text-yellow-800"
                : "bg-red-100 text-red-800"
            }`}
          >
            {initialCapacity.availability_badge}
          </span>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-sm text-red-700">
          <AlertCircle className="w-4 h-4 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg flex items-center gap-2 text-sm text-green-700">
          <Check className="w-4 h-4 flex-shrink-0" />
          <span>Capacity settings updated successfully.</span>
        </div>
      )}

      <form onSubmit={handleSave} className="space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-1.5">
              <Globe className="w-4 h-4 text-gray-500" />
              Primary Timezone (IANA)
            </label>
            <select
              value={timezone}
              onChange={(e) => setTimezone(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-900 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
            >
              <option value="Asia/Kolkata">Asia/Kolkata (IST, UTC+5:30)</option>
              <option value="Asia/Dubai">Asia/Dubai (GST, UTC+4:00)</option>
              <option value="Asia/Singapore">Asia/Singapore (SGT, UTC+8:00)</option>
              <option value="Europe/London">Europe/London (GMT/BST)</option>
              <option value="America/New_York">America/New_York (EST/EDT)</option>
              <option value="America/Los_Angeles">America/Los_Angeles (PST/PDT)</option>
              <option value="UTC">UTC</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Currently Accepting New Assistance Sessions
            </label>
            <div className="flex items-center gap-3 mt-2">
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={isAccepting}
                  onChange={(e) => setIsAccepting(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-indigo-600"></div>
              </label>
              <span className="text-sm font-medium text-gray-700">
                {isAccepting ? "Accepting proposals" : "Paused / Not accepting"}
              </span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Max Weekly Sessions
            </label>
            <input
              type="number"
              min="1"
              max="20"
              value={maxWeeklySessions}
              onChange={(e) => setMaxWeeklySessions(e.target.value)}
              className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm text-gray-900 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
            />
            <p className="text-xs text-gray-500 mt-1">
              Maximum confirmed assistance sessions in any rolling 7-day window (1-20).
            </p>
          </div>
        </div>

        <div className="flex justify-end pt-4 border-t border-gray-100">
          <button
            type="submit"
            disabled={saving}
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg text-sm transition disabled:opacity-50"
          >
            {saving ? "Saving Preferences..." : "Save Capacity Preferences"}
          </button>
        </div>
      </form>
    </div>
  );
};
