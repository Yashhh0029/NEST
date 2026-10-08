import { useCallback } from "react";
import { create } from "zustand";
import type { ToastMessage, ToastType } from "@/types/common";

interface ToastStore {
  toasts: ToastMessage[];
  addToast: (toast: Omit<ToastMessage, "id">) => void;
  removeToast: (id: string) => void;
}

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  addToast: (toast) => {
    const id = Math.random().toString(36).substring(2, 9);
    const duration = toast.duration ?? 4000;
    const newToast: ToastMessage = { ...toast, id };

    set((state) => {
      // Avoid stacking duplicate identical toasts
      const exists = state.toasts.some(
        (t) => t.message === toast.message && t.type === toast.type
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
    (message: string, type: ToastType = "info", title?: string, duration?: number) => {
      addToast({ message, type, title, duration });
    },
    [addToast]
  );

  const success = useCallback(
    (message: string, title?: string, duration?: number) => {
      addToast({ message, type: "success", title, duration });
    },
    [addToast]
  );

  const error = useCallback(
    (message: string, title?: string, duration?: number) => {
      addToast({ message, type: "error", title, duration });
    },
    [addToast]
  );

  const warning = useCallback(
    (message: string, title?: string, duration?: number) => {
      addToast({ message, type: "warning", title, duration });
    },
    [addToast]
  );

  const info = useCallback(
    (message: string, title?: string, duration?: number) => {
      addToast({ message, type: "info", title, duration });
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
