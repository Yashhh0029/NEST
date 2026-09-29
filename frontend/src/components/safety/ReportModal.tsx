import React, { useState } from "react";
import { Flag, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";
import { createReport } from "@/services/safety";
import type { ReportReason } from "@/types/safety";

export interface ReportModalProps {
  isOpen: boolean;
  onClose: () => void;
  reportedUserId?: string;
  targetUserId?: string;
  reportedUserName?: string;
  targetName?: string;
  connectionId?: string;
  messageId?: string;
  targetMessageId?: string;
  messageSnippet?: string;
  questionId?: string;
  answerId?: string;
  questionTitle?: string;
  onSuccess?: () => void;
}

const REPORT_REASONS: { value: ReportReason; label: string; desc: string }[] = [
  { value: "HARASSMENT", label: "Harassment or Bullying", desc: "Abusive, degrading, or persistent unwanted contact" },
  { value: "SPAM", label: "Spam or Advertising", desc: "Unsolicited promotional messages or automated bots" },
  { value: "SCAM", label: "Fraud or Financial Scam", desc: "Deceptive schemes, money requests, or phishing" },
  { value: "THREAT", label: "Threat or Physical Violence", desc: "Threats of harm, violence, or dangerous behavior" },
  { value: "INAPPROPRIATE_CONTENT", label: "Inappropriate Content", desc: "Explicit, vulgar, or offensive text or material" },
  { value: "FAKE_PROFILE", label: "Impersonation or Fake Profile", desc: "Using false identity or misrepresenting community credentials" },
  { value: "SAFETY_CONCERN", label: "Safety Risk or Suspicious Behavior", desc: "Actions jeopardizing community trust or offline personal safety" },
  { value: "OTHER", label: "Other Policy Violation", desc: "Other issues violating NEST community standards" },
];

export const ReportModal: React.FC<ReportModalProps> = ({
  isOpen,
  onClose,
  reportedUserId,
  targetUserId,
  reportedUserName,
  targetName,
  connectionId,
  messageId,
  targetMessageId,
  messageSnippet,
  questionId,
  answerId,
  questionTitle,
  onSuccess,
}) => {
  const [selectedReason, setSelectedReason] = useState<ReportReason>("HARASSMENT");
  const [description, setDescription] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSuccess, setIsSuccess] = useState(false);

  if (!isOpen) return null;

  const targetId = reportedUserId || targetUserId || "";
  const displayName = reportedUserName || targetName || "Member";
  const activeMessageId = messageId || targetMessageId;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await createReport({
        reported_user_id: targetId,
        connection_id: connectionId,
        message_id: activeMessageId,
        question_id: questionId,
        answer_id: answerId,
        reason: selectedReason,
        description: description.trim() || undefined,
      });
      setIsSuccess(true);
      if (onSuccess) onSuccess();
      setTimeout(() => {
        setIsSuccess(false);
        setDescription("");
        onClose();
      }, 1500);
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Failed to submit report. Please try again.";
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fade-in">
      <div className="bg-white dark:bg-brand-dark-card border border-gray-200 dark:border-brand-dark-border rounded-2xl p-6 max-w-lg w-full shadow-2xl space-y-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 flex items-center justify-center shrink-0">
            <Flag className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 font-heading">
              Report {questionTitle ? "Question" : activeMessageId ? "Message" : displayName}
            </h3>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Submitted confidentially for administrator review
            </p>
          </div>
        </div>

        {isSuccess ? (
          <div className="py-8 text-center space-y-2">
            <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto animate-bounce" />
            <h4 className="text-base font-bold text-gray-900 dark:text-gray-100">
              Report Submitted
            </h4>
            <p className="text-xs text-gray-500 dark:text-gray-400 max-w-sm mx-auto">
              Thank you for keeping NEST safe. Our moderation team will investigate this report.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {messageSnippet && (
              <div className="p-3 rounded-xl bg-gray-50 dark:bg-brand-dark-muted/30 border border-gray-200 dark:border-brand-dark-border text-xs">
                <span className="font-semibold text-gray-700 dark:text-gray-300 block mb-1">
                  Reported Message:
                </span>
                <p className="text-gray-500 italic dark:text-gray-400 line-clamp-2">
                  &ldquo;{messageSnippet}&rdquo;
                </p>
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">
                Reason for Report <span className="text-red-500">*</span>
              </label>
              <select
                value={selectedReason}
                onChange={(e) => setSelectedReason(e.target.value as ReportReason)}
                className="w-full text-xs p-2.5 rounded-xl border border-gray-200 dark:border-brand-dark-border bg-white dark:bg-brand-dark-card text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-primary"
              >
                {REPORT_REASONS.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label} — {r.desc}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-gray-700 dark:text-gray-300">
                Additional Details (Optional)
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={3}
                maxLength={2000}
                placeholder="Provide context, details, or specific concerns to assist admin review..."
                className="w-full text-xs p-3 rounded-xl border border-gray-200 dark:border-brand-dark-border bg-white dark:bg-brand-dark-card text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-brand-primary placeholder:text-gray-400"
              />
              <span className="text-[10px] text-gray-400 text-right block">
                {description.length} / 2000
              </span>
            </div>

            {errorMessage && (
              <div className="flex items-center gap-2 p-3 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 text-red-700 dark:text-red-300 text-xs">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{errorMessage}</span>
              </div>
            )}

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-gray-100 dark:border-brand-dark-border">
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
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <span className="flex items-center gap-1.5">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Submitting...
                  </span>
                ) : (
                  "Submit Report"
                )}
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
