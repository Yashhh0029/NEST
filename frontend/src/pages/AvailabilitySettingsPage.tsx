import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Clock } from "lucide-react";
import { availabilityService } from "@/services/availability";
import { CapacityControls } from "@/components/availability/CapacityControls";
import { WeeklyScheduleEditor } from "@/components/availability/WeeklyScheduleEditor";
import { CardSkeleton } from "@/components/ui/Skeleton";
import type {
  PublicAvailabilityProfile,
  HelperAvailabilitySlot,
  HelperAvailabilitySlotCreate,
  UpdateCapacityPayload,
} from "@/types/availability";

export function AvailabilitySettingsPage() {
  const [capacity, setCapacity] = useState<PublicAvailabilityProfile | null>(null);
  const [slots, setSlots] = useState<HelperAvailabilitySlot[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      setLoading(true);
      const [capData, slotData] = await Promise.all([
        availabilityService.getMyCapacity(),
        availabilityService.getMySlots(),
      ]);
      setCapacity(capData);
      setSlots(slotData);
    } catch {
      // Handled by component states
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleSaveCapacity = async (payload: UpdateCapacityPayload) => {
    const updated = await availabilityService.updateMyCapacity(payload);
    setCapacity(updated);
  };

  const handleSaveSlots = async (newSlots: HelperAvailabilitySlotCreate[]) => {
    const updated = await availabilityService.replaceMySlots(newSlots);
    setSlots(updated);
    // Refresh capacity status after slots update
    const freshCap = await availabilityService.getMyCapacity();
    setCapacity(freshCap);
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto py-6 space-y-6">
        <CardSkeleton />
        <CardSkeleton />
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto py-4 sm:py-6 space-y-6">
      {/* Top action row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link
            to="/profile"
            className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold font-heading text-gray-900 flex items-center gap-2">
              <Clock className="w-6 h-6 text-indigo-600" />
              Availability & Capacity
            </h1>
            <p className="text-sm text-gray-500">
              Manage your assistance schedule and prevent overload with real-time capacity derivation.
            </p>
          </div>
        </div>
      </div>

      {capacity && (
        <CapacityControls
          initialCapacity={capacity}
          onSave={handleSaveCapacity}
        />
      )}

      <WeeklyScheduleEditor
        initialSlots={slots}
        onSave={handleSaveSlots}
      />
    </div>
  );
}
export default AvailabilitySettingsPage;
