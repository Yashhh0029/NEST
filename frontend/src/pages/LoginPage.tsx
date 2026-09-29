import { useState } from "react";
import { Link, useNavigate, useLocation } from "react-router-dom";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { useAuthStore } from "@/store/useAuthStore";
import { useToast } from "@/hooks/useToast";
import { Card } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Eye, EyeOff, Compass } from "lucide-react";

const loginSchema = z.object({
  email: z.string().min(1, "Please enter a valid email address").email("Please enter a valid email address"),
  password: z.string().min(1, "Password is required"),
});

type LoginFormData = z.infer<typeof loginSchema>;

export function LoginPage() {
  const [showPassword, setShowPassword] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuthStore();
  const { success: toastSuccess, error: toastError } = useToast();

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || "/home";

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

  const onSubmit = async (data: LoginFormData) => {
    setIsSubmitting(true);
    setApiError(null);

    try {
      await login(data);
      toastSuccess("Welcome back to NEST!", "Login Successful");
      navigate(from, { replace: true });
    } catch (err: unknown) {
      let msg = "Invalid email or password.";
      if (err && typeof err === "object" && "response" in err) {
        const responseData = (err as { response?: { data?: { detail?: string } } }).response?.data;
        if (responseData?.detail && typeof responseData.detail === "string") {
          msg = responseData.detail;
        }
      }
      setApiError(msg);
      toastError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

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

        {apiError && (
          <div className="p-3 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/50 text-xs text-brand-danger font-medium">
            {apiError}
          </div>
        )}

        <form onSubmit={handleSubmit(onSubmit)} noValidate className="space-y-4">
          <Input
            label="Email Address"
            type="email"
            placeholder="you@example.com"
            error={errors.email?.message}
            {...register("email")}
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
            {...register("password")}
          />

          <Button type="submit" isLoading={isSubmitting} className="w-full mt-2 font-semibold">
            Log In
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
