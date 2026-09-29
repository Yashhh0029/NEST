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

    set((state) => ({ toasts: [...state.toasts, newToast] }));

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
  const { addToast, removeToast } = useToastStore();

  return {
    toast: (message: string, type: ToastType = "info", title?: string, duration?: number) => {
      addToast({ message, type, title, duration });
    },
    success: (message: string, title?: string, duration?: number) => {
      addToast({ message, type: "success", title, duration });
    },
    error: (message: string, title?: string, duration?: number) => {
      addToast({ message, type: "error", title, duration });
    },
    warning: (message: string, title?: string, duration?: number) => {
      addToast({ message, type: "warning", title, duration });
    },
    info: (message: string, title?: string, duration?: number) => {
      addToast({ message, type: "info", title, duration });
    },
    removeToast,
  };
}
