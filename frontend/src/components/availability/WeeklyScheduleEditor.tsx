import React, { useState } from "react";
import { Plus, Trash2, Clock, Check, AlertCircle } from "lucide-react";
import {
  DAY_NAMES,
  type DayOfWeek,
  type HelperAvailabilitySlot,
  type HelperAvailabilitySlotCreate,
} from "@/types/availability";

interface Props {
  initialSlots?: HelperAvailabilitySlot[];
  onSave: (slots: HelperAvailabilitySlotCreate[]) => Promise<void>;
}

interface LocalSlot {
  id: string;
  day_of_week: DayOfWeek;
  start_time: string;
  end_time: string;
  is_recurring: boolean;
}

export const WeeklyScheduleEditor: React.FC<Props> = ({ initialSlots = [], onSave }) => {
  const [slots, setSlots] = useState<LocalSlot[]>(() =>
    initialSlots.map((s) => ({
      id: s.id,
      day_of_week: s.day_of_week,
      start_time: s.start_time.substring(0, 5),
      end_time: s.end_time.substring(0, 5),
      is_recurring: s.is_recurring,
    }))
  );
  const [selectedDay, setSelectedDay] = useState<DayOfWeek>(0);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const daySlots = slots.filter((s) => s.day_of_week === selectedDay);

  const handleAddSlot = () => {
    setError(null);
    setSuccess(false);
    const newSlot: LocalSlot = {
      id: `temp_${Date.now()}`,
      day_of_week: selectedDay,
      start_time: "09:00",
      end_time: "17:00",
      is_recurring: true,
    };
    setSlots((prev) => [...prev, newSlot]);
  };

  const handleRemoveSlot = (id: string) => {
    setSlots((prev) => prev.filter((s) => s.id !== id));
    setError(null);
    setSuccess(false);
  };

  const handleUpdateSlot = (id: string, field: "start_time" | "end_time", value: string) => {
    setSlots((prev) =>
      prev.map((s) => (s.id === id ? { ...s, [field]: value } : s))
    );
    setError(null);
    setSuccess(false);
  };

  const handleSave = async () => {
    setError(null);
    setSuccess(false);
    // Validate each slot start < end
    for (const s of slots) {
      if (s.start_time >= s.end_time) {
        setError(`On ${DAY_NAMES[s.day_of_week]}, start time must be before end time.`);
        return;
      }
    }

    try {
      setSaving(true);
      const payload: HelperAvailabilitySlotCreate[] = slots.map((s) => ({
        day_of_week: s.day_of_week,
        start_time: s.start_time.length === 5 ? `${s.start_time}:00` : s.start_time,
        end_time: s.end_time.length === 5 ? `${s.end_time}:00` : s.end_time,
        is_recurring: s.is_recurring,
      }));
      await onSave(payload);
      setSuccess(true);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to save schedule slots.";
      setError(msg);
    } finally {
      setSaving(false);
    }
  };

  const daysList: DayOfWeek[] = [0, 1, 2, 3, 4, 5, 6];

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-100 p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
            <Clock className="w-5 h-5 text-indigo-600" />
            Weekly Availability Schedule
          </h2>
          <p className="text-sm text-gray-500 mt-1">
            Specify the days and time blocks when you are generally available to assist newcomers.
          </p>
        </div>
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="inline-flex items-center px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg text-sm transition disabled:opacity-50"
        >
          {saving ? "Saving..." : success ? "Saved!" : "Save Schedule"}
        </button>
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
          <span>Weekly schedule updated successfully.</span>
        </div>
      )}

      {/* Day Tabs */}
      <div className="flex border-b border-gray-200 mb-6 overflow-x-auto pb-1 gap-1">
        {daysList.map((day) => {
          const count = slots.filter((s) => s.day_of_week === day).length;
          const isSelected = selectedDay === day;
          return (
            <button
              key={day}
              type="button"
              onClick={() => setSelectedDay(day)}
              className={`px-4 py-2.5 text-sm font-medium rounded-t-lg transition whitespace-nowrap flex items-center gap-2 ${
                isSelected
                  ? "bg-indigo-50 text-indigo-700 border-b-2 border-indigo-600 font-semibold"
                  : "text-gray-600 hover:text-gray-900 hover:bg-gray-50"
              }`}
            >
              {DAY_NAMES[day]}
              {count > 0 && (
                <span
                  className={`text-xs px-2 py-0.5 rounded-full ${
                    isSelected ? "bg-indigo-200 text-indigo-800" : "bg-gray-200 text-gray-700"
                  }`}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Slots for Selected Day */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold text-gray-800">
            {DAY_NAMES[selectedDay]} Time Slots
          </h3>
          <button
            type="button"
            onClick={handleAddSlot}
            className="inline-flex items-center gap-1.5 text-sm text-indigo-600 hover:text-indigo-800 font-medium"
          >
            <Plus className="w-4 h-4" />
            Add Window
          </button>
        </div>

        {daySlots.length === 0 ? (
          <div className="text-center py-8 bg-gray-50 rounded-lg border border-dashed border-gray-200">
            <Clock className="w-8 h-8 text-gray-400 mx-auto mb-2" />
            <p className="text-sm text-gray-500 font-medium">No availability configured for {DAY_NAMES[selectedDay]}</p>
            <button
              type="button"
              onClick={handleAddSlot}
              className="mt-2 text-sm text-indigo-600 hover:underline font-medium inline-block"
            >
              Add your first slot
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            {daySlots.map((slot) => (
              <div
                key={slot.id}
                className="flex items-center gap-4 p-3 bg-gray-50 border border-gray-200 rounded-lg"
              >
                <div className="flex items-center gap-2 flex-1">
                  <label className="text-xs text-gray-500 font-medium">From</label>
                  <input
                    type="time"
                    value={slot.start_time}
                    onChange={(e) => handleUpdateSlot(slot.id, "start_time", e.target.value)}
                    className="border border-gray-300 rounded px-2.5 py-1.5 text-sm text-gray-800 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
                  />
                  <span className="text-gray-400 font-medium">to</span>
                  <input
                    type="time"
                    value={slot.end_time}
                    onChange={(e) => handleUpdateSlot(slot.id, "end_time", e.target.value)}
                    className="border border-gray-300 rounded px-2.5 py-1.5 text-sm text-gray-800 bg-white focus:ring-2 focus:ring-indigo-500 outline-none"
                  />
                </div>
                <button
                  type="button"
                  onClick={() => handleRemoveSlot(slot.id)}
                  className="p-1.5 text-red-500 hover:text-red-700 hover:bg-red-50 rounded transition"
                  title="Remove slot"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
