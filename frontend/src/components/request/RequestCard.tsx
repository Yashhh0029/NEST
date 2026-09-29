import { Link } from "react-router-dom";
import type { NewcomerRequest } from "@/types/request";
import { Card } from "../ui/Card";
import { Badge } from "../ui/Badge";
import { Button } from "../ui/Button";
import { formatDate } from "@/lib/utils";
import { MapPin, Calendar, ArrowRight, Trash2, Edit3 } from "lucide-react";

export interface RequestCardProps {
  request: NewcomerRequest;
  onDelete?: (id: string) => void;
  onEdit?: (request: NewcomerRequest) => void;
}

export function RequestCard({ request, onDelete, onEdit }: RequestCardProps) {
  const needs = request.extracted_requirements?.needs || [];

  const statusVariants: Record<string, "primary" | "success" | "neutral"> = {
    OPEN: "primary",
    MATCHED: "success",
    CLOSED: "neutral",
  };

  return (
    <Card hover className="flex flex-col justify-between h-full space-y-4">
      <div className="space-y-3">
        {/* Header row with Status and Date */}
        <div className="flex items-center justify-between gap-2">
          <Badge variant={statusVariants[request.status] || "neutral"} size="sm">
            {request.status}
          </Badge>
          <span className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
            <Calendar className="w-3.5 h-3.5" />
            {formatDate(request.created_at)}
          </span>
        </div>

        {/* Raw request text */}
        <p className="text-base font-medium text-gray-900 dark:text-gray-100 line-clamp-3 leading-snug">
          "{request.raw_text}"
        </p>

        {/* Location & Budget chips */}
        <div className="flex flex-wrap gap-1.5 pt-1">
          {(request.area || request.city) && (
            <Badge variant="primary" size="sm" icon={<MapPin className="w-3 h-3" />}>
              {[request.area, request.city].filter(Boolean).join(", ")}
            </Badge>
          )}

          {request.budget_amount != null && (
            <Badge variant="accent" size="sm" icon="💰">
              {request.budget_operator === "<=" ? "under " : ""}₹
              {request.budget_amount.toLocaleString("en-IN")}
              {request.budget_period ? `/${request.budget_period}` : ""}
            </Badge>
          )}

          {needs.slice(0, 2).map((n, idx) => (
            <Badge key={idx} variant="neutral" size="sm">
              {n.item}
            </Badge>
          ))}
          {needs.length > 2 && (
            <Badge variant="muted" size="sm">
              +{needs.length - 2} more
            </Badge>
          )}
        </div>
      </div>

      {/* Footer Actions */}
      <div className="pt-3 border-t border-gray-100 dark:border-brand-dark-border/60 flex items-center justify-between gap-2">
        <div className="flex items-center gap-1">
          {onEdit && (
            <button
              onClick={() => onEdit(request)}
              aria-label="Edit request"
              className="p-2 text-gray-500 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-brand-dark-muted/40 transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
            >
              <Edit3 className="w-4 h-4" />
            </button>
          )}
          {onDelete && (
            <button
              onClick={() => onDelete(request.id)}
              aria-label="Delete request"
              className="p-2 text-gray-500 hover:text-brand-danger dark:text-gray-400 dark:hover:text-brand-danger rounded-lg hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>

        <Link to={`/requests/${request.id}`}>
          <Button variant="secondary" size="sm" rightIcon={<ArrowRight className="w-3.5 h-3.5" />}>
            View Details
          </Button>
        </Link>
      </div>
    </Card>
  );
}
