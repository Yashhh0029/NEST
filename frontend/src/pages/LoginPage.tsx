import { useState, useEffect, useRef } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { api } from "@/services/api";
import { authService } from "@/services/auth";
import { useAuthStore } from "@/store/useAuthStore";
import { useToast } from "@/hooks/useToast";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { GoogleSignInButton } from "@/components/auth/GoogleSignInButton";
import { Eye, EyeOff, Compass, Mail } from "lucide-react";

const loginSchema = z.object({
  email: z.string().min(1, "Please enter a valid email address").email("Please enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

type LoginFormData = z.infer<typeof loginSchema>;

export function LoginPage() {
  const [showPassword, setShowPassword] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isSubmittingRef = useRef(false);
  const [unverifiedEmail, setUnverifiedEmail] = useState<string | null>(null);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [isResending, setIsResending] = useState(false);

  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuthStore();
  const { success: toastSuccess, error: toastError } = useToast();

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || "/home";

  // Pre-warm backend while user is filling the login form to eliminate cold-start delay
  useEffect(() => {
    api.get("/health").catch(() => {});
  }, []);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: "",
      password: "",
    },
  });

  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => {
      setResendCooldown((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  const handleResend = async () => {
    if (!unverifiedEmail || resendCooldown > 0) return;
    setIsResending(true);
    try {
      const res = await authService.resendVerification(unverifiedEmail);
      toastSuccess(res.message, "Verification Email Sent");
      setResendCooldown(60);
    } catch (err: unknown) {
      let detail = "Failed to resend verification email.";
      if (err && typeof err === "object" && "response" in err) {
        const resp = (err as { response?: { data?: { detail?: string } } }).response;
        if (resp?.data?.detail) detail = resp.data.detail;
      }
      toastError(detail, "Resend Error");
    } finally {
      setIsResending(false);
    }
  };

  const onSubmit = async (data: LoginFormData) => {
    if (isSubmittingRef.current || isSubmitting) return;
    isSubmittingRef.current = true;
    setIsSubmitting(true);
    setApiError(null);
    setUnverifiedEmail(null);

    try {
      await login(data);
      toastSuccess("Welcome back to NEST!", "Login Successful");
      navigate(from, { replace: true });
    } catch (err: unknown) {
      isSubmittingRef.current = false;
      let msg = "Unable to reach NEST. Please try again.";
      let isUnverified = false;

      if (err && typeof err === "object" && "response" in err) {
        const response = (err as { response?: { status?: number; data?: { detail?: string } } }).response;
        const status = response?.status;
        const detail = response?.data?.detail;
        const detailStr = typeof detail === "string" ? detail : "";

        if (
          detailStr.includes("EMAIL_NOT_VERIFIED") ||
          detailStr.toLowerCase().includes("verify your email")
        ) {
          isUnverified = true;
          msg = "Please verify your email before signing in.";
        } else if (status === 401) {
          msg = detailStr || "Invalid email or password.";
        } else if (status === 403) {
          if (detailStr.toLowerCase().includes("deactivated")) {
            msg = "Your account is deactivated. Please contact support.";
          } else {
            msg = detailStr || "Account access restricted.";
          }
        } else if (status === 502 || status === 503 || status === 504) {
          msg = "Server is waking up. Please try again in a moment.";
        } else if (detailStr) {
          msg = detailStr;
        } else {
          msg = "Server is waking up. Please try again in a moment.";
        }
      } else if (
        err &&
        typeof err === "object" &&
        "code" in err &&
        (err as { code?: string }).code === "ECONNABORTED"
      ) {
        msg = "Server is waking up. Please try again in a moment.";
      } else if (
        err &&
        typeof err === "object" &&
        "message" in err &&
        String((err as { message?: string }).message).toLowerCase().includes("network")
      ) {
        msg = "Unable to reach NEST. Please try again.";
      }

      if (isUnverified) {
        setUnverifiedEmail(data.email);
        setResendCooldown(45);
      } else {
        setApiError(msg);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const maskedEmail = (() => {
    if (!unverifiedEmail) return "";
    const [localPart, domain] = unverifiedEmail.split("@");
    if (!localPart) return unverifiedEmail;
    return localPart.length > 2
      ? `${localPart[0]}***${localPart[localPart.length - 1]}@${domain}`
      : `${localPart[0]}***@${domain}`;
  })();

  return (
    <div className="max-w-md mx-auto py-8 sm:py-16">
      <Card className="p-6 sm:p-8 space-y-6">
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-teal-50 dark:bg-brand-dark-muted/60 text-brand-primary dark:text-teal-300 mx-auto flex items-center justify-center mb-2">
            <Compass className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-bold font-heading text-gray-900 dark:text-gray-100">
            Welcome Back
          </h1>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Log in to continue finding matches and helping newcomers.
          </p>
        </div>

        {unverifiedEmail && (
          <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-900/50 space-y-3 text-left">
            <div className="flex items-center gap-2 text-amber-800 dark:text-amber-200 font-semibold text-sm">
              <Mail className="w-4 h-4 text-amber-600" />
              <span>Verify your email first</span>
            </div>
            <p className="text-xs text-amber-700 dark:text-amber-300">
              We sent a verification link to{" "}
              <strong className="font-mono text-gray-900 dark:text-gray-100">
                {maskedEmail}
              </strong>
              . Please verify your email before logging in.
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleResend}
              disabled={isResending || resendCooldown > 0}
              className="w-full text-xs font-medium"
            >
              {isResending
                ? "Sending..."
                : resendCooldown > 0
                ? `Resend available in ${resendCooldown}s`
                : "Resend verification email"}
            </Button>
          </div>
        )}

        {apiError && (
          <div className="p-3 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/50 text-xs text-brand-danger font-medium">
            {apiError}
          </div>
        )}

        <GoogleSignInButton text="signin_with" />

        <div className="relative flex py-2 items-center">
          <div className="flex-grow border-t border-slate-200 dark:border-slate-800"></div>
          <span className="flex-shrink mx-3 text-xs text-slate-400 uppercase tracking-wider">or with email</span>
          <div className="flex-grow border-t border-slate-200 dark:border-slate-800"></div>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
          <Input
            label="Email Address"
            type="email"
            placeholder="you@example.com"
            error={errors.email?.message}
            {...register("email", {
              onChange: () => {
                if (apiError) setApiError(null);
              },
            })}
          />

          <Input
            label="Password"
            type={showPassword ? "text" : "password"}
            placeholder="Your password"
            error={errors.password?.message}
            rightIcon={
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? "Hide password" : "Show password"}
                className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            }
            {...register("password", {
              onChange: () => {
                if (apiError) setApiError(null);
              },
            })}
          />

          <Button
            type="submit"
            isLoading={isSubmitting}
            disabled={isSubmitting}
            className="w-full mt-2 font-semibold"
          >
            {isSubmitting ? "Signing in..." : "Log In"}
          </Button>
        </form>

        <div className="text-center pt-2 border-t border-gray-100 dark:border-brand-dark-border/60 text-xs text-gray-500 dark:text-gray-400">
          Don't have an account?{" "}
          <Link
            to="/register"
            className="text-brand-primary dark:text-teal-400 font-semibold hover:underline"
          >
            Create an account
          </Link>
        </div>
      </Card>
    </div>
  );
}
