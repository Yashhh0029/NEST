let loadPromise: Promise<boolean> | null = null;

export function loadGoogleMaps(): Promise<boolean> {
  if (typeof window === "undefined") {
    return Promise.resolve(false);
  }

  // Already loaded
  if ((window as any).google && (window as any).google.maps) {
    return Promise.resolve(true);
  }

  if (loadPromise) {
    return loadPromise;
  }

  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY;
  if (!apiKey || typeof apiKey !== "string" || apiKey.trim() === "" || apiKey === "your_google_maps_api_key_here") {
    // Graceful fallback when no key is configured
    return Promise.resolve(false);
  }

  loadPromise = new Promise<boolean>((resolve) => {
    // Check if script element already exists
    const existingScript = document.querySelector('script[src*="maps.googleapis.com/maps/api/js"]');
    if (existingScript) {
      existingScript.addEventListener("load", () => resolve(true));
      existingScript.addEventListener("error", () => resolve(false));
      return;
    }

    const script = document.createElement("script");
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey.trim())}&libraries=places,geometry&loading=async`;
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
