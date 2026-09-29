import React, { forwardRef } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger" | "accent";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className,
      variant = "primary",
      size = "md",
      isLoading = false,
      disabled,
      children,
      leftIcon,
      rightIcon,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      "inline-flex items-center justify-center font-medium rounded-xl transition-all duration-150 active:scale-[0.98] disabled:opacity-60 disabled:pointer-events-none disabled:active:scale-100 min-h-[44px] min-w-[44px] select-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2";

    const variants = {
      primary:
        "bg-brand-primary text-white hover:bg-brand-primary-hover focus-visible:ring-brand-primary shadow-sm",
      secondary:
        "bg-teal-50 text-brand-primary hover:bg-teal-100 dark:bg-brand-dark-muted/40 dark:text-teal-200 dark:hover:bg-brand-dark-muted/60 focus-visible:ring-brand-primary",
      outline:
        "border border-gray-300 dark:border-brand-dark-border text-gray-700 dark:text-gray-200 bg-transparent hover:bg-gray-100 dark:hover:bg-brand-dark-card focus-visible:ring-brand-primary",
      ghost:
        "text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-brand-dark-card focus-visible:ring-brand-primary",
      danger:
        "bg-brand-danger text-white hover:bg-red-700 focus-visible:ring-brand-danger shadow-sm",
      accent:
        "bg-brand-accent text-gray-900 font-semibold hover:bg-brand-accent-hover focus-visible:ring-brand-accent shadow-sm",
    };

    const sizes = {
      sm: "text-xs px-3 py-1.5 h-9",
      md: "text-sm px-4 py-2.5 h-11",
      lg: "text-base px-6 py-3.5 h-13",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={cn(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {isLoading ? (
          <Loader2 className="w-4 h-4 mr-2 animate-spin" />
        ) : leftIcon ? (
          <span className="mr-2 inline-flex items-center">{leftIcon}</span>
        ) : null}
        {children}
        {!isLoading && rightIcon ? (
          <span className="ml-2 inline-flex items-center">{rightIcon}</span>
        ) : null}
      </button>
    );
  }
);

Button.displayName = "Button";
