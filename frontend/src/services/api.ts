import axios from "axios";
import { ENV } from "@/config/env";

export const TOKEN_STORAGE_KEY = "nest_access_token";

export const api = axios.create({
  baseURL: ENV.API_URL,
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 15000,
});

// Request interceptor: attach bearer token from sessionStorage if present, except for public auth routes
api.interceptors.request.use(
  (config) => {
    const isPublicAuthRoute =
      config.url?.includes("/api/auth/register") ||
      config.url?.includes("/api/auth/login") ||
      config.url?.includes("/api/auth/google") ||
      config.url?.includes("/api/auth/verify-email") ||
      config.url?.includes("/api/auth/resend-verification");

    if (!isPublicAuthRoute) {
      const token = sessionStorage.getItem(TOKEN_STORAGE_KEY);
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    } else if (config.headers && config.headers.Authorization) {
      delete config.headers.Authorization;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: handle 401 or deactivated 403 by clearing auth and dispatching event
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const isDeactivated =
      error.response?.status === 403 &&
      (error.response?.data?.detail === "User account is deactivated." ||
        error.response?.data?.detail === "Inactive user account.");

    if (error.response?.status === 401 || isDeactivated) {
      sessionStorage.removeItem(TOKEN_STORAGE_KEY);
      window.dispatchEvent(new CustomEvent("nest:unauthorized"));
    }
    return Promise.reject(error);
  }
);
