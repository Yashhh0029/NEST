import React, { useState } from "react";
import {
  ThumbsUp,
  ThumbsDown,
  CheckCircle2,
  Star,
  Flag,
  Trash2,
  Loader2,
  Check,
} from "lucide-react";
import type { CommunityAnswer } from "@/types/community";

interface AnswerItemProps {
  answer: CommunityAnswer;
  isQuestionAuthor: boolean;
  currentUserId?: string;
  onVote: (answerId: string, type: "HELPFUL" | "NOT_HELPFUL") => Promise<void>;
  onRemoveVote: (answerId: string) => Promise<void>;
  onAccept: (answerId: string) => Promise<void>;
  onDelete: (answerId: string) => Promise<void>;
  onReport: (answer: CommunityAnswer) => void;
}

export const AnswerItem: React.FC<AnswerItemProps> = ({
  answer,
  isQuestionAuthor,
  currentUserId,
  onVote,
  onRemoveVote,
  onAccept,
  onDelete,
  onReport,
}) => {
  const [isVoting, setIsVoting] = useState(false);
  const [isAccepting, setIsAccepting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const isAuthor = currentUserId === answer.author_id;
  const trust = answer.author_trust_signals;

  const formattedDate = new Date(answer.created_at).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });

  const handleVoteClick = async (type: "HELPFUL" | "NOT_HELPFUL") => {
    if (isVoting || isAuthor) return;
    setIsVoting(true);
    try {
      if (answer.user_vote === type) {
        await onRemoveVote(answer.id);
      } else {
        await onVote(answer.id, type);
      }
    } finally {
      setIsVoting(false);
    }
  };

  const handleAcceptClick = async () => {
    if (isAccepting || !isQuestionAuthor) return;
    setIsAccepting(true);
    try {
      await onAccept(answer.id);
    } finally {
      setIsAccepting(false);
    }
  };

  const handleDeleteClick = async () => {
    if (isDeleting || !isAuthor) return;
    if (!window.confirm("Are you sure you want to delete this answer?")) return;
    setIsDeleting(true);
    try {
      await onDelete(answer.id);
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div
      className={`p-5 rounded-2xl border transition-all ${
        answer.is_accepted
          ? "bg-emerald-50/40 dark:bg-emerald-950/20 border-emerald-300 dark:border-emerald-800/60 shadow-sm"
          : "bg-white dark:bg-brand-dark-card border-gray-200 dark:border-brand-dark-border"
      }`}
    >
      {/* Accepted Badge */}
      {answer.is_accepted && (
        <div className="flex items-center gap-1.5 text-xs font-bold text-emerald-700 dark:text-emerald-400 mb-3 bg-emerald-100/70 dark:bg-emerald-900/40 px-3 py-1 rounded-lg w-fit border border-emerald-300/80 dark:border-emerald-800/60">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          Accepted Answer
        </div>
      )}

      {/* Author Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-full bg-teal-100 dark:bg-teal-900/60 text-teal-800 dark:text-teal-300 flex items-center justify-center font-bold text-xs">
            {answer.author_name.charAt(0).toUpperCase()}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-sm text-gray-900 dark:text-gray-100">
                {answer.author_name}
              </span>
              {isAuthor && (
                <span className="text-[10px] font-semibold text-teal-700 dark:text-teal-300 bg-teal-50 dark:bg-teal-950/60 px-1.5 py-0.5 rounded border border-teal-200 dark:border-teal-900/50">
                  You
                </span>
              )}
            </div>

            {/* Author Trust Signals (Factual reputation only, no manufactured scores) */}
            <div className="text-[11px] text-gray-500 dark:text-gray-400">
              {trust && trust.reputation_status === "AVAILABLE" && trust.average_rating !== null ? (
                <span className="flex items-center gap-1 text-amber-700 dark:text-amber-400 font-medium">
                  <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                  {trust.average_rating.toFixed(1)}
                  <span className="text-gray-500 dark:text-gray-400 font-normal">
                    ({trust.review_count} {trust.review_count === 1 ? "review" : "reviews"} • {trust.completed_interactions_count} completed)
                  </span>
                </span>
              ) : (
                <span className="text-gray-400 dark:text-gray-500 italic">
                  New member — reputation unavailable
                </span>
              )}
            </div>
          </div>
        </div>

        <span className="text-xs text-gray-400 dark:text-gray-500">{formattedDate}</span>
      </div>

      {/* Answer Body */}
      <p className="text-sm text-gray-800 dark:text-gray-200 whitespace-pre-wrap leading-relaxed mb-4">
        {answer.body}
      </p>

      {/* Footer Controls: Voting, Accept, Report, Delete */}
      <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-gray-100 dark:border-brand-dark-border/60 text-xs">
        <div className="flex items-center gap-2">
          {/* Helpful Vote */}
          <button
            onClick={() => handleVoteClick("HELPFUL")}
            disabled={isVoting || isAuthor}
            title={isAuthor ? "You cannot vote on your own answer" : "Mark as helpful"}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-medium transition-colors ${
              answer.user_vote === "HELPFUL"
                ? "bg-teal-50 dark:bg-teal-950/60 border-teal-500 text-teal-700 dark:text-teal-300 font-semibold"
                : "border-gray-200 dark:border-brand-dark-border text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-brand-dark"
            } ${isAuthor ? "opacity-60 cursor-not-allowed" : ""}`}
          >
            <ThumbsUp className={`w-3.5 h-3.5 ${answer.user_vote === "HELPFUL" ? "fill-teal-600 text-teal-600" : ""}`} />
            <span>Helpful ({answer.helpful_count})</span>
          </button>

          {/* Not Helpful Vote */}
          <button
            onClick={() => handleVoteClick("NOT_HELPFUL")}
            disabled={isVoting || isAuthor}
            title={isAuthor ? "You cannot vote on your own answer" : "Mark as not helpful"}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-medium transition-colors ${
              answer.user_vote === "NOT_HELPFUL"
                ? "bg-rose-50 dark:bg-rose-950/60 border-rose-400 text-rose-700 dark:text-rose-300 font-semibold"
                : "border-gray-200 dark:border-brand-dark-border text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-brand-dark"
            } ${isAuthor ? "opacity-60 cursor-not-allowed" : ""}`}
          >
            <ThumbsDown className={`w-3.5 h-3.5 ${answer.user_vote === "NOT_HELPFUL" ? "fill-rose-600 text-rose-600" : ""}`} />
            <span>Not Helpful ({answer.not_helpful_count})</span>
          </button>
        </div>

        <div className="flex items-center gap-2">
          {/* Question author: Accept answer button */}
          {isQuestionAuthor && (
            <button
              onClick={handleAcceptClick}
              disabled={isAccepting}
              className={`flex items-center gap-1 px-3 py-1 rounded-lg border text-xs font-semibold transition-colors ${
                answer.is_accepted
                  ? "bg-emerald-600 text-white border-emerald-600 hover:bg-emerald-700"
                  : "border-emerald-600 text-emerald-700 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-950/40"
              }`}
            >
              {isAccepting ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : answer.is_accepted ? (
                <>
                  <Check className="w-3.5 h-3.5" />
                  Accepted
                </>
              ) : (
                "Accept as Best Answer"
              )}
            </button>
          )}

          {/* Answer Author: Delete */}
          {isAuthor && (
            <button
              onClick={handleDeleteClick}
              disabled={isDeleting}
              className="p-1.5 text-gray-400 hover:text-rose-600 rounded-lg hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors"
              title="Delete your answer"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          )}

          {/* Report Button */}
          {!isAuthor && (
            <button
              onClick={() => onReport(answer)}
              className="p-1.5 text-gray-400 hover:text-amber-600 rounded-lg hover:bg-amber-50 dark:hover:bg-amber-950/30 transition-colors"
              title="Report this answer"
            >
              <Flag className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
