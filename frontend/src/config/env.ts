export const ENV = {
  API_URL: (import.meta.env.VITE_API_URL || "http://127.0.0.1:8000").replace(/\/$/, ""),
  WS_URL: (import.meta.env.VITE_WS_URL || "").replace(/\/$/, ""),
  GOOGLE_MAPS_API_KEY: (import.meta.env.VITE_GOOGLE_MAPS_API_KEY || "").replace(/^["']|["']$/g, "").trim(),
  GOOGLE_CLIENT_ID: (import.meta.env.VITE_GOOGLE_CLIENT_ID || "").replace(/^["']|["']$/g, "").trim(),
} as const;
