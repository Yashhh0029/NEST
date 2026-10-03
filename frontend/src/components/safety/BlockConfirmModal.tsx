import React, { useState } from "react";
import { AlertTriangle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { blockUser } from "@/services/safety";

export interface BlockConfirmModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm?: () => Promise<void>;
  onSuccess?: () => void;
  userName?: string;
  targetName?: string;
  targetUserId?: string;
  isSubmitting?: boolean;
}

export const BlockConfirmModal: React.FC<BlockConfirmModalProps> = ({
  isOpen,
  onClose,
  onConfirm,
  onSuccess,
  userName,
  targetName,
  targetUserId,
  isSubmitting: externalIsSubmitting = false,
}) => {
  const [internalSubmitting, setInternalSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const displayName = userName || targetName || "Member";
  const isSubmitting = externalIsSubmitting || internalSubmitting;

  const handleConfirm = async () => {
    setError(null);
    if (onConfirm) {
      await onConfirm();
      return;
    }

    if (targetUserId) {
      try {
        setInternalSubmitting(true);
        await blockUser(targetUserId);
        if (onSuccess) onSuccess();
        onClose();
      } catch (err: any) {
        const msg = err.response?.data?.detail || "Failed to block user. Please try again.";
        setError(msg);
      } finally {
        setInternalSubmitting(false);
      }
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/50 backdrop-blur-sm animate-fade-in">
      <div className="bg-white dark:bg-brand-dark-card border border-gray-200 dark:border-brand-dark-border rounded-2xl p-4 sm:p-6 max-w-md w-full max-h-[calc(100dvh-2rem)] overflow-y-auto shadow-2xl space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-red-100 dark:bg-red-950/60 text-red-600 dark:text-red-400 flex items-center justify-center shrink-0">
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 font-heading">
              Block {displayName}?
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Safety & trust restriction
            </p>
          </div>
        </div>

        <p className="text-sm text-gray-600 dark:text-gray-300 leading-relaxed">
          They will no longer be able to message you, send you connection requests, or appear in your helper recommendations. Any existing messages you exchanged will remain visible as historical records.
        </p>

        {error && (
          <p className="text-xs text-red-600 bg-red-50 dark:bg-red-950/40 p-2.5 rounded-xl border border-red-200">
            {error}
          </p>
        )}

        <div className="flex flex-col-reverse sm:flex-row items-center justify-end gap-2.5 pt-3 border-t border-gray-100 dark:border-brand-dark-border">
          <Button
            variant="outline"
            size="sm"
            onClick={onClose}
            disabled={isSubmitting}
            className="w-full sm:w-auto"
          >
            Cancel
          </Button>
          <Button
            variant="primary"
            size="sm"
            onClick={handleConfirm}
            disabled={isSubmitting}
            className="w-full sm:w-auto bg-red-600 hover:bg-red-700 text-white border-transparent"
          >
            {isSubmitting ? (
              <span className="flex items-center justify-center gap-1.5">
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                Blocking...
              </span>
            ) : (
              "Block User"
            )}
          </Button>
        </div>
      </div>
    </div>
  );
};
