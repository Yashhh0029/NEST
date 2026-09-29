import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { BrowserRouter, MemoryRouter, Routes, Route } from "react-router-dom";
import { ChatPage } from "@/pages/ChatPage";
import { ConnectionsPage } from "@/pages/ConnectionsPage";
import * as chatService from "@/services/chat";
import * as connectionsService from "@/services/connections";
import { useAuthStore } from "@/store/useAuthStore";
import type { ConversationItem, MessageItem } from "@/types/chat";
import type { ConnectionItem } from "@/types/connection";

const mockPartner = {
  id: "partner-123",
  name: "Sneha Patil",
  headline: "Local Food & PG Expert",
  city: "Bengaluru",
  area: "Whitefield",
};

const mockConversation: ConversationItem = {
  id: "conv-123",
  connection_id: "conn-active-1",
  partner: mockPartner,
  request: {
    id: "req-1",
    raw_text: "Need budget PG in Whitefield",
    city: "Bengaluru",
    area: "Whitefield",
  },
  created_at: "2026-03-01T10:00:00Z",
  updated_at: "2026-03-01T10:05:00Z",
  unread_count: 0,
};

const mockMessages: MessageItem[] = [
  {
    id: "msg-1",
    conversation_id: "conv-123",
    sender_id: "partner-123",
    sender_name: "Sneha Patil",
    content: "Hi! Welcome to Whitefield. How can I help?",
    is_read: true,
    is_mine: false,
    created_at: "2026-03-01T10:00:00Z",
    updated_at: "2026-03-01T10:00:00Z",
  },
  {
    id: "msg-2",
    conversation_id: "conv-123",
    sender_id: "current-user",
    sender_name: "Current User",
    content: "Looking for recommendations near ITPL.",
    is_read: true,
    is_mine: true,
    created_at: "2026-03-01T10:02:00Z",
    updated_at: "2026-03-01T10:02:00Z",
  },
];

describe("Phase 8 Chat & Messaging Frontend", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useAuthStore.setState({
      user: {
        id: "current-user",
        email: "me@example.test",
        name: "Current User",
        created_at: "2026-01-01T00:00:00Z",
      },
      isAuthenticated: true,
      loading: false,
    });
  });

  describe("ConnectionsPage Message Navigation", () => {
    it("renders Message button for ACTIVE connections and not for PENDING", async () => {
      const mockConnections: ConnectionItem[] = [
        {
          id: "conn-active-1",
          request_id: "req-1",
          requester_id: "current-user",
          helper_id: "partner-123",
          status: "ACCEPTED",
          created_at: "2026-03-01T10:00:00Z",
          updated_at: "2026-03-01T10:00:00Z",
          accepted_at: "2026-03-01T10:00:00Z",
          helper: mockPartner,
        },
        {
          id: "conn-pending-1",
          request_id: "req-2",
          requester_id: "current-user",
          helper_id: "other-user",
          status: "PENDING",
          created_at: "2026-03-01T11:00:00Z",
          updated_at: "2026-03-01T11:00:00Z",
        },
      ];

      vi.spyOn(connectionsService, "listConnections").mockResolvedValue({
        total: 2,
        connections: mockConnections,
      });

      render(
        <BrowserRouter>
          <ConnectionsPage />
        </BrowserRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Connections")).toBeInTheDocument();
      });

      // Switch to Active tab
      const activeTab = screen.getByRole("button", { name: /Active/i });
      fireEvent.click(activeTab);

      await waitFor(() => {
        expect(screen.getByText("Sneha Patil")).toBeInTheDocument();
      });

      // Message button must be visible for active connection
      const messageBtn = screen.getByRole("button", { name: /Message/i });
      expect(messageBtn).toBeInTheDocument();

      // Check link destination
      const link = messageBtn.closest("a");
      expect(link).toHaveAttribute("href", "/chat/conn-active-1");
    });
  });

  describe("ChatPage Component", () => {
    it("loads conversation and renders messages correctly", async () => {
      vi.spyOn(chatService, "getConversationByConnection").mockResolvedValue(mockConversation);
      vi.spyOn(chatService, "getMessages").mockResolvedValue({
        total: 2,
        has_more: false,
        messages: mockMessages,
      });

      render(
        <MemoryRouter initialEntries={["/chat/conn-active-1"]}>
          <Routes>
            <Route path="/chat/:connectionId" element={<ChatPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Sneha Patil")).toBeInTheDocument();
      });

      expect(screen.getByText(/Local Food & PG Expert/i)).toBeInTheDocument();
      expect(screen.getByText(/Need budget PG in Whitefield/i)).toBeInTheDocument();

      // Verify messages rendered
      expect(screen.getByText("Hi! Welcome to Whitefield. How can I help?")).toBeInTheDocument();
      expect(screen.getByText("Looking for recommendations near ITPL.")).toBeInTheDocument();
    });

    it("allows sending a new message and updates message stream", async () => {
      vi.spyOn(chatService, "getConversationByConnection").mockResolvedValue(mockConversation);
      vi.spyOn(chatService, "getMessages").mockResolvedValue({
        total: 2,
        has_more: false,
        messages: mockMessages,
      });

      const newMsg: MessageItem = {
        id: "msg-3",
        conversation_id: "conv-123",
        sender_id: "current-user",
        sender_name: "Current User",
        content: "What about metro connectivity?",
        is_read: false,
        is_mine: true,
        created_at: "2026-03-01T10:05:00Z",
        updated_at: "2026-03-01T10:05:00Z",
      };

      const sendSpy = vi.spyOn(chatService, "sendMessage").mockResolvedValue(newMsg);

      render(
        <MemoryRouter initialEntries={["/chat/conn-active-1"]}>
          <Routes>
            <Route path="/chat/:connectionId" element={<ChatPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Sneha Patil")).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText(/Type a message.../i);
      fireEvent.change(input, { target: { value: "What about metro connectivity?" } });

      const submitBtn = screen.getByRole("button", { name: "" }); // Send button
      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(sendSpy).toHaveBeenCalledWith("conv-123", "What about metro connectivity?");
      });

      expect(screen.getByText("What about metro connectivity?")).toBeInTheDocument();
    });

    it("displays error card when conversation access is forbidden", async () => {
      vi.spyOn(chatService, "getConversationByConnection").mockRejectedValue({
        response: {
          status: 403,
          data: { detail: "Messaging is only allowed for active accepted connections." },
        },
      });

      render(
        <MemoryRouter initialEntries={["/chat/conn-pending-1"]}>
          <Routes>
            <Route path="/chat/:connectionId" element={<ChatPage />} />
          </Routes>
        </MemoryRouter>
      );

      await waitFor(() => {
        expect(screen.getByText("Cannot Open Conversation")).toBeInTheDocument();
      });

      expect(
        screen.getByText("Messaging is only allowed for active accepted connections.")
      ).toBeInTheDocument();
      expect(screen.getByText("Return to Connections")).toBeInTheDocument();
    });
  });
});
