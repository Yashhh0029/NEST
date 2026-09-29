import React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "primary" | "accent" | "success" | "danger" | "neutral" | "muted";
  size?: "sm" | "md";
  icon?: React.ReactNode;
}

export function Badge({
  className,
  variant = "neutral",
  size = "md",
  icon,
  children,
  ...props
}: BadgeProps) {
  const baseStyles =
    "inline-flex items-center gap-1.5 font-medium rounded-full transition-colors select-none";

  const variants = {
    primary:
      "bg-teal-50 text-brand-primary border border-teal-200/80 dark:bg-brand-dark-muted/40 dark:text-teal-300 dark:border-brand-dark-border",
    accent:
      "bg-amber-50 text-amber-800 border border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800/40",
    success:
      "bg-green-50 text-green-700 border border-green-200 dark:bg-green-950/40 dark:text-green-300 dark:border-green-800/40",
    danger:
      "bg-red-50 text-red-700 border border-red-200 dark:bg-red-950/40 dark:text-red-300 dark:border-red-800/40",
    neutral:
      "bg-gray-100 text-gray-700 border border-gray-200 dark:bg-brand-dark-card dark:text-gray-300 dark:border-brand-dark-border",
    muted:
      "bg-gray-50/70 text-gray-500 border border-dashed border-gray-300 dark:bg-brand-dark-card/50 dark:text-gray-400 dark:border-brand-dark-border",
  };

  const sizes = {
    sm: "text-xs px-2.5 py-0.5",
    md: "text-xs md:text-sm px-3.5 py-1",
  };

  return (
    <span className={cn(baseStyles, variants[variant], sizes[size], className)} {...props}>
      {icon && <span className="inline-flex shrink-0 items-center">{icon}</span>}
      {children}
    </span>
  );
}
