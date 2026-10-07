/**
 * Centralized Refresh Coordinator for NEST
 * 
 * Manages:
 * - Scoped data invalidation across components (requests, connections, sessions, notifications, etc.)
 * - In-flight request deduplication to prevent duplicate concurrent network calls
 * - Browser tab visibility tracking (document.visibilityState)
 * - Browser network online/offline tracking (navigator.onLine)
 */

export type RefreshScope =
  | "requests"
  | "nearby_requests"
  | "connections"
  | "sessions"
  | "notifications"
  | "profile"
  | "chat"
  | "reviews"
  | "community"
  | string;

type ListenerCallback = (scopes: string[]) => void;

class RefreshCoordinator {
  private listeners = new Set<ListenerCallback>();
  private inFlightRequests = new Map<string, Promise<any>>();
  private isVisible = typeof document !== "undefined" ? document.visibilityState === "visible" : true;
  private isOnlineStatus = typeof navigator !== "undefined" ? navigator.onLine : true;

  constructor() {
    if (typeof window !== "undefined") {
      this.initVisibilityListener();
      this.initNetworkListeners();
    }
  }

  private initVisibilityListener() {
    document.addEventListener("visibilitychange", () => {
      const nowVisible = document.visibilityState === "visible";
      const changed = this.isVisible !== nowVisible;
      this.isVisible = nowVisible;

      if (changed && nowVisible) {
        // Tab just became visible: notify subscribers to check staleness and refresh
        this.notify(["visibility_visible"]);
      } else if (changed && !nowVisible) {
        this.notify(["visibility_hidden"]);
      }
    });
  }

  private initNetworkListeners() {
    window.addEventListener("online", () => {
      this.isOnlineStatus = true;
      this.notify(["network_online"]);
    });

    window.addEventListener("offline", () => {
      this.isOnlineStatus = false;
      this.notify(["network_offline"]);
    });
  }

  /**
   * Check if tab is currently visible
   */
  public isTabVisible(): boolean {
    if (typeof document === "undefined") return true;
    return document.visibilityState === "visible";
  }

  /**
   * Check if browser is online
   */
  public isOnline(): boolean {
    if (typeof navigator === "undefined") return this.isOnlineStatus;
    return this.isOnlineStatus && navigator.onLine;
  }

  /**
   * Invalidate one or more scopes to trigger immediate refresh in active listeners.
   */
  public invalidate(scopes: string | string[]): void {
    const list = Array.isArray(scopes) ? scopes : [scopes];
    if (list.length === 0) return;
    this.notify(list);
  }

  /**
   * Subscribe to invalidation events.
   * If scopes is provided, callback is only called if at least one matching scope is invalidated.
   */
  public subscribe(
    callback: (invalidatedScopes: string[]) => void,
    scopes?: string[]
  ): () => void {
    const wrapper: ListenerCallback = (invalidated) => {
      if (!scopes || scopes.length === 0) {
        callback(invalidated);
        return;
      }
      const hasMatch = invalidated.some(
        (s) =>
          scopes.includes(s) ||
          s === "visibility_visible" ||
          s === "network_online" ||
          s === "all"
      );
      if (hasMatch) {
        callback(invalidated);
      }
    };

    this.listeners.add(wrapper);
    return () => {
      this.listeners.delete(wrapper);
    };
  }

  private notify(scopes: string[]): void {
    this.listeners.forEach((listener) => {
      try {
        listener(scopes);
      } catch (err) {
        // Prevent one faulty subscriber from breaking others
        console.error("RefreshCoordinator listener error:", err);
      }
    });
  }

  /**
   * Execute an async fetcher with in-flight request deduplication.
   * If an identical key is already being fetched, reuses the in-flight Promise.
   */
  public async executeDeduplicated<T>(
    key: string,
    fetcher: () => Promise<T>
  ): Promise<T> {
    const existing = this.inFlightRequests.get(key);
    if (existing) {
      return existing as Promise<T>;
    }

    const promise = (async () => {
      try {
        return await fetcher();
      } finally {
        this.inFlightRequests.delete(key);
      }
    })();

    this.inFlightRequests.set(key, promise);
    return promise;
  }

  /**
   * Clear an in-flight request by key (e.g. when cancelled or manually retried).
   */
  public clearInFlight(key: string): void {
    this.inFlightRequests.delete(key);
  }

  /**
   * Clear all in-flight requests (useful for tests or hard resets).
   */
  public clearAllInFlight(): void {
    this.inFlightRequests.clear();
  }
}

export const refreshCoordinator = new RefreshCoordinator();
