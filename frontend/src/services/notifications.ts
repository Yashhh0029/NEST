import { api } from "./api";

export interface NotificationItem {
  id: string;
  user_id: string;
  request_id: string;
  notification_type: string;
  title: string;
  message: string;
  distance_km: number | null;
  request_status: string;
  is_read: boolean;
  created_at: string;
  read_at: string | null;
}

export interface NotificationListResponse {
  items: NotificationItem[];
  total: number;
  unread_count: number;
}

export interface UnreadCountResponse {
  unread_count: number;
}

export const notificationService = {
  getNotifications: async (limit: number = 20, skip: number = 0): Promise<NotificationListResponse> => {
    const response = await api.get<NotificationListResponse>("/api/notifications", {
      params: { limit, skip },
    });
    return response.data;
  },

  getUnreadCount: async (): Promise<number> => {
    const response = await api.get<UnreadCountResponse>("/api/notifications/unread-count");
    return response.data.unread_count;
  },

  markAsRead: async (notificationId: string): Promise<NotificationItem> => {
    const response = await api.patch<NotificationItem>(`/api/notifications/${notificationId}/read`);
    return response.data;
  },

  markAllAsRead: async (): Promise<{ message: string; marked_count: number }> => {
    const response = await api.post<{ message: string; marked_count: number }>("/api/notifications/mark-all-read");
    return response.data;
  },
};
