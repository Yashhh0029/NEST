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
    const { data } = await api.get<HelperAvailabilitySlot[]>("/api/v1/availability/slots/me");
    return data;
  },

  /**
   * Bulk replace weekly availability schedule.
   */
  async replaceMySlots(slots: HelperAvailabilitySlotCreate[]): Promise<HelperAvailabilitySlot[]> {
    const { data } = await api.put<HelperAvailabilitySlot[]>("/api/v1/availability/slots/me", slots);
    return data;
  },

  /**
   * Get helper's current capacity configuration and real-time status.
   */
  async getMyCapacity(): Promise<PublicAvailabilityProfile> {
    const { data } = await api.get<PublicAvailabilityProfile>("/api/v1/availability/capacity/me");
    return data;
  },

  /**
   * Update capacity settings (timezone, max weekly hours, max monthly sessions, is_accepting).
   */
  async updateMyCapacity(payload: UpdateCapacityPayload): Promise<PublicAvailabilityProfile> {
    const { data } = await api.put<PublicAvailabilityProfile>("/api/v1/availability/capacity/me", payload);
    return data;
  },

  /**
   * Get public or connected availability profile for any helper.
   * If connected, server returns detailed slots; otherwise returns coarse available days/time ranges.
   */
  async getUserAvailability(userId: string): Promise<PublicAvailabilityProfile> {
    const { data } = await api.get<PublicAvailabilityProfile>(`/api/v1/availability/user/${userId}`);
    return data;
  },
};
