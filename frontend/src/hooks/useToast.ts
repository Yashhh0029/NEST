import { useCallback } from "react";
import { create } from "zustand";
import type { ToastMessage, ToastType } from "@/types/common";

interface ToastStore {
  toasts: ToastMessage[];
  addToast: (toast: Omit<ToastMessage, "id">) => void;
  removeToast: (id: string) => void;
}

function formatToastMessage(msg: unknown): string {
  if (typeof msg === "string") return msg;
  if (!msg) return "";
  if (Array.isArray(msg)) {
    return msg
      .map((item) => (typeof item === "object" && item !== null ? (item as any).msg || JSON.stringify(item) : String(item)))
      .join(", ");
  }
  if (typeof msg === "object") {
    const obj = msg as Record<string, unknown>;
    if (typeof obj.message === "string") return obj.message;
    if (typeof obj.detail === "string") return obj.detail;
    if (Array.isArray(obj.detail)) return formatToastMessage(obj.detail);
    try {
      return JSON.stringify(msg);
    } catch {
      return String(msg);
    }
  }
  return String(msg);
}

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  addToast: (toast) => {
    const id = Math.random().toString(36).substring(2, 9);
    const duration = toast.duration ?? 4000;
    const cleanMessage = formatToastMessage(toast.message);
    const cleanTitle = toast.title ? formatToastMessage(toast.title) : undefined;
    const newToast: ToastMessage = { ...toast, message: cleanMessage, title: cleanTitle, id };

    set((state) => {
      // Avoid stacking duplicate identical toasts
      const exists = state.toasts.some(
        (t) => t.message === cleanMessage && t.type === toast.type
      );
      if (exists) return state;
      return { toasts: [...state.toasts, newToast] };
    });

    if (duration > 0) {
      setTimeout(() => {
        set((state) => ({
          toasts: state.toasts.filter((t) => t.id !== id),
        }));
      }, duration);
    }
  },
  removeToast: (id: string) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),
}));

export function useToast() {
  const addToast = useToastStore((state) => state.addToast);
  const removeToast = useToastStore((state) => state.removeToast);

  const toast = useCallback(
    (message: any, type: ToastType = "info", title?: string, duration?: number) => {
      addToast({ message: formatToastMessage(message), type, title, duration });
    },
    [addToast]
  );

  const success = useCallback(
    (message: any, title?: string, duration?: number) => {
      addToast({ message: formatToastMessage(message), type: "success", title, duration });
    },
    [addToast]
  );

  const error = useCallback(
    (message: any, title?: string, duration?: number) => {
      addToast({ message: formatToastMessage(message), type: "error", title, duration });
    },
    [addToast]
  );

  const warning = useCallback(
    (message: any, title?: string, duration?: number) => {
      addToast({ message: formatToastMessage(message), type: "warning", title, duration });
    },
    [addToast]
  );

  const info = useCallback(
    (message: any, title?: string, duration?: number) => {
      addToast({ message: formatToastMessage(message), type: "info", title, duration });
    },
    [addToast]
  );

  return {
    toast,
    success,
    error,
    warning,
    info,
    removeToast,
  };
}
