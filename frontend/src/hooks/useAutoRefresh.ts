import { useState, useEffect, useRef, useCallback } from "react";
import { refreshCoordinator } from "@/services/refreshCoordinator";

export interface AutoRefreshOptions<T> {
  queryKey: string;
  fetchFn: (signal: AbortSignal) => Promise<T>;
  interval?: number; // Milliseconds between auto-refetches (default 45000 = 45s)
  enabled?: boolean; // Whether polling and invalidation listeners are active (default true)
  scopes?: string[]; // Scopes that trigger immediate invalidation (e.g. ['requests', 'nearby_requests'])
  staleTime?: number; // Minimum ms before refetching on visibility return (default 5000)
  detectNewItems?: (previous: T, next: T) => number; // Optional detector for newly arrived items
  stageNewItems?: boolean; // If true and new items detected, stage them behind applyNewItems instead of auto-replacing
  initialData?: T;
  onSuccess?: (data: T, isBackground: boolean) => void;
  onError?: (error: unknown) => void;
}

export interface AutoRefreshResult<T> {
  data: T | undefined;
  setData: React.Dispatch<React.SetStateAction<T | undefined>>;
  isLoading: boolean;
  isRefreshing: boolean;
  isOffline: boolean;
  error: Error | null;
  lastUpdated: Date | null;
  newItemsCount: number;
  applyNewItems: () => void;
  dismissNewItems: () => void;
  refreshNow: () => Promise<T | undefined>;
}

export function useAutoRefresh<T>({
  queryKey,
  fetchFn,
  interval = 45000,
  enabled = true,
  scopes = [],
  staleTime = 5000,
  detectNewItems,
  stageNewItems = false,
  initialData,
  onSuccess,
  onError,
}: AutoRefreshOptions<T>): AutoRefreshResult<T> {
  const [data, setData] = useState<T | undefined>(initialData);
  const [isLoading, setIsLoading] = useState<boolean>(!initialData);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [isOffline, setIsOffline] = useState<boolean>(!refreshCoordinator.isOnline());
  const [error, setError] = useState<Error | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(initialData ? new Date() : null);
  const [newItemsCount, setNewItemsCount] = useState<number>(0);

  // Staged data when new items are detected and stageNewItems is true
  const stagedDataRef = useRef<T | null>(null);

  // Mutable refs to track state without resetting effects
  const dataRef = useRef<T | undefined>(data);
  dataRef.current = data;

  const lastUpdatedRef = useRef<Date | null>(lastUpdated);
  lastUpdatedRef.current = lastUpdated;

  const isFetchingRef = useRef<boolean>(false);
  const hasAuthErrorRef = useRef<boolean>(false);
  const currentIntervalRef = useRef<number>(interval);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const isMountedRef = useRef<boolean>(true);

  // Keep latest callbacks
  const fetchFnRef = useRef(fetchFn);
  fetchFnRef.current = fetchFn;
  const onSuccessRef = useRef(onSuccess);
  onSuccessRef.current = onSuccess;
  const onErrorRef = useRef(onError);
  onErrorRef.current = onError;
  const detectNewItemsRef = useRef(detectNewItems);
  detectNewItemsRef.current = detectNewItems;

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const scheduleNextPoll = useCallback(() => {
    clearTimer();
    if (!enabled || !isMountedRef.current || hasAuthErrorRef.current) {
      return;
    }

    timerRef.current = setTimeout(() => {
      // Check environment guards before polling
      if (
        !refreshCoordinator.isTabVisible() ||
        !refreshCoordinator.isOnline() ||
        isFetchingRef.current ||
        hasAuthErrorRef.current
      ) {
        scheduleNextPoll();
        return;
      }

      executeFetch(true);
    }, currentIntervalRef.current);
  }, [enabled, clearTimer]);

  const executeFetch = useCallback(
    async (isBackground = false): Promise<T | undefined> => {
      if (!isMountedRef.current || isFetchingRef.current || hasAuthErrorRef.current) {
        return dataRef.current;
      }

      // If offline, don't attempt request
      if (!refreshCoordinator.isOnline()) {
        setIsOffline(true);
        scheduleNextPoll();
        return dataRef.current;
      }

      setIsOffline(false);

      // Abort previous in-flight request if present and clear from deduplication
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
        refreshCoordinator.clearInFlight(queryKey);
      }

      const controller = new AbortController();
      abortControllerRef.current = controller;
      isFetchingRef.current = true;

      if (isBackground) {
        setIsRefreshing(true);
      } else {
        if (!dataRef.current) {
          setIsLoading(true);
        } else {
          setIsRefreshing(true);
        }
      }

      try {
        // Execute through coordinator deduplication
        const result = await refreshCoordinator.executeDeduplicated(
          queryKey,
          () => fetchFnRef.current(controller.signal)
        );

        if (!isMountedRef.current || controller.signal.aborted) {
          return undefined;
        }

        const now = new Date();
        setLastUpdated(now);
        setError(null);
        // Reset backoff interval on success
        currentIntervalRef.current = interval;

        // Check if new items arrived
        if (
          isBackground &&
          stageNewItems &&
          detectNewItemsRef.current &&
          dataRef.current
        ) {
          const count = detectNewItemsRef.current(dataRef.current, result);
          if (count > 0) {
            stagedDataRef.current = result;
            setNewItemsCount(count);
            // Don't auto-replace data yet to prevent sudden reorder / scroll jump
            onSuccessRef.current?.(result, true);
            return result;
          }
        }

        // Apply immediately
        setData(result);
        dataRef.current = result;
        setNewItemsCount(0);
        stagedDataRef.current = null;
        onSuccessRef.current?.(result, isBackground);
        return result;
      } catch (err: unknown) {
        if (!isMountedRef.current || controller.signal.aborted) {
          return undefined;
        }

        // Ignore cancellations/aborts — do not treat cancellation as a user-facing API error!
        const isCanceled =
          Boolean(
            err &&
              typeof err === "object" &&
              ("name" in err || "code" in err) &&
              ((err as any).name === "CanceledError" ||
                (err as any).name === "AbortError" ||
                (err as any).code === "ERR_CANCELED")
          ) || controller.signal.aborted;

        if (isCanceled) {
          return undefined;
        }

        const status =
          err && typeof err === "object" && "response" in err
            ? (err as { response?: { status?: number } }).response?.status
            : null;

        // 401 or 403: Stop polling completely
        if (status === 401 || status === 403) {
          hasAuthErrorRef.current = true;
          clearTimer();
        } else if (status === 429) {
          // Rate limited: Exponential backoff up to 2 minutes
          currentIntervalRef.current = Math.min(currentIntervalRef.current * 2, 120000);
        } else if (!status || status >= 500) {
          // 5xx or Network failure: Backoff by 1.5x up to 60s
          currentIntervalRef.current = Math.min(currentIntervalRef.current * 1.5, 60000);
        }

        const standardError = err instanceof Error ? err : new Error(String(err));
        setError(standardError);
        onErrorRef.current?.(err);
        return undefined;
      } finally {
        if (isMountedRef.current) {
          isFetchingRef.current = false;
          setIsLoading(false);
          setIsRefreshing(false);
          scheduleNextPoll();
        }
      }
    },
    [queryKey, interval, stageNewItems, scheduleNextPoll, clearTimer]
  );

  // Manual refresh action
  const refreshNow = useCallback(async (): Promise<T | undefined> => {
    // Reset backoff on intentional user refresh
    currentIntervalRef.current = interval;
    hasAuthErrorRef.current = false;
    refreshCoordinator.clearInFlight(queryKey);
    // Discard staged state and fetch fresh
    stagedDataRef.current = null;
    setNewItemsCount(0);
    return executeFetch(false);
  }, [executeFetch, interval, queryKey]);

  // Apply staged new items
  const applyNewItems = useCallback(() => {
    if (stagedDataRef.current) {
      setData(stagedDataRef.current);
      dataRef.current = stagedDataRef.current;
      stagedDataRef.current = null;
      setNewItemsCount(0);
    }
  }, []);

  // Dismiss new items notification without applying
  const dismissNewItems = useCallback(() => {
    setNewItemsCount(0);
    stagedDataRef.current = null;
  }, []);

  // Initial fetch and subscription setup
  useEffect(() => {
    isMountedRef.current = true;
    hasAuthErrorRef.current = false;

    // Trigger initial fetch if no initial data
    if (!dataRef.current && enabled) {
      executeFetch(false);
    } else {
      scheduleNextPoll();
    }

    // Subscribe to refreshCoordinator events (scopes, visibility, network)
    const unsubscribe = refreshCoordinator.subscribe((invalidated) => {
      if (!isMountedRef.current || !enabled) return;

      if (invalidated.includes("visibility_hidden")) {
        return;
      }

      if (invalidated.includes("visibility_visible")) {
        // Tab became visible: check staleness
        const last = lastUpdatedRef.current;
        const isStale = !last || Date.now() - last.getTime() >= staleTime;
        if (isStale) {
          executeFetch(true);
        }
      } else if (invalidated.includes("network_online")) {
        // Network back online: clear offline status and refetch
        setIsOffline(false);
        executeFetch(true);
      } else if (invalidated.includes("network_offline")) {
        setIsOffline(true);
      } else {
        // Scoped invalidation (e.g. user created request, accepted connection)
        executeFetch(true);
      }
    }, scopes);

    return () => {
      isMountedRef.current = false;
      clearTimer();
      unsubscribe();
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [queryKey, enabled, JSON.stringify(scopes), staleTime, executeFetch, scheduleNextPoll, clearTimer]);

  return {
    data,
    setData,
    isLoading,
    isRefreshing,
    isOffline,
    error,
    lastUpdated,
    newItemsCount,
    applyNewItems,
    dismissNewItems,
    refreshNow,
  };
}
