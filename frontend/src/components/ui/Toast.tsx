import { useToastStore } from "@/hooks/useToast";
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

export function ToastContainer() {
  const { toasts, removeToast } = useToastStore();

  if (toasts.length === 0) return null;

  return (
    <div
      aria-live="polite"
      aria-label="Notifications"
      className="fixed bottom-20 md:bottom-6 right-4 left-4 md:left-auto md:w-96 z-50 flex flex-col gap-2.5 pointer-events-none"
    >
      {toasts.map((toast) => {
        const icons = {
          success: <CheckCircle2 className="w-5 h-5 text-brand-success shrink-0" />,
          error: <AlertCircle className="w-5 h-5 text-brand-danger shrink-0" />,
          warning: <AlertTriangle className="w-5 h-5 text-brand-accent shrink-0" />,
          info: <Info className="w-5 h-5 text-brand-primary shrink-0" />,
        };

        const bgBorders = {
          success: "border-green-200 dark:border-green-900/50 bg-white dark:bg-brand-dark-card",
          error: "border-red-200 dark:border-red-900/50 bg-white dark:bg-brand-dark-card",
          warning: "border-amber-200 dark:border-amber-900/50 bg-white dark:bg-brand-dark-card",
          info: "border-teal-200 dark:border-teal-900/50 bg-white dark:bg-brand-dark-card",
        };

        return (
          <div
            key={toast.id}
            role="status"
            className={cn(
              "pointer-events-auto flex items-start gap-3 p-4 rounded-xl border shadow-lg transition-all duration-200 animate-in slide-in-from-bottom-5",
              bgBorders[toast.type]
            )}
          >
            {icons[toast.type]}
            <div className="flex-1 text-sm">
              {toast.title && (
                <p className="font-semibold text-gray-900 dark:text-gray-100">{toast.title}</p>
              )}
              <p className="text-gray-600 dark:text-gray-300">{toast.message}</p>
            </div>
            <button
              onClick={() => removeToast(toast.id)}
              aria-label="Dismiss notification"
              className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded min-h-[32px] min-w-[32px] flex items-center justify-center"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
