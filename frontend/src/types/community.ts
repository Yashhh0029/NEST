export type QuestionCategory =
  | "ACCOMMODATION"
  | "HOUSING" // Legacy alias mapped to ACCOMMODATION
  | "TRANSPORT"
  | "FOOD"
  | "SAFETY"
  | "JOBS"
  | "EDUCATION"
  | "HEALTHCARE"
  | "LOCAL_SERVICES"
  | "COST_OF_LIVING"
  | "DAILY_LIFE"
  | "OTHER";

export interface CategoryOption {
  value: QuestionCategory;
  label: string;
}

export const COMMUNITY_CATEGORIES: CategoryOption[] = [
  { value: "ACCOMMODATION", label: "Housing & PGs" },
  { value: "FOOD", label: "Food & Mess" },
  { value: "TRANSPORT", label: "Commute & Transport" },
  { value: "JOBS", label: "Jobs & Careers" },
  { value: "EDUCATION", label: "Education & Learning" },
  { value: "HEALTHCARE", label: "Healthcare & Medical" },
  { value: "LOCAL_SERVICES", label: "Local Services & Repairs" },
  { value: "COST_OF_LIVING", label: "Cost of Living & Finance" },
  { value: "SAFETY", label: "Safety & Community" },
  { value: "DAILY_LIFE", label: "Daily Life & Essentials" },
  { value: "OTHER", label: "Other" },
];

export const CATEGORY_LABELS: Record<string, string> = {
  ACCOMMODATION: "Housing & PGs",
  HOUSING: "Housing & PGs",
  FOOD: "Food & Mess",
  TRANSPORT: "Commute & Transport",
  JOBS: "Jobs & Careers",
  EDUCATION: "Education & Learning",
  HEALTHCARE: "Healthcare & Medical",
  LOCAL_SERVICES: "Local Services & Repairs",
  COST_OF_LIVING: "Cost of Living & Finance",
  SAFETY: "Safety & Community",
  DAILY_LIFE: "Daily Life & Essentials",
  OTHER: "Other",
};

export const getCategoryLabel = (category?: string | null): string => {
  if (!category) return "Other";
  return CATEGORY_LABELS[category] || category.replace(/_/g, " ");
};

export type QuestionStatus = "OPEN" | "RESOLVED" | "CLOSED";

export type VoteType = "HELPFUL" | "NOT_HELPFUL";

export interface AuthorTrustSignals {
  author_id: string;
  author_name: string;
  reputation_status: "AVAILABLE" | "UNAVAILABLE";
  average_rating: number | null;
  review_count: number;
  completed_interactions_count: number;
}

export interface CommunityAnswer {
  id: string;
  question_id: string;
  author_id: string;
  author_name?: string;
  author?: {
    id: string;
    name: string;
  } | null;
  body: string;
  is_accepted: boolean;
  helpful_count?: number;
  helpful_votes?: number;
  not_helpful_count?: number;
  not_helpful_votes?: number;
  score?: number;
  created_at: string;
  updated_at: string;
  user_vote?: VoteType | null;
  author_trust_signals?: AuthorTrustSignals | null;
}

export interface CommunityQuestion {
  id: string;
  author_id: string;
  author_name?: string;
  author?: {
    id: string;
    name: string;
  } | null;
  title: string;
  body: string;
  category: QuestionCategory;
  city?: string | null;
  area?: string | null;
  status: QuestionStatus;
  answer_count?: number;
  answers_count?: number;
  has_accepted_answer: boolean;
  created_at: string;
  updated_at: string;
  author_trust_signals?: AuthorTrustSignals | null;
}

export interface CommunityQuestionDetail extends CommunityQuestion {
  answers: CommunityAnswer[];
}

export interface CommunityQuestionListResponse {
  total: number;
  questions: CommunityQuestion[];
}

export interface QuestionSearchParams {
  q?: string;
  category?: QuestionCategory | "ALL";
  city?: string;
  area?: string;
  status?: QuestionStatus;
  limit?: number;
  offset?: number;
}

export interface QuestionCreateInput {
  title: string;
  body: string;
  category: QuestionCategory;
  city?: string;
  area?: string;
}

export interface AnswerCreateInput {
  body: string;
}

export interface RequestCommunityKnowledgeItem {
  question: CommunityQuestion;
  relevance_score: number;
  accepted_or_top_answer?: CommunityAnswer | null;
}

export interface CommunitySearchItem {
  question: CommunityQuestion;
  similarity_score: number;
  top_answer?: CommunityAnswer | null;
}

export interface CommunitySearchResponse {
  query: string;
  total: number;
  results: CommunitySearchItem[];
}

export interface CommunityForRequestResponse {
  request_id: string;
  total: number;
  items: RequestCommunityKnowledgeItem[];
}

