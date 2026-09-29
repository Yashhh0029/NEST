import React, { useState } from "react";
import { X, HelpCircle, Loader2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { communityService } from "@/services/community";
import type { QuestionCategory, CommunityQuestion } from "@/types/community";

interface AskQuestionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (question: CommunityQuestion) => void;
  initialCity?: string;
  initialArea?: string;
}

const CATEGORIES: { value: QuestionCategory; label: string }[] = [
  { value: "HOUSING", label: "Housing & PGs" },
  { value: "FOOD", label: "Food & Mess" },
  { value: "TRANSPORT", label: "Commute & Transport" },
  { value: "JOBS", label: "Jobs & Careers" },
  { value: "LOCAL_SERVICES", label: "Local Services & Repairs" },
  { value: "SAFETY", label: "Safety & Community" },
  { value: "DAILY_LIFE", label: "Daily Life & Essentials" },
  { value: "OTHER", label: "Other" },
];

export const AskQuestionModal: React.FC<AskQuestionModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  initialCity = "",
  initialArea = "",
}) => {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [category, setCategory] = useState<QuestionCategory>("HOUSING");
  const [city, setCity] = useState(initialCity);
  const [area, setArea] = useState(initialArea);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (title.trim().length < 10) {
      setError("Title must be at least 10 characters long.");
      return;
    }
    if (body.trim().length < 20) {
      setError("Details must be at least 20 characters long.");
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const created = await communityService.createQuestion({
        title: title.trim(),
        body: body.trim(),
        category,
        city: city.trim() || undefined,
        area: area.trim() || undefined,
      });
      setTitle("");
      setBody("");
      onSuccess(created);
      onClose();
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Failed to post question. Please try again.";
      setError(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fade-in">
      <div className="bg-white dark:bg-brand-dark-card border border-gray-200 dark:border-brand-dark-border rounded-2xl p-6 max-w-xl w-full shadow-2xl space-y-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-teal-100 dark:bg-teal-950/60 text-teal-700 dark:text-teal-400 flex items-center justify-center shrink-0">
              <HelpCircle className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 font-heading">
                Ask the Community
              </h3>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                Get advice and local knowledge from verified NEST members
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-brand-dark-border/40 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {error && (
          <div className="flex items-center gap-2.5 p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 text-rose-700 dark:text-rose-300 text-xs">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
              Question Title *
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Which broadband is most reliable near Balewadi High Street?"
              className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 dark:border-brand-dark-border bg-gray-50 dark:bg-brand-dark text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-primary"
              disabled={isSubmitting}
              required
            />
            <p className="text-[11px] text-gray-400 mt-1">Be specific and descriptive (min 10 characters)</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                Category *
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value as QuestionCategory)}
                className="w-full px-3 py-2 rounded-xl border border-gray-200 dark:border-brand-dark-border bg-gray-50 dark:bg-brand-dark text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-primary"
                disabled={isSubmitting}
              >
                {CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                City (Optional)
              </label>
              <input
                type="text"
                value={city}
                onChange={(e) => setCity(e.target.value)}
                placeholder="e.g. Pune"
                className="w-full px-3 py-2 rounded-xl border border-gray-200 dark:border-brand-dark-border bg-gray-50 dark:bg-brand-dark text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-primary"
                disabled={isSubmitting}
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                Area / Locality (Optional)
              </label>
              <input
                type="text"
                value={area}
                onChange={(e) => setArea(e.target.value)}
                placeholder="e.g. Baner"
                className="w-full px-3 py-2 rounded-xl border border-gray-200 dark:border-brand-dark-border bg-gray-50 dark:bg-brand-dark text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-primary"
                disabled={isSubmitting}
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
              Details & Context *
            </label>
            <textarea
              rows={4}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Provide enough details for neighbors to give helpful answers..."
              className="w-full px-3.5 py-2.5 rounded-xl border border-gray-200 dark:border-brand-dark-border bg-gray-50 dark:bg-brand-dark text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-primary resize-none"
              disabled={isSubmitting}
              required
            />
            <p className="text-[11px] text-gray-400 mt-1">Minimum 20 characters</p>
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-gray-100 dark:border-brand-dark-border">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isSubmitting}
              className="text-xs"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting || title.trim().length < 10 || body.trim().length < 20}
              className="text-xs flex items-center gap-1.5"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Posting...
                </>
              ) : (
                "Post Question"
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
