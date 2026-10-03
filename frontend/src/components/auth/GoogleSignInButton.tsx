import React, { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/useAuthStore";
import { useToast } from "@/hooks/useToast";
import { Loader2 } from "lucide-react";

interface GoogleSignInButtonProps {
  text?: "signin_with" | "signup_with" | "continue_with";
  className?: string;
  onSuccess?: () => void;
}

declare global {
  interface Window {
    google?: any;
  }
}

import { ENV } from "@/config/env";

export const GoogleSignInButton: React.FC<GoogleSignInButtonProps> = ({
  text = "continue_with",
  className = "",
  onSuccess,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const { googleLogin } = useAuthStore();
  const { success, error, toast } = useToast();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [isConfigured, setIsConfigured] = useState(false);

  const clientId = ENV.GOOGLE_CLIENT_ID;

  useEffect(() => {
    if (!clientId) {
      setIsConfigured(false);
      return;
    }

    setIsConfigured(true);

    const initializeGoogle = () => {
      if (window.google?.accounts?.id && containerRef.current) {
        window.google.accounts.id.initialize({
          client_id: clientId,
          auto_select: false,
          itp_support: true,
          error_callback: (err: any) => {
            console.warn("Google Identity Services error:", err);
            if (err?.type === "popup_closed" || err?.type === "popup_failed_to_open") {
              toast(
                "Sign-in popup was blocked or closed. If using Brave or an adblocker, please disable Shields or allow popups for this site.",
                "warning",
                "Popup Blocked"
              );
            }
          },
          callback: async (response: any) => {
            if (response.credential) {
              setLoading(true);
              try {
                await googleLogin(response.credential);
                success("Successfully signed in with Google!", "Welcome to NEST");
                onSuccess?.();
                navigate("/home");
              } catch (err: any) {
                const detail =
                  err.response?.data?.detail ||
                  (err.message === "Network Error"
                    ? "Cannot reach backend server. Please verify network."
                    : "Google Sign-In verification failed.");
                error(detail, "Authentication Error");
              } finally {
                setLoading(false);
              }
            }
          },
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
        }
      }
    };

    if (window.google?.accounts?.id) {
      initializeGoogle();
    } else {
      const existingScript = document.querySelector('script[src="https://accounts.google.com/gsi/client"]');
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
  }, [clientId, googleLogin, navigate, onSuccess, text, toast]);

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
    <div className={`relative flex justify-center ${className}`}>
      {/* If Google script loaded & client ID configured, native GIS button renders here */}
      <div ref={containerRef} className={isConfigured ? "block" : "hidden"} />

      {/* Styled fallback button matching Google branding guidelines */}
      {(!isConfigured || loading) && (
        <button
          type="button"
          onClick={handleFallbackClick}
          disabled={loading}
          className="w-full flex items-center justify-center gap-3 px-5 py-3 rounded-full border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-200 font-medium text-sm hover:bg-slate-50 dark:hover:bg-slate-800/80 transition-all duration-200 shadow-sm active:scale-[0.99] disabled:opacity-60"
        >
          {loading ? (
            <Loader2 className="w-4 h-4 animate-spin text-slate-600 dark:text-slate-400" />
          ) : (
            <svg className="w-5 h-5" viewBox="0 0 24 24">
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
          )}
          <span>{loading ? "Authenticating..." : getLabel()}</span>
        </button>
      )}
    </div>
  );
};
