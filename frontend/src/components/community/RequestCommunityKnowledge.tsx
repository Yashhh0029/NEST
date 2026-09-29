import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  HelpCircle,
  MessageSquare,
  CheckCircle2,
  ExternalLink,
  PlusCircle,
  Loader2,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { communityService } from "@/services/community";
import { AskQuestionModal } from "./AskQuestionModal";
import type { CommunityQuestion, CommunityForRequestResponse } from "@/types/community";

interface RequestCommunityKnowledgeProps {
  requestId: string;
  city?: string | null;
  area?: string | null;
}

export const RequestCommunityKnowledge: React.FC<RequestCommunityKnowledgeProps> = ({
  requestId,
  city,
  area,
}) => {
  const [data, setData] = useState<CommunityForRequestResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const fetchRelated = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await communityService.getCommunityForRequest(requestId, 4);
      setData(res);
    } catch (err: any) {
      setError("Unable to load community discussions.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRelated();
  }, [requestId]);

  const handleQuestionCreated = (_newQ: CommunityQuestion) => {
    fetchRelated();
  };

  return (
    <div className="bg-white dark:bg-brand-dark-card border border-gray-200 dark:border-brand-dark-border rounded-2xl p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-xl bg-teal-100 dark:bg-teal-950/60 text-teal-700 dark:text-teal-400 flex items-center justify-center shrink-0">
            <HelpCircle className="w-4 h-4" />
          </div>
          <div>
            <h3 className="font-heading font-bold text-sm text-gray-900 dark:text-gray-100">
              Community Knowledge
            </h3>
            <p className="text-[11px] text-gray-500 dark:text-gray-400">
              Discussions and tips from local neighbors
            </p>
          </div>
        </div>

        <Button
          size="sm"
          variant="outline"
          onClick={() => setIsModalOpen(true)}
          className="text-xs h-8 flex items-center gap-1.5"
        >
          <PlusCircle className="w-3.5 h-3.5 text-teal-600 dark:text-teal-400" />
          Ask Community
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-6">
          <Loader2 className="w-5 h-5 text-teal-600 animate-spin" />
        </div>
      ) : error ? (
        <p className="text-xs text-gray-400 py-3 text-center">{error}</p>
      ) : data && data.items.length > 0 ? (
        <div className="space-y-2.5">
          {data.items.map(({ question: q }) => (
            <Link
              key={q.id}
              to={`/community/${q.id}`}
              className="block p-3 rounded-xl border border-gray-100 dark:border-brand-dark-border/60 hover:border-teal-500/30 hover:bg-gray-50/60 dark:hover:bg-brand-dark/40 transition-colors group"
            >
              <div className="flex items-start justify-between gap-2">
                <span className="font-heading font-semibold text-xs text-gray-800 dark:text-gray-200 group-hover:text-teal-600 dark:group-hover:text-teal-400 transition-colors line-clamp-1">
                  {q.title}
                </span>
                {q.has_accepted_answer && (
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                )}
              </div>
              <div className="flex items-center gap-3 text-[11px] text-gray-400 mt-1">
                <span>{q.category.replace("_", " ")}</span>
                <span>•</span>
                <span className="flex items-center gap-1">
                  <MessageSquare className="w-3 h-3" />
                  {q.answer_count}
                </span>
              </div>
            </Link>
          ))}

          <Link
            to="/community"
            className="flex items-center justify-center gap-1 text-xs text-teal-600 dark:text-teal-400 hover:underline pt-1 font-medium"
          >
            Explore all community questions
            <ExternalLink className="w-3 h-3" />
          </Link>
        </div>
      ) : (
        /* Honest empty state — no manufactured community questions */
        <div className="py-5 text-center px-4 rounded-xl bg-gray-50/60 dark:bg-brand-dark/30 border border-dashed border-gray-200 dark:border-brand-dark-border space-y-2">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            No community discussions found for this request yet.
          </p>
          <button
            onClick={() => setIsModalOpen(true)}
            className="text-xs font-semibold text-teal-600 dark:text-teal-400 hover:underline"
          >
            Be the first to ask the community!
          </button>
        </div>
      )}

      <AskQuestionModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSuccess={handleQuestionCreated}
        initialCity={city || undefined}
        initialArea={area || undefined}
      />
    </div>
  );
};
