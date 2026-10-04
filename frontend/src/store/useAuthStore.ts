import { create } from "zustand";
import { authService } from "@/services/auth";
import type { LoginPayload, User } from "@/types/auth";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (payload: LoginPayload) => Promise<void>;
  googleLogin: (credential: string) => Promise<void>;
  logout: () => void;
  setUser: (user: User | null) => void;
  clearAuth: () => void;
  initializeAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: typeof window !== "undefined" ? authService.getToken() : null,
  isAuthenticated: false,
  loading: true,

  login: async (payload: LoginPayload) => {
    set({ loading: true });
    try {
      const tokenData = await authService.login(payload);
      const user = tokenData.user || (await authService.getMe());
      set({
        accessToken: tokenData.access_token,
        user,
        isAuthenticated: true,
        loading: false,
      });
    } catch (error) {
      set({ loading: false, isAuthenticated: false, user: null, accessToken: null });
      throw error;
    }
  },

  googleLogin: async (credential: string) => {
    set({ loading: true });
    try {
      const tokenData = await authService.googleLogin(credential);
      const user = tokenData.user || (await authService.getMe());
      set({
        accessToken: tokenData.access_token,
        user,
        isAuthenticated: true,
        loading: false,
      });
    } catch (error) {
      set({ loading: false, isAuthenticated: false, user: null, accessToken: null });
      throw error;
    }
  },

  logout: () => {
    authService.logout();
    set({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      loading: false,
    });
  },

  setUser: (user: User | null) => {
    set({
      user,
      isAuthenticated: !!user,
    });
  },

  clearAuth: () => {
    authService.logout();
    set({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      loading: false,
    });
  },

  initializeAuth: async () => {
    const token = authService.getToken();
    if (!token) {
      set({ loading: false, isAuthenticated: false, user: null });
      return;
    }

    try {
      const user = await authService.getMe();
      set({
        user,
        accessToken: token,
        isAuthenticated: true,
        loading: false,
      });
    } catch {
      authService.logout();
      set({
        user: null,
        accessToken: null,
        isAuthenticated: false,
        loading: false,
      });
    }
  },
}));

// Listen for global unauthorized events to reset store
if (typeof window !== "undefined") {
  window.addEventListener("nest:unauthorized", () => {
    useAuthStore.getState().clearAuth();
  });
}
