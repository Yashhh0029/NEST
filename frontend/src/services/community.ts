import { api } from "./api";
import type {
  CommunityQuestion,
  CommunityQuestionDetail,
  CommunityQuestionListResponse,
  CommunityAnswer,
  QuestionSearchParams,
  QuestionCreateInput,
  AnswerCreateInput,
  VoteType,
  CommunityForRequestResponse,
} from "@/types/community";

export const communityService = {
  /**
   * Search and list community questions with optional semantic search and filters.
   */
  async searchQuestions(params?: QuestionSearchParams): Promise<CommunityQuestionListResponse> {
    const cleanParams: Record<string, string | number> = {};
    if (params?.q?.trim()) cleanParams.q = params.q.trim();
    if (params?.category && params.category !== "ALL") cleanParams.category = params.category;
    if (params?.city?.trim()) cleanParams.city = params.city.trim();
    if (params?.area?.trim()) cleanParams.area = params.area.trim();
    if (params?.status) cleanParams.status = params.status;
    if (params?.limit) cleanParams.limit = params.limit;
    if (params?.offset) cleanParams.offset = params.offset;

    const { data } = await api.get<CommunityQuestionListResponse>("/api/community/questions", {
      params: cleanParams,
    });
    return data;
  },

  /**
   * Get single question with all answers, author trust signals, and current user votes.
   */
  async getQuestionDetail(questionId: string): Promise<CommunityQuestionDetail> {
    const { data } = await api.get<CommunityQuestionDetail>(`/api/community/questions/${questionId}`);
    return data;
  },

  /**
   * Post a new community question.
   */
  async createQuestion(input: QuestionCreateInput): Promise<CommunityQuestion> {
    const { data } = await api.post<CommunityQuestion>("/api/community/questions", input);
    return data;
  },

  /**
   * Update question (author only).
   */
  async updateQuestion(questionId: string, input: Partial<QuestionCreateInput>): Promise<CommunityQuestion> {
    const { data } = await api.patch<CommunityQuestion>(`/api/community/questions/${questionId}`, input);
    return data;
  },

  /**
   * Delete question (author only).
   */
  async deleteQuestion(questionId: string): Promise<{ success: boolean; message: string }> {
    const { data } = await api.delete<{ success: boolean; message: string }>(
      `/api/community/questions/${questionId}`
    );
    return data;
  },

  /**
   * Post an answer to a question.
   */
  async createAnswer(questionId: string, input: AnswerCreateInput): Promise<CommunityAnswer> {
    const { data } = await api.post<CommunityAnswer>(
      `/api/community/questions/${questionId}/answers`,
      input
    );
    return data;
  },

  /**
   * Update an existing answer (author only).
   */
  async updateAnswer(
    questionId: string,
    answerId: string,
    input: AnswerCreateInput
  ): Promise<CommunityAnswer> {
    const { data } = await api.patch<CommunityAnswer>(
      `/api/community/questions/${questionId}/answers/${answerId}`,
      input
    );
    return data;
  },

  /**
   * Delete an answer (author only).
   */
  async deleteAnswer(
    questionId: string,
    answerId: string
  ): Promise<{ success: boolean; message: string }> {
    const { data } = await api.delete<{ success: boolean; message: string }>(
      `/api/community/questions/${questionId}/answers/${answerId}`
    );
    return data;
  },

  /**
   * Cast or update a vote on an answer (HELPFUL / NOT_HELPFUL).
   */
  async voteAnswer(
    questionId: string,
    answerId: string,
    voteType: VoteType
  ): Promise<CommunityAnswer> {
    const { data } = await api.post<CommunityAnswer>(
      `/api/community/questions/${questionId}/answers/${answerId}/vote`,
      { vote_type: voteType }
    );
    return data;
  },

  /**
   * Remove user's vote on an answer.
   */
  async removeAnswerVote(
    questionId: string,
    answerId: string
  ): Promise<CommunityAnswer> {
    const { data } = await api.delete<CommunityAnswer>(
      `/api/community/questions/${questionId}/answers/${answerId}/vote`
    );
    return data;
  },

  /**
   * Toggle accepted status on an answer (question author only).
   */
  async acceptAnswer(
    questionId: string,
    answerId: string
  ): Promise<CommunityAnswer> {
    const { data } = await api.post<CommunityAnswer>(
      `/api/community/questions/${questionId}/answers/${answerId}/accept`
    );
    return data;
  },

  /**
   * Surface related community questions for a specific request.
   */
  async getCommunityForRequest(
    requestId: string,
    limit: number = 5
  ): Promise<CommunityForRequestResponse> {
    const { data } = await api.get<CommunityForRequestResponse>(
      `/api/community/for-request/${requestId}`,
      { params: { limit } }
    );
    return data;
  },
};
