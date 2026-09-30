export type DayOfWeek = 0 | 1 | 2 | 3 | 4 | 5 | 6;

export const DAY_NAMES: Record<DayOfWeek, string> = {
  0: 'Monday',
  1: 'Tuesday',
  2: 'Wednesday',
  3: 'Thursday',
  4: 'Friday',
  5: 'Saturday',
  6: 'Sunday',
};

export type AvailabilityStatus = 'AVAILABLE' | 'AT_CAPACITY' | 'NOT_ACCEPTING';

export interface HelperAvailabilitySlot {
  id: string;
  user_id: string;
  day_of_week: DayOfWeek;
  start_time: string; // HH:MM:SS or HH:MM
  end_time: string;   // HH:MM:SS or HH:MM
  is_recurring: boolean;
  effective_date?: string | null;
  created_at: string;
}

export interface HelperAvailabilitySlotCreate {
  day_of_week: DayOfWeek;
  start_time: string;
  end_time: string;
  is_recurring?: boolean;
  effective_date?: string | null;
}

export interface PublicAvailabilityProfile {
  user_id: string;
  helper_timezone: string;
  timezone?: string;
  max_weekly_sessions?: number | null;
  accepting_sessions?: boolean;
  current_status: AvailabilityStatus;
  availability_badge: string;
  available_days?: number[];
  available_time_ranges?: string[];
  detailed_slots?: HelperAvailabilitySlot[];
}

export interface UpdateCapacityPayload {
  helper_timezone?: string;
  timezone?: string;
  max_weekly_sessions?: number | null;
  accepting_sessions?: boolean;
}

