import { useState, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { authService } from "@/services/auth";
import { useAuthStore } from "@/store/useAuthStore";
import { useToast } from "@/hooks/useToast";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Eye, EyeOff, Check, X, Compass } from "lucide-react";
import type { UserRole } from "@/types/common";

const registerSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters").max(100),
  email: z.string().email("Please enter a valid email address"),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .regex(/[0-9]/, "Password must contain at least one number"),
  role: z.enum(["newcomer", "helper", "both"] as const),
});

type RegisterFormData = z.infer<typeof registerSchema>;

export function RegisterPage() {
  const [searchParams] = useSearchParams();
  const [showPassword, setShowPassword] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const navigate = useNavigate();
  const { login } = useAuthStore();
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

  // Password strength checks
  const hasMinLength = passwordValue.length >= 8;
  const hasNumber = /[0-9]/.test(passwordValue);
  const hasSpecial = /[^A-Za-z0-9]/.test(passwordValue);

  const onSubmit = async (data: RegisterFormData) => {
    setIsSubmitting(true);
    setApiError(null);

    try {
      // 1. Register user
      await authService.register(data);

      // 2. Automatically log in to get JWT token
      await login({ email: data.email, password: data.password });

      toastSuccess("Account created successfully! Welcome to NEST.", "Registration Complete");
      navigate("/onboarding");
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

        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
          {/* Name */}
          <Input
            label="Full Name *"
            placeholder="e.g. Priya Sharma"
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
