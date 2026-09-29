import React, { useState } from "react";
import { Star, X } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { createReview } from "@/services/reviews";
import { useToast } from "@/hooks/useToast";

interface ReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  connectionId: string;
  partnerName: string;
  onSuccess: () => void;
}

const RATING_LABELS: Record<number, string> = {
  1: "Needs Improvement",
  2: "Fair",
  3: "Good",
  4: "Very Helpful",
  5: "Exceptional Help",
};

export const ReviewModal: React.FC<ReviewModalProps> = ({
  isOpen,
  onClose,
  connectionId,
  partnerName,
  onSuccess,
}) => {
  const { success: toastSuccess, error: toastError } = useToast();
  const [rating, setRating] = useState<number>(0);
  const [hoverRating, setHoverRating] = useState<number>(0);
  const [comment, setComment] = useState<string>("");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (rating < 1 || rating > 5) {
      setErrorMessage("Please select a rating between 1 and 5 stars.");
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await createReview(connectionId, {
        rating,
        comment: comment.trim() || undefined,
      });
      toastSuccess(`Thank you! Your review for ${partnerName} has been submitted.`);
      onSuccess();
      onClose();
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : null;
      setErrorMessage(msg || "Failed to submit review. Please try again.");
      toastError(msg || "Failed to submit review.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const activeStar = hoverRating || rating;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fade-in">
      <div
        className="w-full max-w-md bg-white dark:bg-brand-dark-card border border-gray-200 dark:border-brand-dark-border rounded-2xl shadow-xl overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-labelledby="review-modal-title"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-brand-dark-border">
          <h2
            id="review-modal-title"
            className="text-lg font-bold text-gray-900 dark:text-gray-100 font-heading"
          >
            Review {partnerName}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded-lg p-1 transition-colors"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          <div className="text-center space-y-2">
            <p className="text-sm text-gray-600 dark:text-gray-300">
              How was your experience collaborating with{" "}
              <span className="font-semibold text-gray-900 dark:text-gray-100">
                {partnerName}
              </span>
              ?
            </p>

            {/* Star selector */}
            <div className="flex items-center justify-center gap-2 pt-2">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  type="button"
                  key={star}
                  onClick={() => setRating(star)}
                  onMouseEnter={() => setHoverRating(star)}
                  onMouseLeave={() => setHoverRating(0)}
                  className="p-1 text-gray-300 dark:text-gray-600 hover:scale-110 transition-transform focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-primary rounded"
                  aria-label={`${star} star${star > 1 ? "s" : ""}`}
                >
                  <Star
                    className={`w-8 h-8 ${
                      star <= activeStar
                        ? "fill-amber-400 text-amber-400 drop-shadow-sm"
                        : "fill-transparent text-gray-300 dark:text-gray-600"
                    }`}
                  />
                </button>
              ))}
            </div>

            <p className="text-xs font-medium text-amber-600 dark:text-amber-400 h-4">
              {activeStar > 0 ? RATING_LABELS[activeStar] : "Select 1 to 5 stars"}
            </p>
          </div>

          {/* Comment text area */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center">
              <label
                htmlFor="review-comment"
                className="text-xs font-semibold text-gray-700 dark:text-gray-300"
              >
                Feedback (Optional)
              </label>
              <span className="text-[11px] text-gray-400">
                {comment.length} / 1000
              </span>
            </div>
            <textarea
              id="review-comment"
              rows={4}
              maxLength={1000}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              placeholder="Share constructive feedback about their responsiveness, helpfulness, and local guidance..."
              className="w-full text-sm px-3.5 py-2.5 rounded-xl border border-gray-200 dark:border-brand-dark-border bg-gray-50/50 dark:bg-brand-dark-muted/30 text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-primary"
            />
          </div>

          {errorMessage && (
            <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 text-xs text-rose-700 dark:text-rose-300">
              {errorMessage}
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-2">
            <Button
              type="button"
              variant="outline"
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
              isLoading={isSubmitting}
              disabled={rating === 0 || isSubmitting}
            >
              Submit Review
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
