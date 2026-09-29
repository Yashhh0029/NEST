import React from "react";
import { Button } from "./Button";

export interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  actionLabel?: string;
  onAction?: () => void;
}

export function EmptyState({
  icon,
  title,
  description,
  actionLabel,
  onAction,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 md:p-12 text-center rounded-card border border-dashed border-gray-200 dark:border-brand-dark-border bg-gray-50/50 dark:bg-brand-dark-card/30">
      {icon && (
        <div className="w-14 h-14 rounded-2xl bg-teal-50 dark:bg-brand-dark-muted/40 text-brand-primary dark:text-teal-300 flex items-center justify-center mb-4">
          {icon}
        </div>
      )}
      <h3 className="text-lg font-bold font-heading text-gray-900 dark:text-gray-100">
        {title}
      </h3>
      <p className="mt-1.5 text-sm text-gray-500 dark:text-gray-400 max-w-sm">
        {description}
      </p>
      {actionLabel && onAction && (
        <div className="mt-6">
          <Button onClick={onAction}>{actionLabel}</Button>
        </div>
      )}
    </div>
  );
}
