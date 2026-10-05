import React, { useState } from "react";
import { MessageSquare, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { reactivateConnection } from "@/services/connections";

export interface ReactivateConfirmModalProps {
  isOpen: boolean;
  connectionId?: string;
  onClose: () => void;
  onSuccess?: () => void;
  onConfirm?: () => Promise<void>;
  partnerName?: string;
}

export const ReactivateConfirmModal: React.FC<ReactivateConfirmModalProps> = ({
  isOpen,
  connectionId,
  onClose,
  onSuccess,
  onConfirm,
  partnerName,
}) => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleReactivate = async () => {
    setError(null);
    setIsSubmitting(true);
    try {
      if (onConfirm) {
        await onConfirm();
      } else if (connectionId) {
        await reactivateConnection(connectionId);
      }
      if (onSuccess) {
        onSuccess();
      }
      onClose();
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response
              ?.data?.detail
          : null;
      setError(
        msg || "Failed to reactivate conversation. Please check your connection or safety status."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="reactivate-modal-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/50 backdrop-blur-sm animate-fade-in"
    >
      <div className="bg-white dark:bg-brand-dark-card border border-gray-200 dark:border-brand-dark-border rounded-2xl p-4 sm:p-6 max-w-md w-full max-h-[calc(100dvh-2rem)] overflow-y-auto shadow-2xl space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-brand-primary/10 text-brand-primary flex items-center justify-center shrink-0">
            <MessageSquare className="w-5 h-5" />
          </div>
          <div>
            <h3
              id="reactivate-modal-title"
              className="text-lg font-bold text-gray-900 dark:text-gray-100 font-heading"
            >
              Reactivate conversation?
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {partnerName ? `With ${partnerName}` : "Restore messaging access"}
            </p>
          </div>
        </div>

        <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
          You and the other person will be able to message each other again. Previous messages will remain available.
        </p>

        {error && (
          <p className="text-xs text-red-600 bg-red-50 dark:bg-red-950/40 p-2.5 rounded-xl border border-red-200">
            {error}
          </p>
        )}

        <div className="flex items-center justify-end gap-3 pt-2">
          <Button
            variant="ghost"
            onClick={onClose}
            disabled={isSubmitting}
            className="text-gray-600 dark:text-gray-400"
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            onClick={handleReactivate}
            disabled={isSubmitting}
            className="min-w-[110px]"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                Reactivating...
              </>
            ) : (
              "Reactivate"
            )}
          </Button>
        </div>
      </div>
    </div>
  );
};
export default ReactivateConfirmModal;
