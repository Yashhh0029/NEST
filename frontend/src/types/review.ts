export interface ReviewItem {
  id: string;
  connection_id: string;
  reviewer_id: string;
  reviewee_id: string;
  rating: number;
  comment?: string | null;
  created_at: string;
  reviewer_name?: string | null;
  reviewee_name?: string | null;
}

export interface ReviewCreatePayload {
  rating: number;
  comment?: string;
}

export interface ReputationSummary {
  user_id: string;
  average_rating: number | null;
  review_count: number;
  status: "AVAILABLE" | "UNAVAILABLE";
}

export interface ReviewListResponse {
  total: number;
  reviews: ReviewItem[];
}
