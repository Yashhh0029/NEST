import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { Bell, CheckCheck, MapPin, ExternalLink, Loader2 } from "lucide-react";
import { notificationService, type NotificationItem } from "@/services/notifications";

import { ENV } from "@/config/env";

export function NotificationBell() {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const fetchUnreadCount = async () => {
    try {
      const count = await notificationService.getUnreadCount();
      setUnreadCount(count);
    } catch {
      // silently ignore network issues
    }
  };

  const fetchNotificationsList = async () => {
    setIsLoading(true);
    try {
      const res = await notificationService.getNotifications(15, 0);
      setNotifications(res.items);
      setUnreadCount(res.unread_count);
    } catch {
      // silently ignore network issues
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 30000);

    // WebSocket real-time subscription
    let ws: WebSocket | null = null;
    const token = sessionStorage.getItem("nest_access_token");
    if (token) {
      try {
        const base = ENV.API_URL || window.location.origin;
        const wsUrl = base.replace(/^http/, "ws") + `/api/notifications/ws?token=${token}`;
        ws = new WebSocket(wsUrl);
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === "NEW_NOTIFICATION" && data.notification) {
              setNotifications((prev) => [data.notification, ...prev]);
              setUnreadCount((c) => c + 1);
            }
          } catch {
            // ignore
          }
        };
      } catch {
        // ignore ws failure, polling interval serves as fallback
      }
    }

    return () => {
      clearInterval(interval);
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    };
  }, []);

  const handleToggle = () => {
    if (!isOpen) {
      fetchNotificationsList();
    }
    setIsOpen(!isOpen);
  };

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  const handleNotificationClick = async (notif: NotificationItem) => {
    if (!notif.is_read) {
      try {
        await notificationService.markAsRead(notif.id);
        setNotifications((prev) =>
          prev.map((n) => (n.id === notif.id ? { ...n, is_read: true } : n))
        );
        setUnreadCount((c) => Math.max(0, c - 1));
      } catch {
        // ignore
      }
    }
    setIsOpen(false);
    navigate(`/requests?highlight=${notif.request_id}`);
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationService.markAllAsRead();
      setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
      setUnreadCount(0);
    } catch {
      // ignore
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={handleToggle}
        className="relative p-2 rounded-xl text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-brand-dark-card transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary"
        aria-label="View notifications"
        aria-expanded={isOpen}
      >
        <Bell className="w-5 h-5" />
        {unreadCount > 0 && (
          <span className="absolute top-1 right-1 min-w-[18px] h-[18px] px-1 bg-red-500 text-white text-[11px] font-bold rounded-full flex items-center justify-center animate-pulse">
            {unreadCount > 99 ? "99+" : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 max-h-[80vh] bg-white dark:bg-brand-dark-card rounded-2xl shadow-xl border border-gray-100 dark:border-brand-dark-border z-50 flex flex-col overflow-hidden animate-in fade-in-50 zoom-in-95 duration-100">
          <div className="p-3.5 border-b border-gray-100 dark:border-brand-dark-border flex items-center justify-between bg-gray-50/50 dark:bg-brand-dark/50">
            <div className="flex items-center gap-2">
              <span className="font-heading font-bold text-sm text-gray-900 dark:text-gray-100">
                Community Alerts
              </span>
              {unreadCount > 0 && (
                <span className="text-xs px-2 py-0.5 rounded-full bg-teal-100 dark:bg-teal-900/40 text-teal-700 dark:text-teal-300 font-semibold">
                  {unreadCount} new
                </span>
              )}
            </div>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-xs text-brand-primary dark:text-teal-400 hover:underline flex items-center gap-1 font-medium"
              >
                <CheckCheck className="w-3.5 h-3.5" />
                Mark all read
              </button>
            )}
          </div>

          <div className="overflow-y-auto max-h-[360px] divide-y divide-gray-100 dark:divide-brand-dark-border">
            {isLoading ? (
              <div className="p-6 flex flex-col items-center justify-center text-gray-400 text-xs gap-2">
                <Loader2 className="w-5 h-5 animate-spin text-brand-primary" />
                <span>Checking nearby alerts...</span>
              </div>
            ) : notifications.length === 0 ? (
              <div className="p-8 text-center text-gray-400 text-xs">
                No nearby notifications right now.
              </div>
            ) : (
              notifications.map((notif) => (
                <div
                  key={notif.id}
                  onClick={() => handleNotificationClick(notif)}
                  className={`p-3.5 hover:bg-gray-50 dark:hover:bg-brand-dark/40 cursor-pointer transition-colors flex flex-col gap-1.5 ${
                    !notif.is_read
                      ? "bg-teal-50/40 dark:bg-teal-950/20 border-l-4 border-brand-primary"
                      : ""
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <span className="text-xs font-semibold text-gray-900 dark:text-gray-100">
                      {notif.title}
                    </span>
                    {notif.distance_km !== null && (
                      <span className="shrink-0 text-[11px] font-medium px-2 py-0.5 rounded bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 flex items-center gap-1">
                        <MapPin className="w-3 h-3" />
                        {notif.distance_km} km
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-600 dark:text-gray-300 line-clamp-2">
                    {notif.message}
                  </p>
                  <div className="flex items-center justify-between text-[10px] text-gray-400 pt-1">
                    <span className="capitalize px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500">
                      Status: {notif.request_status.toLowerCase()}
                    </span>
                    <span className="flex items-center gap-1 text-brand-primary dark:text-teal-400 font-medium">
                      View Request <ExternalLink className="w-3 h-3" />
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
