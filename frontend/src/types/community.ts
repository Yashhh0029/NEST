export type QuestionCategory =
  | "HOUSING"
  | "FOOD"
  | "TRANSPORT"
  | "JOBS"
  | "LOCAL_SERVICES"
  | "SAFETY"
  | "DAILY_LIFE"
  | "OTHER";

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
  author_name: string;
  body: string;
  is_accepted: boolean;
  helpful_count: number;
  not_helpful_count: number;
  score: number;
  created_at: string;
  updated_at: string;
  user_vote?: VoteType | null;
  author_trust_signals: AuthorTrustSignals;
}

export interface CommunityQuestion {
  id: string;
  author_id: string;
  author_name: string;
  title: string;
  body: string;
  category: QuestionCategory;
  city?: string | null;
  area?: string | null;
  status: QuestionStatus;
  answer_count: number;
  has_accepted_answer: boolean;
  created_at: string;
  updated_at: string;
  author_trust_signals: AuthorTrustSignals;
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

export interface CommunityForRequestResponse {
  request_id: string;
  total: number;
  items: RequestCommunityKnowledgeItem[];
}
