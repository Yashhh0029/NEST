import React from "react";
import { Link } from "react-router-dom";
import { MessageSquare, CheckCircle2, MapPin, Star } from "lucide-react";
import type { CommunityQuestion } from "@/types/community";

interface QuestionCardProps {
  question: CommunityQuestion;
}

const CATEGORY_COLORS: Record<string, string> = {
  HOUSING: "bg-blue-50 text-blue-700 border-blue-200 dark:bg-blue-950/40 dark:text-blue-300 dark:border-blue-900/50",
  FOOD: "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-900/50",
  TRANSPORT: "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-950/40 dark:text-emerald-300 dark:border-emerald-900/50",
  JOBS: "bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-950/40 dark:text-indigo-300 dark:border-indigo-900/50",
  LOCAL_SERVICES: "bg-purple-50 text-purple-700 border-purple-200 dark:bg-purple-950/40 dark:text-purple-300 dark:border-purple-900/50",
  SAFETY: "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-950/40 dark:text-rose-300 dark:border-rose-900/50",
  DAILY_LIFE: "bg-teal-50 text-teal-700 border-teal-200 dark:bg-teal-950/40 dark:text-teal-300 dark:border-teal-900/50",
  OTHER: "bg-gray-100 text-gray-700 border-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:border-gray-700",
};

export const QuestionCard: React.FC<QuestionCardProps> = ({ question }) => {
  const categoryStyle = CATEGORY_COLORS[question.category] || CATEGORY_COLORS.OTHER;
  const trust = question.author_trust_signals;

  const formattedDate = new Date(question.created_at).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });

  return (
    <Link
      to={`/community/${question.id}`}
      className="block bg-white dark:bg-brand-dark-card border border-gray-200 dark:border-brand-dark-border rounded-2xl p-5 hover:border-teal-500/40 hover:shadow-soft dark:hover:border-teal-400/40 transition-all group"
    >
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-3 mb-2">
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border uppercase tracking-wider ${categoryStyle}`}
          >
            {question.category.replace("_", " ")}
          </span>
          {(question.city || question.area) && (
            <span className="flex items-center gap-1 text-[11px] font-medium text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-brand-dark px-2 py-0.5 rounded-full border border-gray-200/60 dark:border-brand-dark-border">
              <MapPin className="w-3 h-3 text-teal-600 dark:text-teal-400" />
              {[question.area, question.city].filter(Boolean).join(", ")}
            </span>
          )}
          {question.has_accepted_answer && (
            <span className="flex items-center gap-1 text-[11px] font-semibold text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/50 px-2 py-0.5 rounded-full border border-emerald-200 dark:border-emerald-900/50">
              <CheckCircle2 className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
              Resolved
            </span>
          )}
        </div>

        <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400 shrink-0">
          <div className="flex items-center gap-1">
            <MessageSquare className="w-3.5 h-3.5" />
            <span className="font-semibold text-gray-700 dark:text-gray-200">
              {question.answer_count}
            </span>{" "}
            {question.answer_count === 1 ? "answer" : "answers"}
          </div>
          <span>•</span>
          <span>{formattedDate}</span>
        </div>
      </div>

      <h3 className="font-heading font-bold text-base text-gray-900 dark:text-gray-100 group-hover:text-brand-primary dark:group-hover:text-teal-400 transition-colors line-clamp-2 mb-1.5">
        {question.title}
      </h3>

      <p className="text-xs text-gray-600 dark:text-gray-300 line-clamp-2 mb-3">
        {question.body}
      </p>

      {/* Author & Trust Signals */}
      <div className="flex items-center justify-between pt-3 border-t border-gray-100 dark:border-brand-dark-border/60 text-xs">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-full bg-teal-100 dark:bg-teal-900/50 text-teal-800 dark:text-teal-300 flex items-center justify-center font-bold text-[11px]">
            {question.author_name.charAt(0).toUpperCase()}
          </div>
          <span className="font-medium text-gray-700 dark:text-gray-300">
            {question.author_name}
          </span>
        </div>

        {trust && (
          <div className="text-[11px] text-gray-500 dark:text-gray-400 flex items-center gap-1.5">
            {trust.reputation_status === "AVAILABLE" && trust.average_rating !== null ? (
              <span className="flex items-center gap-1 font-medium text-amber-700 dark:text-amber-400">
                <Star className="w-3 h-3 fill-amber-400 text-amber-400" />
                {trust.average_rating.toFixed(1)}
                <span className="text-gray-400 dark:text-gray-500 font-normal">
                  ({trust.review_count} {trust.review_count === 1 ? "review" : "reviews"})
                </span>
              </span>
            ) : (
              <span className="text-gray-400 dark:text-gray-500 italic">
                New member — reputation unavailable
              </span>
            )}
          </div>
        )}
      </div>
    </Link>
  );
};
