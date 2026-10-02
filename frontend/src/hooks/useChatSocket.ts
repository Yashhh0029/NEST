import { useEffect, useRef, useState, useCallback } from "react";
import { ENV } from "@/config/env";
import { TOKEN_STORAGE_KEY } from "@/services/api";
import type { MessageItem } from "@/types/chat";

interface UseChatSocketOptions {
  conversationId?: string | null;
  onMessageReceived?: (message: MessageItem) => void;
}

export function useChatSocket({
  conversationId,
  onMessageReceived,
}: UseChatSocketOptions) {
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    if (!conversationId) return;

    const token = sessionStorage.getItem(TOKEN_STORAGE_KEY);
    if (!token) {
      setConnectionError("No authentication token available.");
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
        setConnectionError(null);

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

        // Reconnect if not cleanly closed or policy violation
        if (event.code !== 1000 && event.code !== 1008) {
          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, 3000);
        }
      };
    } catch {
      setConnectionError("Failed to initiate WebSocket connection.");
    }
  }, [conversationId, onMessageReceived]);

  useEffect(() => {
    connect();

    return () => {
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
    connectionError,
    sendRealtimeMessage,
  };
}
