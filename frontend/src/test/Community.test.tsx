import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { BrowserRouter } from "react-router-dom";
import { AskQuestionModal } from "@/components/community/AskQuestionModal";
import { QuestionCard } from "@/components/community/QuestionCard";
import { AnswerItem } from "@/components/community/AnswerItem";
import { RequestCommunityKnowledge } from "@/components/community/RequestCommunityKnowledge";
import { CommunityPage } from "@/pages/CommunityPage";
import { communityService } from "@/services/community";
import { useAuthStore } from "@/store/useAuthStore";
import type {
  CommunityQuestion,
  CommunityAnswer,
  CommunityForRequestResponse,
  CommunityQuestionListResponse,
} from "@/types/community";

describe("Phase 12: Community Intelligence", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: {
        id: "user-alice",
        name: "Alice Sharma",
        email: "alice@example.com",
        is_verified: true,
        created_at: "2026-01-01T00:00:00Z",
      },
      isAuthenticated: true,
    });
  });

  const mockQuestion: CommunityQuestion = {
    id: "q-1",
    author_id: "user-bob",
    author_name: "Bob Patil",
    title: "Best broadband in Hinjewadi Phase 1?",
    body: "Looking for an ISP with reliable 100Mbps+ speed and low latency for remote work.",
    category: "DAILY_LIFE",
    city: "Pune",
    area: "Hinjewadi",
    status: "OPEN",
    answer_count: 2,
    has_accepted_answer: true,
    created_at: "2026-09-30T00:00:00Z",
    updated_at: "2026-09-30T00:00:00Z",
    author_trust_signals: {
      author_id: "user-bob",
      author_name: "Bob Patil",
      reputation_status: "AVAILABLE",
      average_rating: 4.8,
      review_count: 5,
      completed_interactions_count: 6,
    },
  };

  const mockAnswer: CommunityAnswer = {
    id: "ans-1",
    question_id: "q-1",
    author_id: "user-carol",
    author_name: "Carol Deshmukh",
    body: "Tata Play Fiber and Airtel Xstream have great uptime near Shivaji Chowk.",
    is_accepted: true,
    helpful_count: 4,
    not_helpful_count: 0,
    score: 4,
    created_at: "2026-09-30T01:00:00Z",
    updated_at: "2026-09-30T01:00:00Z",
    user_vote: null,
    author_trust_signals: {
      author_id: "user-carol",
      author_name: "Carol Deshmukh",
      reputation_status: "UNAVAILABLE",
      average_rating: null,
      review_count: 0,
      completed_interactions_count: 0,
    },
  };

  describe("AskQuestionModal", () => {
    it("renders modal when open with form inputs", () => {
      render(
        <AskQuestionModal
          isOpen={true}
          onClose={vi.fn()}
          onSuccess={vi.fn()}
        />
      );

      expect(screen.getByText("Ask the Community")).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/Which broadband is most reliable/i)).toBeInTheDocument();
      expect(screen.getByText("Post Question")).toBeInTheDocument();
    });

    it("validates title and details length before allowing submission", () => {
      render(
        <AskQuestionModal
          isOpen={true}
          onClose={vi.fn()}
          onSuccess={vi.fn()}
        />
      );

      const submitBtn = screen.getByRole("button", { name: /post question/i });
      expect(submitBtn).toBeDisabled();

      const titleInput = screen.getByPlaceholderText(/Which broadband is most reliable/i);
      const detailsInput = screen.getByPlaceholderText(/Provide enough details/i);

      fireEvent.change(titleInput, { target: { value: "Short" } });
      fireEvent.change(detailsInput, { target: { value: "Too short" } });

      expect(submitBtn).toBeDisabled();

      fireEvent.change(titleInput, { target: { value: "Valid question title for community" } });
      fireEvent.change(detailsInput, { target: { value: "This is a detailed description of the community requirement." } });

      expect(submitBtn).not.toBeDisabled();
    });

    it("renders all canonical category options with friendly display labels and ACCOMMODATION for Housing & PGs", () => {
      render(
        <AskQuestionModal
          isOpen={true}
          onClose={vi.fn()}
          onSuccess={vi.fn()}
        />
      );

      const categorySelect = screen.getByRole("combobox") as HTMLSelectElement;
      expect(categorySelect).toBeInTheDocument();

      const options = Array.from(categorySelect.options);
      expect(options.length).toBe(11);

      const housingOption = options.find((o) => o.text.includes("Housing & PGs"));
      expect(housingOption).toBeDefined();
      expect(housingOption?.value).toBe("ACCOMMODATION");

      const expectedCategories = [
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

      for (const expected of expectedCategories) {
        const found = options.find((o) => o.value === expected.value);
        expect(found, `Expected option with value ${expected.value}`).toBeDefined();
        expect(found?.text).toBe(expected.label);
      }
    });

    it("submits the exact scenario from screenshot: Housing & PGs in Kochi, Kakkanad submitting canonical ACCOMMODATION", async () => {
      const onSuccess = vi.fn();
      const mockCreatedQuestion: CommunityQuestion = {
        ...mockQuestion,
        id: "q-kochi-pg",
        title: "Finding reliable PG accommodation near new workplace",
        body: "Looking for recommendations for safe PG accommodation near Infopark Kakkanad with Wi-Fi and food.",
        category: "ACCOMMODATION",
        city: "Kochi",
        area: "Kakkanad",
      };

      const createSpy = vi.spyOn(communityService, "createQuestion").mockResolvedValueOnce(mockCreatedQuestion);

      render(
        <AskQuestionModal
          isOpen={true}
          onClose={vi.fn()}
          onSuccess={onSuccess}
          initialCity="Kochi"
          initialArea="Kakkanad"
        />
      );

      const titleInput = screen.getByPlaceholderText(/Which broadband is most reliable/i);
      const detailsInput = screen.getByPlaceholderText(/Provide enough details/i);
      const categorySelect = screen.getByRole("combobox");

      // Verify category defaults to ACCOMMODATION / Housing & PGs
      expect((categorySelect as HTMLSelectElement).value).toBe("ACCOMMODATION");

      fireEvent.change(titleInput, { target: { value: "Finding reliable PG accommodation near new workplace" } });
      fireEvent.change(detailsInput, {
        target: { value: "Looking for recommendations for safe PG accommodation near Infopark Kakkanad with Wi-Fi and food." },
      });

      const submitBtn = screen.getByRole("button", { name: /post question/i });
      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(createSpy).toHaveBeenCalledTimes(1);
      });

      expect(createSpy).toHaveBeenCalledWith({
        title: "Finding reliable PG accommodation near new workplace",
        category: "ACCOMMODATION",
        city: "Kochi",
        area: "Kakkanad",
        body: "Looking for recommendations for safe PG accommodation near Infopark Kakkanad with Wi-Fi and food.",
      });

      expect(onSuccess).toHaveBeenCalledWith(mockCreatedQuestion);
    });

    it("submits the exact canonical enum value for every category option", async () => {
      const canonicalValues = [
        "ACCOMMODATION",
        "FOOD",
        "TRANSPORT",
        "JOBS",
        "EDUCATION",
        "HEALTHCARE",
        "LOCAL_SERVICES",
        "COST_OF_LIVING",
        "SAFETY",
        "DAILY_LIFE",
        "OTHER",
      ];

      for (const catValue of canonicalValues) {
        const createSpy = vi.spyOn(communityService, "createQuestion").mockResolvedValueOnce({
          ...mockQuestion,
          category: catValue as any,
        });

        const { unmount } = render(
          <AskQuestionModal
            isOpen={true}
            onClose={vi.fn()}
            onSuccess={vi.fn()}
          />
        );

        const titleInput = screen.getByPlaceholderText(/Which broadband is most reliable/i);
        const detailsInput = screen.getByPlaceholderText(/Provide enough details/i);
        const categorySelect = screen.getByRole("combobox");

        fireEvent.change(titleInput, { target: { value: `Valid question title for category ${catValue}` } });
        fireEvent.change(detailsInput, {
          target: { value: `This is a detailed description of the community requirement for ${catValue}.` },
        });
        fireEvent.change(categorySelect, { target: { value: catValue } });

        const submitBtn = screen.getByRole("button", { name: /post question/i });
        fireEvent.click(submitBtn);

        await waitFor(() => {
          expect(createSpy).toHaveBeenCalledWith(
            expect.objectContaining({
              category: catValue,
            })
          );
        });

        unmount();
      }
    });

    it("displays field-level validation errors cleanly when backend returns 422 errors", async () => {
      vi.spyOn(communityService, "createQuestion").mockRejectedValueOnce({
        response: {
          status: 422,
          data: {
            detail: [
              {
                loc: ["body", "category"],
                msg: "Input should be 'ACCOMMODATION', 'TRANSPORT'...",
                type: "enum",
              },
            ],
          },
        },
      });

      render(
        <AskQuestionModal
          isOpen={true}
          onClose={vi.fn()}
          onSuccess={vi.fn()}
        />
      );

      const titleInput = screen.getByPlaceholderText(/Which broadband is most reliable/i);
      const detailsInput = screen.getByPlaceholderText(/Provide enough details/i);

      fireEvent.change(titleInput, { target: { value: "Valid question title for community" } });
      fireEvent.change(detailsInput, { target: { value: "This is a detailed description of the community requirement." } });

      const submitBtn = screen.getByRole("button", { name: /post question/i });
      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(screen.getByText("Please select a valid community category.")).toBeInTheDocument();
      });

      // Verify it didn't dump raw backend enum message in alert
      expect(screen.queryByText(/Input should be 'ACCOMMODATION'/i)).not.toBeInTheDocument();
    });

    it("preserves category and values in edit mode", async () => {
      const onSuccess = vi.fn();
      const updateSpy = vi.spyOn(communityService, "updateQuestion").mockResolvedValueOnce({
        ...mockQuestion,
        title: "Updated PG accommodation title",
        category: "ACCOMMODATION",
      });

      render(
        <AskQuestionModal
          isOpen={true}
          onClose={vi.fn()}
          onSuccess={onSuccess}
          initialQuestion={{
            ...mockQuestion,
            category: "ACCOMMODATION",
          }}
        />
      );

      expect(screen.getByText("Edit Community Question")).toBeInTheDocument();
      const categorySelect = screen.getByRole("combobox") as HTMLSelectElement;
      expect(categorySelect.value).toBe("ACCOMMODATION");

      const titleInput = screen.getByPlaceholderText(/Which broadband is most reliable/i);
      fireEvent.change(titleInput, { target: { value: "Updated PG accommodation title" } });

      const submitBtn = screen.getByRole("button", { name: /save changes/i });
      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(updateSpy).toHaveBeenCalledWith(
          mockQuestion.id,
          expect.objectContaining({
            title: "Updated PG accommodation title",
            category: "ACCOMMODATION",
          })
        );
      });
    });
  });

  describe("QuestionCard", () => {
    it("displays title, category badge, location, and answer count", () => {
      render(
        <BrowserRouter>
          <QuestionCard question={mockQuestion} />
        </BrowserRouter>
      );

      expect(screen.getByText("Best broadband in Hinjewadi Phase 1?")).toBeInTheDocument();
      expect(screen.getByText("DAILY LIFE")).toBeInTheDocument();
      expect(screen.getByText("Hinjewadi, Pune")).toBeInTheDocument();
      expect(screen.getByText("2")).toBeInTheDocument();
      expect(screen.getByText("Resolved")).toBeInTheDocument();
      expect(screen.getByText("4.8")).toBeInTheDocument();
      expect(screen.getByText("(5 reviews)")).toBeInTheDocument();
    });

    it("displays 'New member — reputation unavailable' when review count is 0", () => {
      const newMemberQ: CommunityQuestion = {
        ...mockQuestion,
        author_trust_signals: {
          author_id: "user-new",
          author_name: "New Person",
          reputation_status: "UNAVAILABLE",
          average_rating: null,
          review_count: 0,
          completed_interactions_count: 0,
        },
      };

      render(
        <BrowserRouter>
          <QuestionCard question={newMemberQ} />
        </BrowserRouter>
      );

      expect(screen.getByText(/New member — reputation unavailable/i)).toBeInTheDocument();
    });
  });

  describe("AnswerItem", () => {
    it("renders answer body, author, and Accepted Answer badge", () => {
      render(
        <AnswerItem
          answer={mockAnswer}
          isQuestionAuthor={false}
          currentUserId="user-alice"
          onVote={vi.fn()}
          onRemoveVote={vi.fn()}
          onAccept={vi.fn()}
          onDelete={vi.fn()}
          onReport={vi.fn()}
        />
      );

      expect(screen.getByText(/Tata Play Fiber and Airtel Xstream/i)).toBeInTheDocument();
      expect(screen.getByText("Carol Deshmukh")).toBeInTheDocument();
      expect(screen.getByText("Accepted Answer")).toBeInTheDocument();
      expect(screen.getByText("Helpful (4)")).toBeInTheDocument();
      expect(screen.getByText("Not Helpful (0)")).toBeInTheDocument();
      expect(screen.getByText(/New member — reputation unavailable/i)).toBeInTheDocument();
    });

    it("disables voting on own answer and indicates 'You'", () => {
      render(
        <AnswerItem
          answer={mockAnswer}
          isQuestionAuthor={false}
          currentUserId="user-carol"
          onVote={vi.fn()}
          onRemoveVote={vi.fn()}
          onAccept={vi.fn()}
          onDelete={vi.fn()}
          onReport={vi.fn()}
        />
      );

      expect(screen.getByText("You")).toBeInTheDocument();
      const voteBtns = screen.getAllByTitle("You cannot vote on your own answer");
      expect(voteBtns).toHaveLength(2);
      expect(voteBtns[0]).toBeDisabled();
      expect(voteBtns[1]).toBeDisabled();
    });

    it("renders 'Accept as Best Answer' button only for question author", () => {
      const { rerender } = render(
        <AnswerItem
          answer={{ ...mockAnswer, is_accepted: false }}
          isQuestionAuthor={false}
          currentUserId="user-alice"
          onVote={vi.fn()}
          onRemoveVote={vi.fn()}
          onAccept={vi.fn()}
          onDelete={vi.fn()}
          onReport={vi.fn()}
        />
      );

      expect(screen.queryByText(/Accept as Best Answer/i)).not.toBeInTheDocument();

      rerender(
        <AnswerItem
          answer={{ ...mockAnswer, is_accepted: false }}
          isQuestionAuthor={true}
          currentUserId="user-bob"
          onVote={vi.fn()}
          onRemoveVote={vi.fn()}
          onAccept={vi.fn()}
          onDelete={vi.fn()}
          onReport={vi.fn()}
        />
      );

      expect(screen.getByText(/Accept as Best Answer/i)).toBeInTheDocument();
    });
  });

  describe("RequestCommunityKnowledge", () => {
    it("renders related questions when available", async () => {
      const mockResponse: CommunityForRequestResponse = {
        request_id: "req-1",
        total: 1,
        items: [{ question: mockQuestion, relevance_score: 0.95 }],
      };

      vi.spyOn(communityService, "getCommunityForRequest").mockResolvedValue(mockResponse);

      render(
        <BrowserRouter>
          <RequestCommunityKnowledge requestId="req-1" city="Pune" area="Baner" />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Community Knowledge")).toBeInTheDocument();
        expect(screen.getByText("Best broadband in Hinjewadi Phase 1?")).toBeInTheDocument();
      });
    });

    it("displays honest empty state when no discussions exist", async () => {
      const emptyResponse: CommunityForRequestResponse = {
        request_id: "req-2",
        total: 0,
        items: [],
      };

      vi.spyOn(communityService, "getCommunityForRequest").mockResolvedValue(emptyResponse);

      render(
        <BrowserRouter>
          <RequestCommunityKnowledge requestId="req-2" />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(
          screen.getByText(/No community discussions found for this request yet/i)
        ).toBeInTheDocument();
        expect(screen.getByText(/Be the first to ask the community!/i)).toBeInTheDocument();
      });
    });
  });

  describe("CommunityPage", () => {
    it("renders page header and searches questions", async () => {
      const listResponse: CommunityQuestionListResponse = {
        total: 1,
        questions: [mockQuestion],
      };

      vi.spyOn(communityService, "searchQuestions").mockResolvedValue(listResponse);

      render(
        <BrowserRouter>
          <CommunityPage />
        </BrowserRouter>
      );

      expect(screen.getByText("Community Intelligence Network")).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/Search community questions/i)).toBeInTheDocument();

      await waitFor(() => {
        expect(screen.getByText("Best broadband in Hinjewadi Phase 1?")).toBeInTheDocument();
      });
    });

    it("displays honest empty state when 0 questions are returned", async () => {
      const emptyResponse: CommunityQuestionListResponse = {
        total: 0,
        questions: [],
      };

      vi.spyOn(communityService, "searchQuestions").mockResolvedValue(emptyResponse);

      render(
        <BrowserRouter>
          <CommunityPage />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("No questions found")).toBeInTheDocument();
        expect(screen.getByText(/Ask the First Question/i)).toBeInTheDocument();
      });
    });
  });
});
