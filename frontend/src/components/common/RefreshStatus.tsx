import { useState, useEffect } from "react";
import { RefreshCw, WifiOff, AlertCircle } from "lucide-react";

interface RefreshStatusProps {
  lastUpdated: Date | null;
  isRefreshing?: boolean;
  isOffline?: boolean;
  error?: Error | null | string;
  onRefresh?: () => void;
  className?: string;
  showManualButton?: boolean;
  compact?: boolean;
}

export function formatRelativeTime(date: Date | null): string {
  if (!date) return "Never updated";
  const seconds = Math.floor((Date.now() - date.getTime()) / 1000);
  if (seconds < 10) return "Updated just now";
  if (seconds < 60) return `Updated ${seconds}s ago`;
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `Updated ${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  return `Updated ${hours}h ago`;
}

export function RefreshStatus({
  lastUpdated,
  isRefreshing = false,
  isOffline = false,
  error,
  onRefresh,
  className = "",
  showManualButton = true,
  compact = false,
}: RefreshStatusProps) {
  const [, setTick] = useState(0);

  // Re-render relative time every 10 seconds without fetching
  useEffect(() => {
    const timer = setInterval(() => {
      setTick((t) => t + 1);
    }, 10000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div
      className={`inline-flex items-center gap-2 text-[11px] font-medium text-slate-500 dark:text-slate-400 select-none ${className}`}
    >
      {isRefreshing ? (
        <span className="inline-flex items-center gap-1.5 text-teal-600 dark:text-teal-400">
          <RefreshCw className="w-3 h-3 animate-spin" />
          <span>Refreshing…</span>
        </span>
      ) : isOffline ? (
        <span className="inline-flex items-center gap-1.5 text-amber-600 dark:text-amber-400">
          <WifiOff className="w-3 h-3" />
          <span>Offline — showing last known data</span>
        </span>
      ) : error ? (
        <span className="inline-flex items-center gap-1.5 text-rose-500 dark:text-rose-400">
          <AlertCircle className="w-3 h-3" />
          <span>Couldn't refresh</span>
          {onRefresh && (
            <button
              type="button"
              onClick={onRefresh}
              className="underline font-semibold hover:text-rose-600 cursor-pointer"
            >
              Retry
            </button>
          )}
        </span>
      ) : (
        <span className="inline-flex items-center gap-1.5 text-slate-500 dark:text-slate-400">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
          <span>{formatRelativeTime(lastUpdated)}</span>
        </span>
      )}

      {showManualButton && onRefresh && !compact && (
        <button
          type="button"
          onClick={onRefresh}
          disabled={isRefreshing}
          title="Refresh data"
          aria-label="Refresh data"
          className="p-1 rounded-md text-slate-400 hover:text-teal-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <RefreshCw className={`w-3 h-3 ${isRefreshing ? "animate-spin" : ""}`} />
        </button>
      )}
    </div>
  );
}

interface RefreshButtonProps {
  onRefresh: () => void;
  isRefreshing?: boolean;
  className?: string;
  size?: "sm" | "md";
  label?: string;
}

export function RefreshButton({
  onRefresh,
  isRefreshing = false,
  className = "",
  size = "sm",
  label = "Refresh",
}: RefreshButtonProps) {
  return (
    <button
      type="button"
      onClick={onRefresh}
      disabled={isRefreshing}
      aria-label={label}
      className={`inline-flex items-center gap-1.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 font-semibold shadow-xs hover:bg-slate-50 dark:hover:bg-slate-800/80 transition cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${
        size === "sm" ? "px-2.5 py-1 text-xs" : "px-3.5 py-1.5 text-sm"
      } ${className}`}
    >
      <RefreshCw className={`w-3.5 h-3.5 text-teal-600 dark:text-teal-400 ${isRefreshing ? "animate-spin" : ""}`} />
      <span>{isRefreshing ? "Refreshing…" : label}</span>
    </button>
  );
}
