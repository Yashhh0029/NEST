import React, { useState, useEffect } from "react";
import { X, HelpCircle, Loader2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { communityService } from "@/services/community";
import {
  COMMUNITY_CATEGORIES,
  type QuestionCategory,
  type CommunityQuestion,
} from "@/types/community";

interface AskQuestionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (question: CommunityQuestion) => void;
  initialQuestion?: CommunityQuestion | null;
  initialCategory?: QuestionCategory;
  initialCity?: string;
  initialArea?: string;
}

export const AskQuestionModal: React.FC<AskQuestionModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  initialQuestion = null,
  initialCategory,
  initialCity = "",
  initialArea = "",
}) => {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [category, setCategory] = useState<QuestionCategory>("ACCOMMODATION");
  const [city, setCity] = useState(initialCity);
  const [area, setArea] = useState(initialArea);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<{
    title?: string;
    body?: string;
    category?: string;
    city?: string;
    area?: string;
  }>({});

  // Sync state whenever modal opens or props change
  useEffect(() => {
    if (isOpen) {
      if (initialQuestion) {
        setTitle(initialQuestion.title || "");
        setBody(initialQuestion.body || "");
        const rawCat = initialQuestion.category as string;
        const normalizedCat = (rawCat === "HOUSING" ? "ACCOMMODATION" : rawCat) as QuestionCategory;
        setCategory(normalizedCat || "ACCOMMODATION");
        setCity(initialQuestion.city || "");
        setArea(initialQuestion.area || "");
      } else {
        setTitle("");
        setBody("");
        const defCat = initialCategory === "HOUSING" ? "ACCOMMODATION" : (initialCategory || "ACCOMMODATION");
        setCategory(defCat);
        setCity(initialCity);
        setArea(initialArea);
      }
      setError(null);
      setFieldErrors({});
    }
  }, [isOpen, initialQuestion, initialCategory, initialCity, initialArea]);

  if (!isOpen) return null;

  const handleFieldChange = (field: "title" | "body" | "category" | "city" | "area", value: string) => {
    if (field === "title") setTitle(value);
    else if (field === "body") setBody(value);
    else if (field === "category") setCategory(value as QuestionCategory);
    else if (field === "city") setCity(value);
    else if (field === "area") setArea(value);

    // Clear field-level error and general banner when user makes adjustments
    if (fieldErrors[field]) {
      setFieldErrors((prev) => ({ ...prev, [field]: undefined }));
    }
    if (error) setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const newErrors: typeof fieldErrors = {};

    if (title.trim().length < 10) {
      newErrors.title = "Title must be at least 10 characters long.";
    }
    if (body.trim().length < 20) {
      newErrors.body = "Details must be at least 20 characters long.";
    }

    if (Object.keys(newErrors).length > 0) {
      setFieldErrors(newErrors);
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setFieldErrors({});

    try {
      let result: CommunityQuestion;
      if (initialQuestion) {
        result = await communityService.updateQuestion(initialQuestion.id, {
          title: title.trim(),
          body: body.trim(),
          category,
          city: city.trim() || undefined,
          area: area.trim() || undefined,
        });
      } else {
        result = await communityService.createQuestion({
          title: title.trim(),
          body: body.trim(),
          category,
          city: city.trim() || undefined,
          area: area.trim() || undefined,
        });
      }

      setTitle("");
      setBody("");
      onSuccess(result);
      onClose();
    } catch (err: any) {
      const rawDetail = err?.response?.data?.detail;
      const apiFieldErrors: typeof fieldErrors = {};
      let generalMsg = "";

      if (Array.isArray(rawDetail)) {
        for (const item of rawDetail) {
          const loc = item.loc || [];
          const field = loc[loc.length - 1];
          if (field === "category") {
            apiFieldErrors.category = "Please select a valid community category.";
          } else if (field === "title") {
            apiFieldErrors.title = item.msg || "Title must be between 5 and 255 characters.";
          } else if (field === "body") {
            apiFieldErrors.body = item.msg || "Details must be at least 20 characters long.";
          } else if (field === "city") {
            apiFieldErrors.city = item.msg || "City name is too long.";
          } else if (field === "area") {
            apiFieldErrors.area = item.msg || "Area name is too long.";
          } else {
            const strMsg = item.msg || JSON.stringify(item);
            generalMsg = generalMsg ? `${generalMsg}, ${strMsg}` : strMsg;
          }
        }
      } else if (typeof rawDetail === "string") {
        generalMsg = rawDetail;
      } else if (rawDetail && typeof rawDetail === "object") {
        generalMsg = rawDetail.message || JSON.stringify(rawDetail);
      } else if (err?.message) {
        generalMsg = err.message;
      }

      setFieldErrors(apiFieldErrors);
      if (generalMsg) {
        setError(generalMsg);
      } else if (Object.keys(apiFieldErrors).length === 0) {
        setError("Failed to post question. Please try again.");
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  const isEditMode = Boolean(initialQuestion);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/50 backdrop-blur-sm animate-fade-in">
      <div className="bg-white dark:bg-brand-dark-card border border-gray-200 dark:border-brand-dark-border rounded-2xl p-4 sm:p-6 max-w-xl w-full max-h-[calc(100dvh-2rem)] overflow-y-auto shadow-2xl space-y-4 sm:space-y-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-teal-100 dark:bg-teal-950/60 text-teal-700 dark:text-teal-400 flex items-center justify-center shrink-0">
              <HelpCircle className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 font-heading">
                {isEditMode ? "Edit Community Question" : "Ask the Community"}
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
              onChange={(e) => handleFieldChange("title", e.target.value)}
              placeholder="e.g. Which broadband is most reliable near Balewadi High Street?"
              className={`w-full px-3.5 py-2.5 rounded-xl border bg-gray-50 dark:bg-brand-dark text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-primary ${
                fieldErrors.title
                  ? "border-rose-500 dark:border-rose-500"
                  : "border-gray-200 dark:border-brand-dark-border"
              }`}
              disabled={isSubmitting}
              required
            />
            {fieldErrors.title ? (
              <p className="text-[11px] text-rose-500 font-medium mt-1">{fieldErrors.title}</p>
            ) : (
              <p className="text-[11px] text-gray-400 mt-1">Be specific and descriptive (min 10 characters)</p>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                Category *
              </label>
              <select
                value={category}
                onChange={(e) => handleFieldChange("category", e.target.value)}
                className={`w-full px-3 py-2 rounded-xl border bg-gray-50 dark:bg-brand-dark text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-primary ${
                  fieldErrors.category
                    ? "border-rose-500 dark:border-rose-500"
                    : "border-gray-200 dark:border-brand-dark-border"
                }`}
                disabled={isSubmitting}
              >
                {COMMUNITY_CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
              {fieldErrors.category && (
                <p className="text-[11px] text-rose-500 font-medium mt-1">{fieldErrors.category}</p>
              )}
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                City (Optional)
              </label>
              <input
                type="text"
                value={city}
                onChange={(e) => handleFieldChange("city", e.target.value)}
                placeholder="e.g. Pune"
                className={`w-full px-3 py-2 rounded-xl border bg-gray-50 dark:bg-brand-dark text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-primary ${
                  fieldErrors.city
                    ? "border-rose-500 dark:border-rose-500"
                    : "border-gray-200 dark:border-brand-dark-border"
                }`}
                disabled={isSubmitting}
              />
              {fieldErrors.city && (
                <p className="text-[11px] text-rose-500 font-medium mt-1">{fieldErrors.city}</p>
              )}
            </div>
            <div>
              <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                Area / Locality (Optional)
              </label>
              <input
                type="text"
                value={area}
                onChange={(e) => handleFieldChange("area", e.target.value)}
                placeholder="e.g. Baner"
                className={`w-full px-3 py-2 rounded-xl border bg-gray-50 dark:bg-brand-dark text-sm text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-primary ${
                  fieldErrors.area
                    ? "border-rose-500 dark:border-rose-500"
                    : "border-gray-200 dark:border-brand-dark-border"
                }`}
                disabled={isSubmitting}
              />
              {fieldErrors.area && (
                <p className="text-[11px] text-rose-500 font-medium mt-1">{fieldErrors.area}</p>
              )}
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
              Details & Context *
            </label>
            <textarea
              rows={4}
              value={body}
              onChange={(e) => handleFieldChange("body", e.target.value)}
              placeholder="Provide enough details for neighbors to give helpful answers..."
              className={`w-full px-3.5 py-2.5 rounded-xl border bg-gray-50 dark:bg-brand-dark text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-primary resize-none ${
                fieldErrors.body
                  ? "border-rose-500 dark:border-rose-500"
                  : "border-gray-200 dark:border-brand-dark-border"
              }`}
              disabled={isSubmitting}
              required
            />
            {fieldErrors.body ? (
              <p className="text-[11px] text-rose-500 font-medium mt-1">{fieldErrors.body}</p>
            ) : (
              <p className="text-[11px] text-gray-400 mt-1">Minimum 20 characters</p>
            )}
          </div>

          <div className="flex flex-col-reverse sm:flex-row items-center justify-end gap-2.5 pt-3 border-t border-gray-100 dark:border-brand-dark-border">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isSubmitting}
              className="w-full sm:w-auto text-xs"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={isSubmitting || title.trim().length < 10 || body.trim().length < 20}
              className="w-full sm:w-auto text-xs flex items-center justify-center gap-1.5"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  {isEditMode ? "Saving..." : "Posting..."}
                </>
              ) : isEditMode ? (
                "Save Changes"
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
