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

// Request interceptor: attach bearer token from sessionStorage if present
api.interceptors.request.use(
  (config) => {
    const token = sessionStorage.getItem(TOKEN_STORAGE_KEY);
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: handle 401 by clearing auth and dispatching event
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      sessionStorage.removeItem(TOKEN_STORAGE_KEY);
      window.dispatchEvent(new CustomEvent("nest:unauthorized"));
    }
    return Promise.reject(error);
  }
);
