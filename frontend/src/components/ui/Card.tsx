import React from "react";
import { cn } from "@/lib/utils";

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hover?: boolean;
}

export function Card({ className, hover = false, children, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-card bg-white dark:bg-brand-dark-card border border-gray-200/80 dark:border-brand-dark-border p-6 shadow-soft transition-all duration-200",
        hover && "hover:shadow-soft-lg hover:-translate-y-0.5",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}
