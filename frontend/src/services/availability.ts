import { api } from "./api";
import type {
  HelperAvailabilitySlot,
  HelperAvailabilitySlotCreate,
  PublicAvailabilityProfile,
  UpdateCapacityPayload,
} from "@/types/availability";

export const availabilityService = {
  /**
   * Get current helper's configured availability slots.
   */
  async getMySlots(): Promise<HelperAvailabilitySlot[]> {
    const { data } = await api.get<any>("/api/availability/slots/me");
    if (Array.isArray(data)) {
      return data;
    }
    return data?.slots ?? [];
  },

  /**
   * Bulk replace weekly availability schedule.
   */
  async replaceMySlots(slots: HelperAvailabilitySlotCreate[]): Promise<HelperAvailabilitySlot[]> {
    const { data } = await api.put<any>("/api/availability/slots", { slots });
    if (Array.isArray(data)) {
      return data;
    }
    return data?.slots ?? [];
  },

  /**
   * Get helper's current capacity configuration and real-time status.
   */
  async getMyCapacity(): Promise<PublicAvailabilityProfile> {
    const { data } = await api.get<any>("/api/availability/capacity/me");
    const currentStatus = data.current_status || data.capacity_status || "AVAILABLE";
    const badge =
      data.availability_badge ||
      (currentStatus === "AVAILABLE" ? "Available" : currentStatus === "AT_CAPACITY" ? "At Capacity" : "Not Accepting");

    return {
      user_id: data.user_id,
      helper_timezone: data.helper_timezone || data.timezone || "Asia/Kolkata",
      timezone: data.helper_timezone || data.timezone || "Asia/Kolkata",
      max_weekly_sessions: data.max_weekly_sessions,
      accepting_sessions: data.accepting_sessions ?? (currentStatus !== "NOT_ACCEPTING"),
      current_status: currentStatus,
      availability_badge: badge,
      detailed_slots: data.slots || data.detailed_slots || [],
    };
  },

  /**
   * Update capacity settings (timezone, max weekly hours, max monthly sessions, is_accepting).
   */
  async updateMyCapacity(payload: UpdateCapacityPayload): Promise<PublicAvailabilityProfile> {
    const { data } = await api.put<any>("/api/availability/capacity", payload);
    const currentStatus = data.current_status || data.capacity_status || "AVAILABLE";
    const badge =
      data.availability_badge ||
      (currentStatus === "AVAILABLE" ? "Available" : currentStatus === "AT_CAPACITY" ? "At Capacity" : "Not Accepting");

    return {
      user_id: data.user_id,
      helper_timezone: data.helper_timezone || data.timezone || "Asia/Kolkata",
      timezone: data.helper_timezone || data.timezone || "Asia/Kolkata",
      max_weekly_sessions: data.max_weekly_sessions,
      accepting_sessions: data.accepting_sessions ?? (currentStatus !== "NOT_ACCEPTING"),
      current_status: currentStatus,
      availability_badge: badge,
      detailed_slots: data.slots || data.detailed_slots || [],
    };
  },

  /**
   * Get public or connected availability profile for any helper.
   * If connected, server returns detailed slots; otherwise returns coarse available days/time ranges.
   */
  async getUserAvailability(userId: string): Promise<PublicAvailabilityProfile> {
    const { data } = await api.get<PublicAvailabilityProfile>(`/api/availability/user/${userId}`);
    return data;
  },
};
