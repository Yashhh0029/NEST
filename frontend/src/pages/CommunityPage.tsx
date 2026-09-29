import React, { useEffect, useState, useCallback } from "react";
import {
  Search,
  PlusCircle,
  HelpCircle,
  Loader2,
  MapPin,
  X,
  Compass,
} from "lucide-react";
import { Button } from "@/components/ui/Button";
import { communityService } from "@/services/community";
import { QuestionCard } from "@/components/community/QuestionCard";
import { AskQuestionModal } from "@/components/community/AskQuestionModal";
import type {
  CommunityQuestion,
  QuestionCategory,
  QuestionSearchParams,
} from "@/types/community";

const CATEGORIES: { value: QuestionCategory | "ALL"; label: string }[] = [
  { value: "ALL", label: "All Topics" },
  { value: "HOUSING", label: "Housing & PGs" },
  { value: "FOOD", label: "Food & Mess" },
  { value: "TRANSPORT", label: "Transport" },
  { value: "JOBS", label: "Jobs" },
  { value: "LOCAL_SERVICES", label: "Local Services" },
  { value: "SAFETY", label: "Safety" },
  { value: "DAILY_LIFE", label: "Daily Life" },
  { value: "OTHER", label: "Other" },
];

export const CommunityPage: React.FC = () => {
  const [questions, setQuestions] = useState<CommunityQuestion[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<QuestionCategory | "ALL">("ALL");
  const [cityFilter, setCityFilter] = useState("");
  const [areaFilter, setAreaFilter] = useState("");

  const [isAskModalOpen, setIsAskModalOpen] = useState(false);

  const fetchQuestions = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: QuestionSearchParams = {};
      if (searchQuery.trim()) params.q = searchQuery.trim();
      if (selectedCategory !== "ALL") params.category = selectedCategory;
      if (cityFilter.trim()) params.city = cityFilter.trim();
      if (areaFilter.trim()) params.area = areaFilter.trim();

      const res = await communityService.searchQuestions(params);
      setQuestions(res.questions);
      setTotal(res.total);
    } catch (err: any) {
      setError("Unable to load community questions. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [searchQuery, selectedCategory, cityFilter, areaFilter]);

  useEffect(() => {
    fetchQuestions();
  }, [fetchQuestions]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchQuestions();
  };

  const handleQuestionCreated = (newQ: CommunityQuestion) => {
    setQuestions((prev) => [newQ, ...prev]);
    setTotal((prev) => prev + 1);
  };

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-teal-600 dark:text-teal-400 font-semibold text-xs uppercase tracking-wider mb-1">
            <Compass className="w-4 h-4" />
            <span>Real Local Knowledge</span>
          </div>
          <h1 className="font-heading font-extrabold text-2xl sm:text-3xl text-gray-900 dark:text-gray-100">
            Community Intelligence Network
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Ask questions, discover neighborhood insights, and get advice from verified neighbors.
          </p>
        </div>

        <Button
          onClick={() => setIsAskModalOpen(true)}
          className="flex items-center gap-2 self-start sm:self-auto shrink-0"
        >
          <PlusCircle className="w-4 h-4" />
          Ask Question
        </Button>
      </div>

      {/* Search & Location Filters */}
      <div className="bg-white dark:bg-brand-dark-card border border-gray-200 dark:border-brand-dark-border rounded-2xl p-4 sm:p-5 shadow-sm space-y-4">
        <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-3 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search community questions, places, topics..."
              className="w-full pl-10 pr-10 py-2.5 rounded-xl border border-gray-200 dark:border-brand-dark-border bg-gray-50 dark:bg-brand-dark text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-primary"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                className="absolute right-3 top-3 text-gray-400 hover:text-gray-600"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          <div className="flex gap-2">
            <div className="relative w-36">
              <MapPin className="absolute left-2.5 top-3 w-3.5 h-3.5 text-gray-400" />
              <input
                type="text"
                value={cityFilter}
                onChange={(e) => setCityFilter(e.target.value)}
                placeholder="City"
                className="w-full pl-8 pr-2 py-2.5 rounded-xl border border-gray-200 dark:border-brand-dark-border bg-gray-50 dark:bg-brand-dark text-xs text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-primary"
              />
            </div>
            <div className="relative w-36">
              <input
                type="text"
                value={areaFilter}
                onChange={(e) => setAreaFilter(e.target.value)}
                placeholder="Area"
                className="w-full px-3 py-2.5 rounded-xl border border-gray-200 dark:border-brand-dark-border bg-gray-50 dark:bg-brand-dark text-xs text-gray-900 dark:text-gray-100 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-brand-primary"
              />
            </div>
            <Button type="submit" size="sm" className="px-4 text-xs">
              Search
            </Button>
          </div>
        </form>

        {/* Category Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1 no-scrollbar">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.value}
              onClick={() => setSelectedCategory(cat.value)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-colors ${
                selectedCategory === cat.value
                  ? "bg-teal-600 text-white shadow-xs"
                  : "bg-gray-100 dark:bg-brand-dark text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-brand-dark-border"
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content Area */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-16 space-y-3">
          <Loader2 className="w-8 h-8 text-teal-600 animate-spin" />
          <p className="text-sm text-gray-400">Loading community discussions...</p>
        </div>
      ) : error ? (
        <div className="p-6 text-center rounded-2xl bg-rose-50 dark:bg-rose-950/30 border border-rose-200 text-rose-700 dark:text-rose-300 text-sm">
          {error}
        </div>
      ) : questions.length > 0 ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>
              Showing {questions.length} of {total} {total === 1 ? "question" : "questions"}
            </span>
          </div>

          <div className="grid grid-cols-1 gap-4">
            {questions.map((q) => (
              <QuestionCard key={q.id} question={q} />
            ))}
          </div>
        </div>
      ) : (
        /* Honest empty state — no fake questions or activity */
        <div className="text-center py-16 px-4 bg-white dark:bg-brand-dark-card border border-dashed border-gray-200 dark:border-brand-dark-border rounded-3xl space-y-4">
          <div className="w-14 h-14 rounded-2xl bg-gray-100 dark:bg-brand-dark flex items-center justify-center mx-auto text-gray-400">
            <HelpCircle className="w-7 h-7" />
          </div>
          <div>
            <h3 className="font-heading font-bold text-lg text-gray-900 dark:text-gray-100">
              No questions found
            </h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 max-w-md mx-auto mt-1">
              {searchQuery || selectedCategory !== "ALL" || cityFilter || areaFilter
                ? "Try adjusting your filters or search keywords."
                : "No community questions have been posted yet. Start the conversation in your neighborhood!"}
            </p>
          </div>
          <Button
            onClick={() => setIsAskModalOpen(true)}
            className="inline-flex items-center gap-2"
          >
            <PlusCircle className="w-4 h-4" />
            Ask the First Question
          </Button>
        </div>
      )}

      {/* Ask Question Modal */}
      <AskQuestionModal
        isOpen={isAskModalOpen}
        onClose={() => setIsAskModalOpen(false)}
        onSuccess={handleQuestionCreated}
        initialCity={cityFilter}
        initialArea={areaFilter}
      />
    </div>
  );
};
