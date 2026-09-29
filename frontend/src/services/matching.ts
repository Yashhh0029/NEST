import { api } from "./api";
import type { FindMatchesPayload, MatchingResultResponse } from "@/types/match";

export const matchingService = {
  async findMatches(payload: FindMatchesPayload): Promise<MatchingResultResponse> {
    const res = await api.post<MatchingResultResponse>("/api/matching/find-matches", payload);
    return res.data;
  },
};
