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
    } catch (err: unknown) {
      const status =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { status?: number } }).response?.status
          : null;

      // Only wipe session and logout on definitive 401 Unauthorized or deactivated 403
      if (status === 401 || status === 403) {
        authService.logout();
        set({
          user: null,
          accessToken: null,
          isAuthenticated: false,
          loading: false,
        });
      } else {
        // Network timeout / cold start: retain token so user stays logged in
        set({
          loading: false,
          isAuthenticated: true,
        });
      }
    }
  },
}));

// Listen for global unauthorized events to reset store
if (typeof window !== "undefined") {
  window.addEventListener("nest:unauthorized", () => {
    useAuthStore.getState().clearAuth();
  });
}
