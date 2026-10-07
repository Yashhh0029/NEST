import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useAutoRefresh } from "@/hooks/useAutoRefresh";
import { refreshCoordinator } from "@/services/refreshCoordinator";

describe("Production-Grade Smart Auto-Refresh Architecture", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.restoreAllMocks();
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  it("1. fetches data on initial load and schedules periodic background refresh", async () => {
    const fetchFn = vi.fn().mockResolvedValue(["req-1", "req-2"]);

    const { result } = renderHook(() =>
      useAutoRefresh({
        queryKey: "test-query-1",
        fetchFn,
        interval: 30000,
      })
    );

    // Initial fetch
    await act(async () => {
      await Promise.resolve();
    });

    expect(fetchFn).toHaveBeenCalledTimes(1);
    expect(result.current.data).toEqual(["req-1", "req-2"]);
    expect(result.current.isLoading).toBe(false);

    // Advance 30 seconds
    await act(async () => {
      vi.advanceTimersByTime(30000);
      await Promise.resolve();
    });

    expect(fetchFn).toHaveBeenCalledTimes(2);
  });

  it("2. pauses polling when document is hidden and resumes/refetches when visible", async () => {
    const fetchFn = vi.fn().mockResolvedValue(["data"]);

    const { result } = renderHook(() =>
      useAutoRefresh({
        queryKey: "test-visibility",
        fetchFn,
        interval: 30000,
        staleTime: 5000,
      })
    );

    await act(async () => {
      await Promise.resolve();
    });
    expect(fetchFn).toHaveBeenCalledTimes(1);

    // Mock document.visibilityState to 'hidden' and notify coordinator
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "hidden",
    });
    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
      await Promise.resolve();
    });

    // Advance past interval while tab is hidden
    await act(async () => {
      vi.advanceTimersByTime(35000);
      await Promise.resolve();
    });

    // Should NOT have polled while tab was hidden
    expect(fetchFn).toHaveBeenCalledTimes(1);

    // Tab becomes visible again
    Object.defineProperty(document, "visibilityState", {
      configurable: true,
      value: "visible",
    });

    await act(async () => {
      document.dispatchEvent(new Event("visibilitychange"));
      await Promise.resolve();
    });

    // Refetches immediately upon returning to visible tab
    expect(fetchFn).toHaveBeenCalledTimes(2);
  });

  it("3. pauses polling when browser is offline and refetches immediately when online", async () => {
    const fetchFn = vi.fn().mockResolvedValue(["online-data"]);

    const { result } = renderHook(() =>
      useAutoRefresh({
        queryKey: "test-network",
        fetchFn,
        interval: 30000,
      })
    );

    await act(async () => {
      await Promise.resolve();
    });
    expect(fetchFn).toHaveBeenCalledTimes(1);

    // Simulate going offline
    Object.defineProperty(navigator, "onLine", {
      configurable: true,
      value: false,
    });

    await act(async () => {
      window.dispatchEvent(new Event("offline"));
      await Promise.resolve();
    });

    expect(result.current.isOffline).toBe(true);

    // Advance timer while offline
    await act(async () => {
      vi.advanceTimersByTime(35000);
      await Promise.resolve();
    });

    // No network requests while offline
    expect(fetchFn).toHaveBeenCalledTimes(1);

    // Simulate back online
    Object.defineProperty(navigator, "onLine", {
      configurable: true,
      value: true,
    });

    await act(async () => {
      window.dispatchEvent(new Event("online"));
      await Promise.resolve();
    });

    expect(result.current.isOffline).toBe(false);
    expect(fetchFn).toHaveBeenCalledTimes(2);
  });

  it("4. refetches immediately when registered scope is invalidated after user action", async () => {
    const fetchFn = vi.fn().mockResolvedValue([{ id: "req-1" }]);

    const { result } = renderHook(() =>
      useAutoRefresh({
        queryKey: "test-scoped-invalidation",
        fetchFn,
        interval: 60000,
        scopes: ["nearby_requests"],
      })
    );

    await act(async () => {
      await Promise.resolve();
    });
    expect(fetchFn).toHaveBeenCalledTimes(1);

    // Simulate user creating a request or accepting a connection
    await act(async () => {
      refreshCoordinator.invalidate(["nearby_requests"]);
      await Promise.resolve();
    });

    expect(fetchFn).toHaveBeenCalledTimes(2);
  });

  it("5. prevents duplicate in-flight requests and deduplicates identical calls", async () => {
    let resolveFirst: (val: any) => void = () => {};
    const fetchFn = vi.fn().mockImplementation(() => {
      return new Promise((resolve) => {
        resolveFirst = resolve;
      });
    });

    const { result } = renderHook(() =>
      useAutoRefresh({
        queryKey: "test-dedup",
        fetchFn,
      })
    );

    // Trigger manual refresh while already fetching
    act(() => {
      result.current.refreshNow();
    });

    expect(fetchFn).toHaveBeenCalledTimes(1);

    // Complete fetch
    await act(async () => {
      resolveFirst(["done"]);
      await Promise.resolve();
    });

    expect(result.current.data).toEqual(["done"]);
  });

  it("6. aborts pending requests on unmount via AbortController cleanup", async () => {
    let capturedSignal: AbortSignal | null = null;
    const fetchFn = vi.fn().mockImplementation((signal: AbortSignal) => {
      capturedSignal = signal;
      return new Promise(() => {}); // never resolves
    });

    const { unmount } = renderHook(() =>
      useAutoRefresh({
        queryKey: "test-abort",
        fetchFn,
      })
    );

    expect(capturedSignal).not.toBeNull();
    expect(capturedSignal!.aborted).toBe(false);

    unmount();

    expect(capturedSignal!.aborted).toBe(true);
  });

  it("7. stops polling on 401 Unauthorized / 403 Forbidden without infinite retry loop", async () => {
    const authError: any = new Error("Unauthorized");
    authError.response = { status: 401 };
    const fetchFn = vi.fn().mockRejectedValue(authError);

    renderHook(() =>
      useAutoRefresh({
        queryKey: "test-401-stop",
        fetchFn,
        interval: 10000,
      })
    );

    await act(async () => {
      await Promise.resolve();
    });
    expect(fetchFn).toHaveBeenCalledTimes(1);

    // Advance time past interval
    await act(async () => {
      vi.advanceTimersByTime(30000);
      await Promise.resolve();
    });

    // Polling must be halted completely on 401
    expect(fetchFn).toHaveBeenCalledTimes(1);
  });

  it("8. backs off interval on 429 Rate Limit error", async () => {
    const rateLimitError: any = new Error("Too Many Requests");
    rateLimitError.response = { status: 429 };
    const fetchFn = vi.fn().mockRejectedValue(rateLimitError);

    renderHook(() =>
      useAutoRefresh({
        queryKey: "test-429-backoff",
        fetchFn,
        interval: 10000,
      })
    );

    await act(async () => {
      await Promise.resolve();
    });
    expect(fetchFn).toHaveBeenCalledTimes(1);

    // At 10000ms, backoff is doubled to 20000ms, so at 10000ms it should not have fired yet
    await act(async () => {
      vi.advanceTimersByTime(10000);
      await Promise.resolve();
    });
    expect(fetchFn).toHaveBeenCalledTimes(1);

    // At 20000ms, it should retry
    await act(async () => {
      vi.advanceTimersByTime(10000);
      await Promise.resolve();
    });
    expect(fetchFn).toHaveBeenCalledTimes(2);
  });

  it("9. manual refresh updates data without browser reload, scroll jump, or form reset", async () => {
    let callCount = 0;
    const fetchFn = vi.fn().mockImplementation(() => {
      callCount++;
      return Promise.resolve([`item-${callCount}`]);
    });

    const { result } = renderHook(() =>
      useAutoRefresh({
        queryKey: "test-manual-refresh",
        fetchFn,
        interval: 60000,
      })
    );

    await act(async () => {
      await Promise.resolve();
    });
    expect(result.current.data).toEqual(["item-1"]);

    // Manual refresh
    await act(async () => {
      await result.current.refreshNow();
    });

    expect(fetchFn).toHaveBeenCalledTimes(2);
    expect(result.current.data).toEqual(["item-2"]);
    expect(result.current.lastUpdated).not.toBeNull();
  });

  it("10. detects new items in background and stages them behind applyNewItems without disruptive reorder", async () => {
    let version = 1;
    const fetchFn = vi.fn().mockImplementation(() => {
      const items = version === 1 ? [{ id: "1" }] : [{ id: "1" }, { id: "2" }];
      return Promise.resolve(items);
    });

    const { result } = renderHook(() =>
      useAutoRefresh({
        queryKey: "test-stage-new",
        fetchFn,
        interval: 20000,
        stageNewItems: true,
        detectNewItems: (prev, next) => next.length - prev.length,
      })
    );

    await act(async () => {
      await Promise.resolve();
    });
    expect(result.current.data).toEqual([{ id: "1" }]);
    expect(result.current.newItemsCount).toBe(0);

    // Simulate new item available in background
    version = 2;
    await act(async () => {
      vi.advanceTimersByTime(20000);
      await Promise.resolve();
    });

    // New items detected, but data is NOT abruptly replaced
    expect(result.current.newItemsCount).toBe(1);
    expect(result.current.data).toEqual([{ id: "1" }]);

    // User clicks applyNewItems
    act(() => {
      result.current.applyNewItems();
    });

    expect(result.current.newItemsCount).toBe(0);
    expect(result.current.data).toEqual([{ id: "1" }, { id: "2" }]);
  });

  it("11. ignores cancellation/abort errors without setting error state or clearing data", async () => {
    const cancelError = new Error("Request aborted");
    cancelError.name = "CanceledError";

    let callCount = 0;
    const fetchFn = vi.fn().mockImplementation(() => {
      callCount++;
      if (callCount === 1) {
        return Promise.resolve(["initial-item"]);
      }
      return Promise.reject(cancelError);
    });

    const { result } = renderHook(() =>
      useAutoRefresh({
        queryKey: "test-cancellation",
        fetchFn,
        interval: 30000,
      })
    );

    await act(async () => {
      await Promise.resolve();
    });
    expect(result.current.data).toEqual(["initial-item"]);
    expect(result.current.error).toBeNull();

    // Trigger second fetch which rejects with CanceledError
    await act(async () => {
      await result.current.refreshNow();
    });

    // Cancellation must NOT set error or wipe data
    expect(result.current.data).toEqual(["initial-item"]);
    expect(result.current.error).toBeNull();
  });

  it("12. non-destructive refresh: preserves existing data when background refresh fails", async () => {
    let callCount = 0;
    const fetchFn = vi.fn().mockImplementation(() => {
      callCount++;
      if (callCount === 1) {
        return Promise.resolve(["cached-item-1", "cached-item-2"]);
      }
      return Promise.reject(new Error("Network gateway timeout"));
    });

    const { result } = renderHook(() =>
      useAutoRefresh({
        queryKey: "test-preserves-data",
        fetchFn,
        interval: 20000,
      })
    );

    // Initial successful fetch
    await act(async () => {
      await Promise.resolve();
    });
    expect(result.current.data).toEqual(["cached-item-1", "cached-item-2"]);
    expect(result.current.error).toBeNull();

    // Background fetch failure after timer
    await act(async () => {
      vi.advanceTimersByTime(20000);
      await Promise.resolve();
    });

    // Existing data MUST be preserved, error recorded for non-destructive indicator
    expect(result.current.data).toEqual(["cached-item-1", "cached-item-2"]);
    expect(result.current.error).not.toBeNull();
    expect(result.current.error?.message).toBe("Network gateway timeout");
  });
});
