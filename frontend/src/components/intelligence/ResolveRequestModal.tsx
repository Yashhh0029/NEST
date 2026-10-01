import { useState } from "react";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { CheckCircle2 } from "lucide-react";

interface ResolveRequestModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: (summary: string, isIndependent?: boolean) => Promise<void>;
  isIndependent?: boolean;
}

export function ResolveRequestModal({
  isOpen,
  onClose,
  onConfirm,
  isIndependent = false,
}: ResolveRequestModalProps) {
  const [summary, setSummary] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    try {
      if (isIndependent) {
        await onConfirm(summary.trim(), true);
      } else {
        await onConfirm(summary.trim());
      }
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={isIndependent ? "Resolved Independently" : "Mark Request as Resolved"}
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="flex items-center gap-3 p-3 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-100 dark:border-emerald-800/40 rounded-xl">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
          <p className="text-xs text-emerald-800 dark:text-emerald-300">
            {isIndependent
              ? "Solved your requirement on your own without a helper? That's great! Confirming independent resolution closes your request legitimately without creating any fake helper connections."
              : "Congratulations on making progress! Marking your request resolved will update all remaining open needs to resolved and complete this request."}
          </p>
        </div>

        <div className="space-y-1">
          <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">
            How was your requirement resolved? (Optional)
          </label>
          <textarea
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            placeholder="e.g. Found a great PG in Hinjewadi Phase 1 through community recommendations and connected with Bob for local transit tips."
            rows={3}
            className="w-full text-xs p-3 rounded-xl border border-gray-200 dark:border-brand-dark-border bg-white dark:bg-brand-dark-surface focus:outline-none focus:ring-1 focus:ring-brand-primary"
          />
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={onClose}
            disabled={isSubmitting}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            size="sm"
            disabled={isSubmitting}
            className="bg-emerald-600 hover:bg-emerald-700 text-white"
          >
            {isSubmitting ? "Resolving..." : "Confirm Resolution"}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
