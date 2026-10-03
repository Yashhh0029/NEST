import { ENV } from "@/config/env";

let loadPromise: Promise<boolean> | null = null;

export function loadGoogleMaps(): Promise<boolean> {
  if (typeof window === "undefined") {
    return Promise.resolve(false);
  }

  // Already loaded
  if ((window as any).google?.maps?.Map) {
    return Promise.resolve(true);
  }

  // JSDOM / Vitest test environment cannot load external script tags
  const isJsdom =
    navigator.userAgent.includes("jsdom") ||
    Boolean((window as any).__vitest__);
  if (isJsdom) {
    return Promise.resolve(false);
  }

  if (loadPromise) {
    return loadPromise;
  }

  const rawKey = ENV.GOOGLE_MAPS_API_KEY || (import.meta as any).env.VITE_GOOGLE_MAPS_API_KEY || "";
  const apiKey = String(rawKey).replace(/^["']|["']$/g, "").trim();
  if (!apiKey || apiKey === "your_google_maps_api_key_here") {
    // Graceful fallback when no key is configured
    return Promise.resolve(false);
  }

  loadPromise = new Promise<boolean>((resolve) => {
    // Check if script element already exists
    const existingScript = document.querySelector('script[src*="maps.googleapis.com/maps/api/js"]');
    if (existingScript) {
      if ((window as any).google?.maps?.Map) {
        resolve(true);
        return;
      }
      existingScript.addEventListener("load", () => resolve(true));
      existingScript.addEventListener("error", () => resolve(false));
      return;
    }

    const script = document.createElement("script");
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey.trim())}&libraries=places,geometry&v=weekly`;
    script.async = true;
    script.defer = true;

    script.onload = () => {
      resolve(true);
    };

    script.onerror = (err) => {
      console.warn("Failed to load Google Maps JavaScript API:", err);
      resolve(false);
    };

    document.head.appendChild(script);
  });

  return loadPromise;
}

export function resetGoogleMapsLoader(): void {
  loadPromise = null;
}
