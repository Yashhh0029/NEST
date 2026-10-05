import { useState, useEffect } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { authService } from "@/services/auth";
import { useToast } from "@/hooks/useToast";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { GoogleSignInButton } from "@/components/auth/GoogleSignInButton";
import { Eye, EyeOff, Check, X, Compass, Mail, ExternalLink } from "lucide-react";
import type { UserRole } from "@/types/common";

const registerSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters").max(100),
  email: z.string().email("Please enter a valid email address"),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .regex(/[0-9]/, "Password must contain at least one number")
    .regex(/[A-Za-z]/, "Password must contain at least one letter"),
  role: z.enum(["newcomer", "helper", "both"] as const),
});

type RegisterFormData = z.infer<typeof registerSchema>;

export function RegisterPage() {
  const [searchParams] = useSearchParams();
  const [showPassword, setShowPassword] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState<string | null>(null);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [isResending, setIsResending] = useState(false);

  const { success: toastSuccess, error: toastError } = useToast();

  const initialRoleParam = searchParams.get("role");
  const initialRole: UserRole =
    initialRoleParam === "helper"
      ? "helper"
      : initialRoleParam === "both"
      ? "both"
      : "newcomer";

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      name: "",
      email: "",
      password: "",
      role: initialRole,
    },
  });

  const selectedRole = watch("role");
  const passwordValue = watch("password") || "";

  useEffect(() => {
    if (initialRoleParam === "helper" || initialRoleParam === "both" || initialRoleParam === "newcomer") {
      setValue("role", initialRoleParam);
    }
  }, [initialRoleParam, setValue]);

  useEffect(() => {
    if (resendCooldown <= 0) return;
    const timer = setInterval(() => {
      setResendCooldown((prev) => prev - 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [resendCooldown]);

  // Password strength checks
  const hasMinLength = passwordValue.length >= 8;
  const hasLetter = /[A-Za-z]/.test(passwordValue);
  const hasNumber = /[0-9]/.test(passwordValue);
  const hasSpecial = /[^A-Za-z0-9]/.test(passwordValue);

  const onSubmit = async (data: RegisterFormData) => {
    setIsSubmitting(true);
    setApiError(null);

    try {
      await authService.register(data);
      setRegisteredEmail(data.email);
      setResendCooldown(60);
      toastSuccess("Verification link sent! Please check your email to activate your account.", "Account Created");
    } catch (err: unknown) {
      const errorDetail =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : "Registration failed. Please verify your details.";
      const msg = typeof errorDetail === "string" ? errorDetail : "Account creation error.";
      setApiError(msg);
      toastError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleResend = async () => {
    if (!registeredEmail || resendCooldown > 0) return;
    setIsResending(true);
    try {
      const res = await authService.resendVerification(registeredEmail);
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

  if (registeredEmail) {
    const isGmail = registeredEmail.includes("@gmail.com") || registeredEmail.includes("@googlemail.com");
    const isOutlook = registeredEmail.includes("@outlook.com") || registeredEmail.includes("@hotmail.com");
    const webmailUrl = isGmail
      ? "https://mail.google.com"
      : isOutlook
      ? "https://outlook.live.com"
      : `mailto:${registeredEmail}`;

    const [localPart, domain] = registeredEmail.split("@");
    const maskedEmail =
      localPart && localPart.length > 2
        ? `${localPart[0]}***${localPart[localPart.length - 1]}@${domain}`
        : `${localPart || ""}***@${domain || ""}`;

    return (
      <div className="max-w-md mx-auto py-12 px-4">
        <Card className="p-6 sm:p-8 space-y-6 text-center shadow-lg border border-slate-200 dark:border-slate-800">
          <div className="w-14 h-14 rounded-2xl bg-teal-50 dark:bg-brand-dark-muted/60 text-brand-primary dark:text-teal-300 mx-auto flex items-center justify-center mb-2">
            <Mail className="w-7 h-7 text-teal-600" />
          </div>

          <div className="space-y-2">
            <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-teal-50 dark:bg-teal-950/40 text-teal-700 dark:text-teal-300 text-xs font-semibold">
              ✉️ Check your email
            </div>
            <h1 className="text-2xl font-bold font-heading text-gray-900 dark:text-gray-100">
              Verify your email to continue
            </h1>
            <p className="text-sm text-gray-600 dark:text-gray-300">
              We've sent a cryptographically secure verification link to:
            </p>
            <p className="text-base font-semibold text-teal-700 dark:text-teal-300 bg-slate-50 dark:bg-slate-900 py-2 px-3 rounded-lg border border-slate-200 dark:border-slate-800">
              {maskedEmail}
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900/40 text-xs text-amber-800 dark:text-amber-200 text-left">
            <strong>Security Notice:</strong> The link will expire in 24 hours. Your account remains inactive until your email ownership is confirmed.
          </div>

          <div className="space-y-3 pt-2">
            <a
              href={webmailUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="block"
            >
              <Button className="w-full gap-2 py-2.5">
                <ExternalLink className="w-4 h-4" /> Open Email Inbox
              </Button>
            </a>

            <Button
              type="button"
              variant="outline"
              onClick={handleResend}
              disabled={isResending || resendCooldown > 0}
              className="w-full py-2.5"
            >
              {isResending
                ? "Sending..."
                : resendCooldown > 0
                ? `Resend available in ${resendCooldown}s`
                : "Resend verification email"}
            </Button>
          </div>

          <div className="pt-2 border-t border-slate-200 dark:border-slate-800">
            <Link to="/login" className="text-xs text-slate-500 hover:text-teal-600 dark:hover:text-teal-400">
              Already verified? Sign in here
            </Link>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-md mx-auto py-6 sm:py-12">
      <Card className="p-6 sm:p-8 space-y-6">
        <div className="text-center space-y-2">
          <div className="w-12 h-12 rounded-2xl bg-teal-50 dark:bg-brand-dark-muted/60 text-brand-primary dark:text-teal-300 mx-auto flex items-center justify-center mb-2">
            <Compass className="w-6 h-6" />
          </div>
          <h1 className="text-2xl font-bold font-heading text-gray-900 dark:text-gray-100">
            Join NEST
          </h1>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Connect with local residents or offer assistance in your city.
          </p>
        </div>

        {apiError && (
          <div className="p-3 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/50 text-xs text-brand-danger font-medium">
            {apiError}
          </div>
        )}

        <GoogleSignInButton text="signup_with" />

        <div className="relative flex py-2 items-center">
          <div className="flex-grow border-t border-slate-200 dark:border-slate-800"></div>
          <span className="flex-shrink mx-3 text-xs text-slate-400 uppercase tracking-wider">or register with email</span>
          <div className="flex-grow border-t border-slate-200 dark:border-slate-800"></div>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
          {/* Name */}
          <Input
            label="Full Name *"
            placeholder="e.g. Yash Kadam"
            error={errors.name?.message}
            {...register("name")}
          />

          {/* Email */}
          <Input
            label="Email Address *"
            type="email"
            placeholder="you@example.com"
            error={errors.email?.message}
            {...register("email")}
          />

          {/* Password */}
          <div>
            <Input
              label="Password *"
              type={showPassword ? "text" : "password"}
              placeholder="At least 8 characters with a number"
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
              {...register("password")}
            />

            {/* Password Strength Checklist */}
            <div className="mt-2 space-y-1 text-xs">
              <div
                className={`flex items-center gap-1.5 ${
                  hasMinLength ? "text-brand-success" : "text-gray-400"
                }`}
              >
                {hasMinLength ? <Check className="w-3.5 h-3.5" /> : <X className="w-3.5 h-3.5" />}
                <span>At least 8 characters</span>
              </div>
              <div
                className={`flex items-center gap-1.5 ${
                  hasLetter ? "text-brand-success" : "text-gray-400"
                }`}
              >
                {hasLetter ? <Check className="w-3.5 h-3.5" /> : <X className="w-3.5 h-3.5" />}
                <span>Contains a letter</span>
              </div>
              <div
                className={`flex items-center gap-1.5 ${
                  hasNumber ? "text-brand-success" : "text-gray-400"
                }`}
              >
                {hasNumber ? <Check className="w-3.5 h-3.5" /> : <X className="w-3.5 h-3.5" />}
                <span>Contains a number</span>
              </div>
              <div
                className={`flex items-center gap-1.5 ${
                  hasSpecial ? "text-brand-success" : "text-gray-400"
                }`}
              >
                {hasSpecial ? <Check className="w-3.5 h-3.5" /> : <X className="w-3.5 h-3.5" />}
                <span>Optional special character (!@#$)</span>
              </div>
            </div>
          </div>

          {/* Role Selection */}
          <div className="space-y-2 pt-2">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-200">
              What brings you to NEST? *
            </label>
            <div className="grid grid-cols-1 gap-2">
              {[
                {
                  id: "newcomer",
                  label: "I'm new to this city",
                  desc: "I need help with housing, local food, transit, or settling in.",
                },
                {
                  id: "helper",
                  label: "I know the city and want to help",
                  desc: "I want to advise newcomers, share tips, or recommend services.",
                },
                {
                  id: "both",
                  label: "Both",
                  desc: "I'm exploring the city and also happy to assist others.",
                },
              ].map((option) => (
                <label
                  key={option.id}
                  className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition-all ${
                    selectedRole === option.id
                      ? "border-brand-primary bg-teal-50/50 dark:bg-brand-dark-muted/30 dark:border-teal-500"
                      : "border-gray-200 dark:border-brand-dark-border hover:bg-gray-50 dark:hover:bg-brand-dark-card"
                  }`}
                >
                  <input
                    type="radio"
                    value={option.id}
                    className="mt-1 accent-brand-primary"
                    {...register("role")}
                  />
                  <div>
                    <span className="block text-sm font-semibold text-gray-900 dark:text-gray-100">
                      {option.label}
                    </span>
                    <span className="block text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                      {option.desc}
                    </span>
                  </div>
                </label>
              ))}
            </div>
          </div>

          <Button type="submit" isLoading={isSubmitting} className="w-full mt-2 font-semibold">
            Create Account
          </Button>
        </form>

        <div className="text-center pt-2 border-t border-gray-100 dark:border-brand-dark-border/60 text-xs text-gray-500 dark:text-gray-400">
          Already have an account?{" "}
          <Link
            to="/login"
            className="text-brand-primary dark:text-teal-400 font-semibold hover:underline"
          >
            Log in here
          </Link>
        </div>
      </Card>
    </div>
  );
}
