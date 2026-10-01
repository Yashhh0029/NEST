import { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { authService } from "@/services/auth";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { useToast } from "@/hooks/useToast";
import { CheckCircle2, AlertCircle, Clock, Mail, ArrowRight, Loader2 } from "lucide-react";

type VerificationState = "loading" | "success" | "expired" | "invalid" | "idle";

export function VerifyEmailPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token");

  const [state, setState] = useState<VerificationState>(token ? "loading" : "idle");
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [resendEmail, setResendEmail] = useState("");
  const [isResending, setIsResending] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);

  const { success: toastSuccess, error: toastError } = useToast();

  useEffect(() => {
    if (!token) return;

    let isMounted = true;
    authService
      .verifyEmail(token)
      .then(() => {
        if (isMounted) setState("success");
      })
      .catch((err: unknown) => {
        if (!isMounted) return;
        let detail = "Verification failed.";
        if (err && typeof err === "object" && "response" in err) {
          const resp = (err as { response?: { data?: { detail?: string } } }).response;
          if (resp?.data?.detail) detail = resp.data.detail;
        }

        setErrorMessage(detail);
        if (detail.toLowerCase().includes("expired")) {
          setState("expired");
        } else {
          setState("invalid");
        }
      });

    return () => {
      isMounted = false;
    };
  }, [token]);

  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => {
      setResendCooldown((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  const handleResend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resendEmail || resendCooldown > 0) return;

    setIsResending(true);
    try {
      const res = await authService.resendVerification(resendEmail);
      toastSuccess(res.message, "Verification Sent");
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

  return (
    <div className="max-w-md mx-auto py-12 px-4">
      <Card className="p-6 sm:p-8 space-y-6 text-center shadow-lg border border-slate-200 dark:border-slate-800">
        <div className="w-14 h-14 rounded-2xl bg-teal-50 dark:bg-brand-dark-muted/60 text-brand-primary dark:text-teal-300 mx-auto flex items-center justify-center mb-2">
          {state === "loading" && <Loader2 className="w-7 h-7 animate-spin text-teal-600" />}
          {state === "success" && <CheckCircle2 className="w-7 h-7 text-emerald-600" />}
          {state === "expired" && <Clock className="w-7 h-7 text-amber-600" />}
          {state === "invalid" && <AlertCircle className="w-7 h-7 text-rose-600" />}
          {state === "idle" && <Mail className="w-7 h-7 text-teal-600" />}
        </div>

        {/* 1. Loading State */}
        {state === "loading" && (
          <div className="space-y-3">
            <h1 className="text-2xl font-bold font-heading text-gray-900 dark:text-gray-100">
              Verifying Your Email
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Please wait a moment while we cryptographically verify your single-use verification token...
            </p>
          </div>
        )}

        {/* 2. Success State */}
        {state === "success" && (
          <div className="space-y-4">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 text-xs font-semibold">
              ✓ Email Verified
            </div>
            <h1 className="text-2xl font-bold font-heading text-gray-900 dark:text-gray-100">
              Your NEST account is ready
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-300">
              Your email address has been verified. You can now securely log in and connect with your local community.
            </p>
            <div className="pt-2">
              <Link to="/login">
                <Button className="w-full gap-2 py-2.5">
                  Continue to Login <ArrowRight className="w-4 h-4" />
                </Button>
              </Link>
            </div>
          </div>
        )}

        {/* 3. Expired State */}
        {state === "expired" && (
          <div className="space-y-4 text-left">
            <div className="text-center space-y-1">
              <h1 className="text-2xl font-bold font-heading text-gray-900 dark:text-gray-100">
                Verification Link Expired
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {errorMessage || "This verification link has expired. Enter your email to receive a new one."}
              </p>
            </div>

            <form onSubmit={handleResend} className="space-y-3 pt-2">
              <Input
                label="Your Email Address"
                type="email"
                required
                placeholder="name@example.com"
                value={resendEmail}
                onChange={(e) => setResendEmail(e.target.value)}
              />
              <Button
                type="submit"
                disabled={isResending || resendCooldown > 0 || !resendEmail}
                className="w-full py-2.5"
              >
                {isResending
                  ? "Sending..."
                  : resendCooldown > 0
                  ? `Resend available in ${resendCooldown}s`
                  : "Send me a new link"}
              </Button>
            </form>

            <div className="text-center pt-2">
              <Link to="/login" className="text-xs text-teal-600 hover:underline">
                Return to Login
              </Link>
            </div>
          </div>
        )}

        {/* 4. Invalid or Replayed State */}
        {state === "invalid" && (
          <div className="space-y-4 text-left">
            <div className="text-center space-y-1">
              <h1 className="text-2xl font-bold font-heading text-gray-900 dark:text-gray-100">
                Invalid or Used Link
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {errorMessage || "This verification link is invalid or has already been used to verify an account."}
              </p>
            </div>

            <div className="p-3.5 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/40 text-xs text-amber-800 dark:text-amber-200">
              If you have already verified your account, you can sign in directly with your email and password.
            </div>

            <div className="space-y-2 pt-2">
              <Link to="/login" className="block">
                <Button className="w-full py-2.5">
                  Sign In to NEST
                </Button>
              </Link>
            </div>

            <div className="pt-2 border-t border-slate-200 dark:border-slate-800">
              <p className="text-xs text-gray-500 text-center mb-2">Need a fresh verification link?</p>
              <form onSubmit={handleResend} className="space-y-2">
                <Input
                  type="email"
                  required
                  placeholder="Enter your email"
                  value={resendEmail}
                  onChange={(e) => setResendEmail(e.target.value)}
                />
                <Button
                  type="submit"
                  variant="outline"
                  size="sm"
                  disabled={isResending || resendCooldown > 0 || !resendEmail}
                  className="w-full"
                >
                  {isResending
                    ? "Sending..."
                    : resendCooldown > 0
                    ? `Cooldown (${resendCooldown}s)`
                    : "Resend Verification Link"}
                </Button>
              </form>
            </div>
          </div>
        )}

        {/* 5. Idle State (User navigated to /verify-email directly) */}
        {state === "idle" && (
          <div className="space-y-4 text-left">
            <div className="text-center space-y-1">
              <h1 className="text-2xl font-bold font-heading text-gray-900 dark:text-gray-100">
                Verify Your Email
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Need to activate your NEST account? Enter your email address to receive a verification link.
              </p>
            </div>

            <form onSubmit={handleResend} className="space-y-3 pt-2">
              <Input
                label="Registered Email"
                type="email"
                required
                placeholder="name@example.com"
                value={resendEmail}
                onChange={(e) => setResendEmail(e.target.value)}
              />
              <Button
                type="submit"
                disabled={isResending || resendCooldown > 0 || !resendEmail}
                className="w-full py-2.5"
              >
                {isResending
                  ? "Sending..."
                  : resendCooldown > 0
                  ? `Resend available in ${resendCooldown}s`
                  : "Send Verification Email"}
              </Button>
            </form>

            <div className="text-center pt-2">
              <Link to="/login" className="text-xs text-teal-600 hover:underline">
                Already verified? Sign in here
              </Link>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
