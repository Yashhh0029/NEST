import { useEffect, useRef, useState, useCallback } from "react";
import { ENV } from "@/config/env";
import { TOKEN_STORAGE_KEY } from "@/services/api";
import { refreshCoordinator } from "@/services/refreshCoordinator";
import type { MessageItem } from "@/types/chat";

interface UseChatSocketOptions {
  conversationId?: string | null;
  onMessageReceived?: (message: MessageItem) => void;
  onPresenceReceived?: (presence: { user_id: string; is_online: boolean; last_seen_at?: string | null }) => void;
  onReconnect?: () => void;
}

export function useChatSocket({
  conversationId,
  onMessageReceived,
  onPresenceReceived,
  onReconnect,
}: UseChatSocketOptions) {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [isReconnecting, setIsReconnecting] = useState<boolean>(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const wasPreviouslyConnectedRef = useRef<boolean>(false);

  const connect = useCallback(() => {
    if (!conversationId) return;

    // Check visibility and network before connecting
    if (!refreshCoordinator.isOnline() || !refreshCoordinator.isTabVisible()) {
      return;
    }

    const token = sessionStorage.getItem(TOKEN_STORAGE_KEY);
    if (!token) {
      setConnectionError("No authentication token available.");
      return;
    }

    // Clean up existing socket if any
    if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
      return;
    }

    try {
      let baseUrl = ENV.WS_URL;
      if (!baseUrl) {
        if (ENV.API_URL.startsWith("http://") || ENV.API_URL.startsWith("https://")) {
          baseUrl = ENV.API_URL.replace(/^http/, "ws");
        } else if (typeof window !== "undefined") {
          const isSecure = window.location.protocol === "https:";
          const wsProtocol = isSecure ? "wss:" : "ws:";
          const host = window.location.host;
          baseUrl = `${wsProtocol}//${host}${ENV.API_URL || ""}`;
        } else {
          baseUrl = "ws://127.0.0.1:8000";
        }
      }
      const cleanBase = baseUrl.replace(/\/$/, "");
      const wsUrl = `${cleanBase}/ws/conversations/${conversationId}?token=${encodeURIComponent(token)}`;

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        setIsReconnecting(false);
        setConnectionError(null);

        // If this was a reconnection after disconnect, fire onReconnect callback to catch up
        if (wasPreviouslyConnectedRef.current) {
          onReconnect?.();
        }
        wasPreviouslyConnectedRef.current = true;

        // Setup ping heartbeat every 20 seconds
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: "ping" }));
          }
        }, 20000);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "message" && data.message) {
            onMessageReceived?.(data.message);
          } else if (data.type === "presence" && data.user_id) {
            onPresenceReceived?.({
              user_id: data.user_id,
              is_online: Boolean(data.is_online),
              last_seen_at: data.last_seen_at || null,
            });
          }
        } catch {
          // Ignore invalid parse
        }
      };

      ws.onerror = () => {
        setConnectionError("Real-time messaging connection error.");
      };

      ws.onclose = (event) => {
        setIsConnected(false);
        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = null;
        }

        // Reconnect with backoff if not cleanly closed or policy violation
        if (event.code !== 1000 && event.code !== 1008) {
          setIsReconnecting(true);
          reconnectTimeoutRef.current = setTimeout(() => {
            if (refreshCoordinator.isOnline() && refreshCoordinator.isTabVisible()) {
              connect();
            }
          }, 3000);
        }
      };
    } catch {
      setConnectionError("Failed to initiate WebSocket connection.");
    }
  }, [conversationId, onMessageReceived, onPresenceReceived, onReconnect]);

  useEffect(() => {
    connect();

    // Listen for tab visibility return and network reconnect to restore socket
    const unsubscribe = refreshCoordinator.subscribe((scopes) => {
      if (scopes.includes("visibility_visible") || scopes.includes("network_online")) {
        if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED) {
          connect();
        }
      }
    });

    return () => {
      unsubscribe();
      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      if (wsRef.current) {
        wsRef.current.close(1000, "Component unmounted");
        wsRef.current = null;
      }
    };
  }, [connect]);

  const sendRealtimeMessage = useCallback((content: string): boolean => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "message",
          content,
        })
      );
      return true;
    }
    return false;
  }, []);

  return {
    isConnected,
    isReconnecting,
    connectionError,
    sendRealtimeMessage,
    reconnect: connect,
  };
}
