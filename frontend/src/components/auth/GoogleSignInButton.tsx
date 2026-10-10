import React, { useEffect, useRef, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/useAuthStore";
import { useToast } from "@/hooks/useToast";
import { Loader2 } from "lucide-react";
import { ENV } from "@/config/env";

interface GoogleSignInButtonProps {
  text?: "signin_with" | "signup_with" | "continue_with";
  className?: string;
  onSuccess?: () => void;
  onError?: (error: string | null) => void;
}

declare global {
  interface Window {
    google?: any;
  }
}

export const GoogleSignInButton: React.FC<GoogleSignInButtonProps> = ({
  text = "continue_with",
  className = "",
  onSuccess,
  onError,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const isInitializedRef = useRef(false);
  const isLoadingRef = useRef(false);

  const { googleLogin } = useAuthStore();
  const { success, error, toast } = useToast();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(false);
  const [isConfigured, setIsConfigured] = useState(false);

  const clientId = ENV.GOOGLE_CLIENT_ID;

  // Keep callback refs fresh without re-initializing Google GIS on every state change
  const callbacksRef = useRef({ onSuccess, onError, googleLogin, navigate, success, error, toast });
  useEffect(() => {
    callbacksRef.current = { onSuccess, onError, googleLogin, navigate, success, error, toast };
  });

  const handleCredentialResponse = useCallback(async (response: any) => {
    if (!response || !response.credential) {
      isLoadingRef.current = false;
      setLoading(false);
      const msg = "Google sign-in did not return a valid credential. Please try again.";
      callbacksRef.current.onError?.(msg);
      return;
    }

    if (isLoadingRef.current) return;
    isLoadingRef.current = true;
    setLoading(true);
    callbacksRef.current.onError?.(null);

    // Timeout guard: 18 seconds max before cleanly unlocking the UI if backend is waking up or network hung
    let timerId: any;
    const timeoutPromise = new Promise<never>((_, reject) => {
      timerId = setTimeout(() => {
        reject(new Error("GOOGLE_AUTH_TIMEOUT"));
      }, 18000);
    });

    try {
      // Clear any stale local session before fresh Google authentication
      sessionStorage.removeItem("nest_access_token");

      await Promise.race([
        callbacksRef.current.googleLogin(response.credential),
        timeoutPromise,
      ]);

      clearTimeout(timerId);
      callbacksRef.current.success("Successfully signed in with Google!", "Welcome to NEST");
      callbacksRef.current.onSuccess?.();
      callbacksRef.current.navigate("/home");
    } catch (err: any) {
      clearTimeout(timerId);
      let detail = "Google Sign-In verification failed. Please try again.";
      const status = err.response?.status;
      const serverDetail = err.response?.data?.detail;

      if (err.message === "GOOGLE_AUTH_TIMEOUT") {
        detail = "Server took too long to respond (cold start). Please click to retry.";
      } else if (status === 403) {
        const detailStr = String(serverDetail || "").toLowerCase();
        if (detailStr.includes("deactivated")) {
          detail = "Your account is deactivated. Please contact support.";
        } else if (detailStr.includes("verify") || detailStr.includes("email")) {
          detail = "Please verify your email before logging in.";
        } else {
          detail = serverDetail || "Account access restricted.";
        }
      } else if (status === 401) {
        detail = serverDetail || "Google authentication failed. Please try again.";
      } else if (status === 502 || status === 503 || status === 504) {
        detail = "Server is waking up (cold start). Please click to retry in a moment.";
      } else if (err.code === "ECONNABORTED") {
        detail = "Connection timed out. Please try again.";
      } else if (err.message === "Network Error" || (typeof navigator !== "undefined" && !navigator.onLine)) {
        detail = "Unable to reach NEST servers. Please check your internet connection and try again.";
      } else if (serverDetail) {
        detail = serverDetail;
      }

      callbacksRef.current.onError?.(detail);
      const isDeactivated = detail.toLowerCase().includes("deactivated");
      callbacksRef.current.error(detail, isDeactivated ? "Account Deactivated" : "Authentication Error");
    } finally {
      isLoadingRef.current = false;
      setLoading(false);
    }
  }, []);

  const handleGisError = useCallback((err: any) => {
    console.warn("Google Identity Services error event:", err);
    isLoadingRef.current = false;
    setLoading(false);

    if (err?.type === "popup_failed_to_open") {
      const msg = "Sign-in popup was blocked by browser. Please allow popups for this site and try again.";
      callbacksRef.current.onError?.(msg);
      callbacksRef.current.toast(msg, "warning", "Popup Blocked");
    } else if (err?.type === "popup_closed") {
      const msg = "Google sign-in was cancelled before completion. Click to try again.";
      callbacksRef.current.onError?.(msg);
    } else if (err?.type === "idpiframe_initialization_failed" || err?.type === "origin_mismatch") {
      const msg = "Google Sign-In configuration error. Please verify authorized JavaScript origins.";
      callbacksRef.current.onError?.(msg);
    }
  }, []);

  useEffect(() => {
    if (!clientId) {
      setIsConfigured(false);
      return;
    }

    setIsConfigured(true);

    const initializeGoogle = () => {
      if (window.google?.accounts?.id && containerRef.current) {
        try {
          window.google.accounts.id.initialize({
            client_id: clientId,
            auto_select: false,
            itp_support: true,
            error_callback: handleGisError,
            callback: handleCredentialResponse,
          });

          if (containerRef.current) {
            containerRef.current.innerHTML = "";
            window.google.accounts.id.renderButton(containerRef.current, {
              theme: "outline",
              size: "large",
              type: "standard",
              shape: "pill",
              text,
              width: 280,
            });
            isInitializedRef.current = true;
          }
        } catch (initErr) {
          console.warn("Failed to render Google Identity Services button:", initErr);
        }
      }
    };

    if (window.google?.accounts?.id) {
      initializeGoogle();
    } else {
      const existingScript = document.querySelector(
        'script[src="https://accounts.google.com/gsi/client"]'
      );
      if (existingScript) {
        existingScript.addEventListener("load", initializeGoogle);
      } else {
        const script = document.createElement("script");
        script.src = "https://accounts.google.com/gsi/client";
        script.async = true;
        script.defer = true;
        script.onload = initializeGoogle;
        document.body.appendChild(script);
      }
    }
  }, [clientId, text, handleCredentialResponse, handleGisError]);

  const handleFallbackClick = () => {
    if (!isConfigured) {
      toast(
        "Google OAuth requires VITE_GOOGLE_CLIENT_ID in frontend/.env. You can log in with standard email credentials below.",
        "info",
        "Google OAuth Setup"
      );
    }
  };

  const getLabel = () => {
    switch (text) {
      case "signin_with":
        return "Sign in with Google";
      case "signup_with":
        return "Sign up with Google";
      case "continue_with":
      default:
        return "Continue with Google";
    }
  };

  return (
    <div className={`relative flex flex-col items-center justify-center ${className}`}>
      {/* Native GIS iframe container - cleanly visible only when not in loading state */}
      <div
        ref={containerRef}
        className={isConfigured && !loading ? "flex justify-center" : "hidden"}
      />

      {/* Responsive Authenticating State matching GIS button pill size */}
      {loading && (
        <div
          role="status"
          aria-live="polite"
          className="w-[280px] h-[40px] flex items-center justify-center gap-2.5 rounded-full border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 font-medium text-sm shadow-xs animate-in fade-in duration-150"
        >
          <Loader2 className="w-4 h-4 animate-spin text-teal-600 dark:text-teal-400 shrink-0" />
          <span>Authenticating...</span>
        </div>
      )}

      {/* Styled fallback button if GIS is not configured */}
      {!isConfigured && !loading && (
        <button
          type="button"
          onClick={handleFallbackClick}
          className="w-full max-w-[280px] h-[40px] flex items-center justify-center gap-3 px-5 rounded-full border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 font-medium text-sm hover:bg-slate-50 dark:hover:bg-slate-800/80 transition-all duration-200 shadow-xs active:scale-[0.99]"
        >
          <svg className="w-4 h-4" viewBox="0 0 24 24">
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />
            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />
            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
            />
            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
            />
          </svg>
          <span>{getLabel()}</span>
        </button>
      )}
    </div>
  );
};
