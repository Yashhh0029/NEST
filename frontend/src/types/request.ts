export interface ExtractedNeed {
  category: string;
  item: string;
  matched_text: string;
  source?: string;
}

export interface ExtractedLocation {
  city?: string | null;
  area?: string | null;
  state?: string | null;
  country?: string | null;
}

export interface BudgetInfo {
  amount?: number | null;
  currency?: string | null;
  operator?: string | null;
  period?: string | null;
  raw_text?: string | null;
}

export interface ExtractedRequest {
  raw_text: string;
  intent: string;
  location: ExtractedLocation;
  needs: ExtractedNeed[];
  budget?: BudgetInfo | null;
  preferences: string[];
  user_context: string[];
  extraction_method: string;
}

export interface RequestParseResponse {
  raw_text: string;
  extracted: ExtractedRequest;
}

export interface RequestCreatePayload {
  text: string;
}

export interface RequestUpdatePayload {
  text?: string;
  status?: string;
}

export interface NewcomerRequest {
  id: string;
  user_id: string;
  raw_text: string;
  intent?: string | null;
  status: "OPEN" | "MATCHED" | "CLOSED" | string;
  city?: string | null;
  area?: string | null;
  state?: string | null;
  country?: string | null;
  budget_amount?: number | null;
  budget_currency?: string | null;
  budget_period?: string | null;
  budget_operator?: string | null;
  extracted_requirements?: {
    intent?: string;
    location?: ExtractedLocation;
    needs?: ExtractedNeed[];
    budget?: BudgetInfo;
    preferences?: string[];
    user_context?: string[];
  } | null;
  preferences?: string[] | null;
  user_context?: string[] | null;
  extraction_method: string;
  created_at: string;
  updated_at: string;
}
