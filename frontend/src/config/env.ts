export const ENV = {
  API_URL: import.meta.env.VITE_API_URL || "http://127.0.0.1:8000",
  GOOGLE_MAPS_API_KEY: import.meta.env.VITE_GOOGLE_MAPS_API_KEY || "",
} as const;
