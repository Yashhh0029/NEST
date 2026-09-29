import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import {
  ArrowLeft,
  MessageSquare,
  CheckCircle2,
  MapPin,
  Star,
  Flag,
  Trash2,
  Loader2,
  Send,
  AlertCircle,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { useAuthStore } from "@/store/useAuthStore";
import { communityService } from "@/services/community";
import { AnswerItem } from "@/components/community/AnswerItem";
import { ReportModal } from "@/components/safety/ReportModal";
import type {
  CommunityQuestionDetail,
  VoteType,
} from "@/types/community";

export const QuestionDetailPage: React.FC = () => {
  const { questionId } = useParams<{ questionId: string }>();
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const [question, setQuestion] = useState<CommunityQuestionDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // New answer form
  const [answerBody, setAnswerBody] = useState("");
  const [isSubmittingAnswer, setIsSubmittingAnswer] = useState(false);
  const [answerError, setAnswerError] = useState<string | null>(null);

  // Deleting question
  const [isDeletingQuestion, setIsDeletingQuestion] = useState(false);

  // Reporting
  const [reportTarget, setReportTarget] = useState<{
    targetUserId: string;
    targetName: string;
    questionId?: string;
    answerId?: string;
    questionTitle?: string;
    messageSnippet?: string;
  } | null>(null);

  const fetchDetail = useCallback(async () => {
    if (!questionId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await communityService.getQuestionDetail(questionId);
      setQuestion(data);
    } catch (err: any) {
      setError(
        err.response?.status === 404
          ? "This question could not be found."
          : "Failed to load question details."
      );
    } finally {
      setLoading(false);
    }
  }, [questionId]);

  useEffect(() => {
    fetchDetail();
  }, [fetchDetail]);

  const handlePostAnswer = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!questionId || answerBody.trim().length < 10) return;
    setIsSubmittingAnswer(true);
    setAnswerError(null);

    try {
      const createdAnswer = await communityService.createAnswer(questionId, {
        body: answerBody.trim(),
      });
      setAnswerBody("");
      setQuestion((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          answer_count: prev.answer_count + 1,
          answers: [...prev.answers, createdAnswer],
        };
      });
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Failed to post answer. Please try again.";
      setAnswerError(msg);
    } finally {
      setIsSubmittingAnswer(false);
    }
  };

  const handleVote = async (answerId: string, type: VoteType) => {
    if (!questionId) return;
    try {
      const updated = await communityService.voteAnswer(questionId, answerId, type);
      setQuestion((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          answers: prev.answers.map((a) => (a.id === answerId ? updated : a)),
        };
      });
    } catch (err: any) {
      alert(err.response?.data?.detail || "Unable to vote on this answer.");
    }
  };

  const handleRemoveVote = async (answerId: string) => {
    if (!questionId) return;
    try {
      const updated = await communityService.removeAnswerVote(questionId, answerId);
      setQuestion((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          answers: prev.answers.map((a) => (a.id === answerId ? updated : a)),
        };
      });
    } catch (err: any) {
      alert(err.response?.data?.detail || "Unable to remove vote.");
    }
  };

  const handleAcceptAnswer = async (answerId: string) => {
    if (!questionId) return;
    try {
      await communityService.acceptAnswer(questionId, answerId);
      // Re-fetch detail to get full synchronized question and answers status
      fetchDetail();
    } catch (err: any) {
      alert(err.response?.data?.detail || "Unable to update accepted answer.");
    }
  };

  const handleDeleteAnswer = async (answerId: string) => {
    if (!questionId) return;
    try {
      await communityService.deleteAnswer(questionId, answerId);
      setQuestion((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          answer_count: Math.max(0, prev.answer_count - 1),
          answers: prev.answers.filter((a) => a.id !== answerId),
        };
      });
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to delete answer.");
    }
  };

  const handleDeleteQuestion = async () => {
    if (!questionId || !window.confirm("Are you sure you want to delete this question?")) return;
    setIsDeletingQuestion(true);
    try {
      await communityService.deleteQuestion(questionId);
      navigate("/community");
    } catch (err: any) {
      alert(err.response?.data?.detail || "Failed to delete question.");
      setIsDeletingQuestion(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-[50vh] flex flex-col items-center justify-center space-y-3">
        <Loader2 className="w-8 h-8 text-teal-600 animate-spin" />
        <p className="text-sm text-gray-400">Loading discussion...</p>
      </div>
    );
  }

  if (error || !question) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-12 text-center space-y-4">
        <div className="p-6 rounded-2xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 text-rose-700 dark:text-rose-300 text-sm">
          {error || "Question not found."}
        </div>
        <Link to="/community">
          <Button variant="outline" className="text-xs">
            <ArrowLeft className="w-4 h-4 mr-1.5" /> Back to Community
          </Button>
        </Link>
      </div>
    );
  }

  const isQuestionAuthor = user?.id === question.author_id;
  const trust = question.author_trust_signals;

  // Answers sorted: accepted answer first, then highest score/helpful descending
  const sortedAnswers = [...question.answers].sort((a, b) => {
    if (a.is_accepted && !b.is_accepted) return -1;
    if (!a.is_accepted && b.is_accepted) return 1;
    return b.score - a.score;
  });

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-6">
      {/* Back button */}
      <div>
        <Link
          to="/community"
          className="inline-flex items-center gap-1.5 text-xs font-semibold text-gray-500 hover:text-teal-600 dark:hover:text-teal-400 transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Community
        </Link>
      </div>

      {/* Question Details Card */}
      <div className="bg-white dark:bg-brand-dark-card border border-gray-200 dark:border-brand-dark-border rounded-3xl p-6 sm:p-8 shadow-sm space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-[11px] font-bold px-3 py-1 rounded-full bg-teal-50 dark:bg-teal-950/60 text-teal-700 dark:text-teal-300 border border-teal-200 dark:border-teal-900/50 uppercase tracking-wider">
              {question.category.replace("_", " ")}
            </span>
            {(question.city || question.area) && (
              <span className="flex items-center gap-1 text-xs text-gray-600 dark:text-gray-300 bg-gray-100 dark:bg-brand-dark px-2.5 py-0.5 rounded-full border border-gray-200/80 dark:border-brand-dark-border">
                <MapPin className="w-3.5 h-3.5 text-teal-600 dark:text-teal-400" />
                {[question.area, question.city].filter(Boolean).join(", ")}
              </span>
            )}
            {question.has_accepted_answer && (
              <span className="flex items-center gap-1 text-xs font-semibold text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/50 px-2.5 py-0.5 rounded-full border border-emerald-200 dark:border-emerald-900/50">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Resolved
              </span>
            )}
          </div>

          {/* Action buttons (Delete / Report) */}
          <div className="flex items-center gap-2">
            {isQuestionAuthor ? (
              <button
                onClick={handleDeleteQuestion}
                disabled={isDeletingQuestion}
                className="flex items-center gap-1 text-xs font-medium text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 px-2.5 py-1.5 rounded-lg transition-colors"
                title="Delete this question"
              >
                <Trash2 className="w-3.5 h-3.5" />
                Delete
              </button>
            ) : (
              <button
                onClick={() =>
                  setReportTarget({
                    targetUserId: question.author_id,
                    targetName: question.author_name,
                    questionId: question.id,
                    questionTitle: question.title,
                  })
                }
                className="flex items-center gap-1 text-xs text-gray-400 hover:text-amber-600 px-2.5 py-1.5 rounded-lg hover:bg-amber-50 dark:hover:bg-amber-950/30 transition-colors"
                title="Report question"
              >
                <Flag className="w-3.5 h-3.5" />
                Report
              </button>
            )}
          </div>
        </div>

        <h1 className="font-heading font-extrabold text-2xl sm:text-3xl text-gray-900 dark:text-gray-100 leading-tight">
          {question.title}
        </h1>

        <p className="text-sm sm:text-base text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed">
          {question.body}
        </p>

        {/* Author metadata & trust signals */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-5 border-t border-gray-100 dark:border-brand-dark-border/80">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-full bg-teal-100 dark:bg-teal-900/60 text-teal-800 dark:text-teal-300 flex items-center justify-center font-bold text-sm">
              {question.author_name.charAt(0).toUpperCase()}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-sm text-gray-900 dark:text-gray-100">
                  {question.author_name}
                </span>
                {isQuestionAuthor && (
                  <span className="text-[10px] font-semibold text-teal-700 dark:text-teal-300 bg-teal-50 dark:bg-teal-950/60 px-1.5 py-0.5 rounded border border-teal-200 dark:border-teal-900/50">
                    Author
                  </span>
                )}
              </div>

              {/* Factual reputation signals */}
              <div className="text-xs text-gray-500 dark:text-gray-400">
                {trust && trust.reputation_status === "AVAILABLE" && trust.average_rating !== null ? (
                  <span className="flex items-center gap-1 text-amber-700 dark:text-amber-400 font-medium">
                    <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
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

          <span className="text-xs text-gray-400">
            Asked {new Date(question.created_at).toLocaleDateString(undefined, {
              month: "short",
              day: "numeric",
              year: "numeric",
            })}
          </span>
        </div>
      </div>

      {/* Answers Section */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="font-heading font-bold text-lg text-gray-900 dark:text-gray-100 flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-teal-600 dark:text-teal-400" />
            <span>
              {question.answer_count} {question.answer_count === 1 ? "Answer" : "Answers"}
            </span>
          </h2>
        </div>

        {sortedAnswers.length > 0 ? (
          <div className="space-y-3">
            {sortedAnswers.map((ans) => (
              <AnswerItem
                key={ans.id}
                answer={ans}
                isQuestionAuthor={isQuestionAuthor}
                currentUserId={user?.id}
                onVote={handleVote}
                onRemoveVote={handleRemoveVote}
                onAccept={handleAcceptAnswer}
                onDelete={handleDeleteAnswer}
                onReport={(a) =>
                  setReportTarget({
                    targetUserId: a.author_id,
                    targetName: a.author_name,
                    questionId: question.id,
                    answerId: a.id,
                    messageSnippet: a.body.slice(0, 100),
                  })
                }
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-10 px-4 rounded-2xl bg-white dark:bg-brand-dark-card border border-gray-200 dark:border-brand-dark-border text-gray-500 dark:text-gray-400 text-xs">
            No answers yet. If you know the neighborhood, share your answer below!
          </div>
        )}
      </div>

      {/* Post Answer Section */}
      <div className="bg-white dark:bg-brand-dark-card border border-gray-200 dark:border-brand-dark-border rounded-3xl p-6 shadow-sm space-y-4">
        <h3 className="font-heading font-bold text-base text-gray-900 dark:text-gray-100">
          Your Answer
        </h3>

        {answerError && (
          <div className="flex items-center gap-2 p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 text-rose-700 dark:text-rose-300 text-xs">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{answerError}</span>
          </div>
        )}

        <form onSubmit={handlePostAnswer} className="space-y-3">
          <textarea
            rows={4}
            value={answerBody}
            onChange={(e) => setAnswerBody(e.target.value)}
            placeholder="Write a clear, helpful answer with local knowledge..."
            className="w-full px-3.5 py-3 rounded-2xl border border-gray-200 dark:border-brand-dark-border bg-gray-50 dark:bg-brand-dark text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-primary resize-none"
            disabled={isSubmittingAnswer}
            required
          />

          <div className="flex items-center justify-between">
            <span className="text-[11px] text-gray-400">
              Minimum 10 characters • Respect community guidelines
            </span>

            <Button
              type="submit"
              disabled={isSubmittingAnswer || answerBody.trim().length < 10}
              className="flex items-center gap-1.5 text-xs"
            >
              {isSubmittingAnswer ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  Posting...
                </>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5" />
                  Post Answer
                </>
              )}
            </Button>
          </div>
        </form>
      </div>

      {/* Report Modal */}
      {reportTarget && (
        <ReportModal
          isOpen={!!reportTarget}
          onClose={() => setReportTarget(null)}
          reportedUserId={reportTarget.targetUserId}
          reportedUserName={reportTarget.targetName}
          questionId={reportTarget.questionId}
          answerId={reportTarget.answerId}
          questionTitle={reportTarget.questionTitle}
          messageSnippet={reportTarget.messageSnippet}
          onSuccess={() => {
            alert("Report submitted for review. Thank you for keeping NEST safe.");
          }}
        />
      )}
    </div>
  );
};
