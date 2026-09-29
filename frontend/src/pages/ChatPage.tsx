import { useState, useEffect, useRef, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { useAuthStore } from "@/store/useAuthStore";
import {
  createConversation,
  getConversationByConnection,
  getMessages,
  sendMessage,
  editMessage,
  deleteMessage,
} from "@/services/chat";
import { useChatSocket } from "@/hooks/useChatSocket";
import type { ConversationItem, MessageItem } from "@/types/chat";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import {
  ArrowLeft,
  Send,
  Loader2,
  MapPin,
  Edit2,
  Trash2,
  Check,
  X,
  FileText,
  AlertCircle,
  Wifi,
  WifiOff,
} from "lucide-react";

export function ChatPage() {
  const { connectionId } = useParams<{ connectionId: string }>();
  const { user } = useAuthStore();

  const [conversation, setConversation] = useState<ConversationItem | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const [inputContent, setInputContent] = useState<string>("");
  const [isSending, setIsSending] = useState<boolean>(false);
  const [sendError, setSendError] = useState<string | null>(null);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingText, setEditingText] = useState<string>("");
  const [isEditing, setIsEditing] = useState<boolean>(false);

  const [hasMore, setHasMore] = useState<boolean>(false);
  const [isLoadingMore, setIsLoadingMore] = useState<boolean>(false);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const messageContainerRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleIncomingRealtimeMessage = useCallback((incoming: MessageItem) => {
    setMessages((prev) => {
      if (prev.some((m) => m.id === incoming.id)) {
        return prev.map((m) => (m.id === incoming.id ? incoming : m));
      }
      return [...prev, incoming];
    });
    setTimeout(scrollToBottom, 50);
  }, []);

  const { isConnected } = useChatSocket({
    conversationId: conversation?.id,
    onMessageReceived: handleIncomingRealtimeMessage,
  });

  // Initialize conversation and messages
  useEffect(() => {
    if (!connectionId) return;

    let isMounted = true;
    setIsLoading(true);
    setError(null);

    const initChat = async () => {
      try {
        let conv: ConversationItem;
        try {
          // Retrieve-only check
          conv = await getConversationByConnection(connectionId);
        } catch (err: unknown) {
          const status =
            err && typeof err === "object" && "response" in err
              ? (err as { response?: { status?: number } }).response?.status
              : null;

          if (status === 404) {
            // First time accessing: create conversation via POST /api/conversations
            conv = await createConversation(connectionId);
          } else {
            throw err;
          }
        }

        if (!isMounted) return;
        setConversation(conv);

        // Fetch messages for conversation
        const msgs = await getMessages(conv.id);
        if (!isMounted) return;
        setMessages(msgs.messages);
        setHasMore(msgs.has_more);
        setTimeout(scrollToBottom, 100);
      } catch (err: unknown) {
        if (!isMounted) return;
        const msg =
          err && typeof err === "object" && "response" in err
            ? (err as { response?: { data?: { detail?: string } } }).response
                ?.data?.detail
            : null;
        setError(
          msg || "Failed to load chat. Only active accepted connections can participate in chat."
        );
      } finally {
        if (isMounted) setIsLoading(false);
      }
    };

    initChat();

    return () => {
      isMounted = false;
    };
  }, [connectionId]);

  const handleSendMessage = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!conversation || !inputContent.trim() || isSending) return;

    const contentToSend = inputContent.trim();
    setIsSending(true);
    setSendError(null);

    try {
      const savedMessage = await sendMessage(conversation.id, contentToSend);
      setInputContent("");

      setMessages((prev) => {
        if (prev.some((m) => m.id === savedMessage.id)) {
          return prev;
        }
        return [...prev, savedMessage];
      });

      setTimeout(scrollToBottom, 50);
    } catch (err: unknown) {
      const msg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response
              ?.data?.detail
          : null;
      setSendError(msg || "Failed to deliver message. Please retry.");
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleStartEdit = (msg: MessageItem) => {
    setEditingId(msg.id);
    setEditingText(msg.content);
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditingText("");
  };

  const handleSaveEdit = async (msgId: string) => {
    if (!editingText.trim() || isEditing) return;
    setIsEditing(true);

    try {
      const updated = await editMessage(msgId, editingText.trim());
      setMessages((prev) =>
        prev.map((m) => (m.id === msgId ? updated : m))
      );
      setEditingId(null);
    } catch {
      // Error handling
    } finally {
      setIsEditing(false);
    }
  };

  const handleDelete = async (msgId: string) => {
    try {
      const deleted = await deleteMessage(msgId);
      setMessages((prev) =>
        prev.map((m) => (m.id === msgId ? deleted : m))
      );
    } catch {
      // Error handling
    }
  };

  const handleLoadOlder = async () => {
    if (!conversation || messages.length === 0 || isLoadingMore || !hasMore)
      return;

    setIsLoadingMore(true);
    try {
      const oldestMessage = messages[0];
      const older = await getMessages(conversation.id, {
        before: oldestMessage.created_at,
        limit: 30,
      });

      setMessages((prev) => [...older.messages, ...prev]);
      setHasMore(older.has_more);
    } catch {
      // Ignore
    } finally {
      setIsLoadingMore(false);
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto py-12 text-center space-y-4">
        <Loader2 className="w-8 h-8 text-brand-primary animate-spin mx-auto" />
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Loading secure human-to-human conversation...
        </p>
      </div>
    );
  }

  if (error || !conversation) {
    return (
      <div className="max-w-xl mx-auto py-12 px-4">
        <Card className="p-8 text-center space-y-4 border-red-200 dark:border-red-950/40 bg-red-50/50 dark:bg-red-950/20">
          <AlertCircle className="w-10 h-10 text-red-500 mx-auto" />
          <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">
            Cannot Open Conversation
          </h2>
          <p className="text-sm text-red-700 dark:text-red-400">
            {error || "Conversation not found."}
          </p>
          <Link to="/connections">
            <Button variant="outline" size="sm">
              <ArrowLeft className="w-4 h-4 mr-1.5" />
              Return to Connections
            </Button>
          </Link>
        </Card>
      </div>
    );
  }

  const partner = conversation.partner;

  return (
    <div className="max-w-3xl mx-auto flex flex-col h-[calc(100vh-8rem)] min-h-[500px] bg-white dark:bg-brand-dark-card rounded-2xl border border-gray-200 dark:border-brand-dark-border shadow-soft overflow-hidden">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200 dark:border-brand-dark-border bg-gray-50/70 dark:bg-brand-dark-muted/20 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <Link
            to="/connections"
            className="p-1.5 rounded-lg text-gray-500 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-200 dark:hover:bg-brand-dark-muted transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center"
            title="Back to Connections"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>

          <div className="w-10 h-10 rounded-xl bg-teal-100 dark:bg-brand-dark-muted text-brand-primary dark:text-teal-300 flex items-center justify-center font-bold font-heading text-base">
            {partner?.name?.charAt(0) || "U"}
          </div>

          <div>
            <div className="flex items-center gap-2">
              <h2 className="font-bold text-sm sm:text-base text-gray-900 dark:text-gray-100 font-heading">
                {partner?.name || "Community Member"}
              </h2>
              <Badge variant="primary" size="sm">
                Connected
              </Badge>
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
              {partner?.headline && <span>{partner.headline}</span>}
              {(partner?.city || partner?.area) && (
                <span className="flex items-center gap-0.5">
                  <MapPin className="w-3 h-3 text-brand-primary" />
                  {[partner.area, partner.city].filter(Boolean).join(", ")}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Live status badge */}
        <div
          className="flex items-center gap-1.5 text-xs text-gray-400"
          title={isConnected ? "Real-time socket active" : "REST polling mode"}
        >
          {isConnected ? (
            <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium text-[11px]">
              <Wifi className="w-3.5 h-3.5" />
              Live
            </span>
          ) : (
            <span className="flex items-center gap-1 text-gray-400 text-[11px]">
              <WifiOff className="w-3.5 h-3.5" />
              REST
            </span>
          )}
        </div>
      </div>

      {/* Associated Request Pill */}
      {conversation.request && (
        <div className="px-4 py-2 bg-teal-50/50 dark:bg-teal-950/20 border-b border-teal-100 dark:border-teal-900/30 text-xs text-gray-600 dark:text-gray-300 flex items-center gap-2">
          <FileText className="w-3.5 h-3.5 text-brand-primary shrink-0" />
          <span className="truncate">
            <strong className="text-gray-800 dark:text-gray-200">
              Request:
            </strong>{" "}
            "{conversation.request.raw_text}"
          </span>
        </div>
      )}

      {/* Message List */}
      <div
        ref={messageContainerRef}
        className="flex-1 overflow-y-auto p-4 space-y-3"
      >
        {hasMore && (
          <div className="text-center pb-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleLoadOlder}
              disabled={isLoadingMore}
              isLoading={isLoadingMore}
            >
              Load earlier messages
            </Button>
          </div>
        )}

        {messages.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <EmptyState
              icon={<Send className="w-8 h-8 text-gray-400" />}
              title="Start the Conversation"
              description="You and your community partner are connected! Send a message to break the ice and collaborate on local requirements."
            />
          </div>
        ) : (
          messages.map((msg) => {
            const isMine = msg.sender_id === user?.id;
            const isDeleted = msg.deleted_at !== null;
            const isEditingThis = editingId === msg.id;

            return (
              <div
                key={msg.id}
                className={`flex flex-col ${
                  isMine ? "items-end" : "items-start"
                }`}
              >
                <div
                  className={`relative group max-w-[85%] sm:max-w-[70%] rounded-2xl px-4 py-2.5 shadow-sm text-sm ${
                    isMine
                      ? "bg-brand-primary text-white rounded-br-none"
                      : "bg-gray-100 dark:bg-brand-dark-muted text-gray-900 dark:text-gray-100 rounded-bl-none"
                  }`}
                >
                  {isEditingThis ? (
                    <div className="space-y-2 py-1 min-w-[220px]">
                      <textarea
                        value={editingText}
                        onChange={(e) => setEditingText(e.target.value)}
                        className="w-full text-xs p-2 rounded-lg bg-white dark:bg-brand-dark-card text-gray-900 dark:text-gray-100 border border-gray-300 focus:outline-none focus:ring-1 focus:ring-brand-primary"
                        rows={2}
                        maxLength={2000}
                      />
                      <div className="flex items-center justify-end gap-1.5">
                        <button
                          onClick={handleCancelEdit}
                          className="px-2 py-1 text-xs rounded hover:bg-black/10 transition-colors"
                        >
                          <X className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleSaveEdit(msg.id)}
                          disabled={isEditing}
                          className="px-2.5 py-1 text-xs font-semibold bg-white text-brand-primary rounded shadow-sm hover:bg-gray-100 transition-colors"
                        >
                          <Check className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <p
                        className={`whitespace-pre-wrap break-words leading-relaxed ${
                          isDeleted ? "italic opacity-70" : ""
                        }`}
                      >
                        {msg.content}
                      </p>

                      <div
                        className={`flex items-center justify-end gap-1.5 mt-1 text-[10px] ${
                          isMine
                            ? "text-teal-100/90"
                            : "text-gray-500 dark:text-gray-400"
                        }`}
                      >
                        {msg.edited_at && !isDeleted && (
                          <span className="italic">(edited)</span>
                        )}
                        <span>
                          {new Date(msg.created_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      </div>
                    </>
                  )}

                  {/* Actions for sender: Edit & Delete */}
                  {isMine && !isDeleted && !isEditingThis && (
                    <div className="hidden group-hover:flex items-center gap-1 absolute -top-3 right-0 bg-white dark:bg-brand-dark-card border border-gray-200 dark:border-brand-dark-border rounded-lg shadow-sm px-1 py-0.5 text-gray-600 dark:text-gray-300">
                      <button
                        onClick={() => handleStartEdit(msg)}
                        title="Edit message"
                        className="p-1 hover:text-brand-primary transition-colors"
                      >
                        <Edit2 className="w-3 h-3" />
                      </button>
                      <button
                        onClick={() => handleDelete(msg.id)}
                        title="Delete message"
                        className="p-1 hover:text-brand-danger transition-colors"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Send Error Toast */}
      {sendError && (
        <div className="px-4 py-2 bg-red-50 dark:bg-red-950/30 text-red-600 text-xs border-t border-red-100 flex items-center justify-between">
          <span>{sendError}</span>
          <button onClick={() => setSendError(null)}>
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Composer */}
      <form
        onSubmit={handleSendMessage}
        className="p-3 border-t border-gray-200 dark:border-brand-dark-border bg-gray-50/50 dark:bg-brand-dark-muted/20 flex items-center gap-2"
      >
        <textarea
          value={inputContent}
          onChange={(e) => setInputContent(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message... (Press Enter to send)"
          rows={1}
          maxLength={2000}
          className="flex-1 resize-none px-3.5 py-2.5 rounded-xl border border-gray-300 dark:border-brand-dark-border bg-white dark:bg-brand-dark-card text-gray-900 dark:text-gray-100 text-sm focus:outline-none focus:ring-2 focus:ring-brand-primary"
        />
        <Button
          type="submit"
          variant="primary"
          size="sm"
          disabled={!inputContent.trim() || isSending}
          isLoading={isSending}
          className="min-h-[44px] min-w-[44px] px-3.5 rounded-xl flex items-center justify-center shrink-0"
        >
          <Send className="w-4 h-4" />
        </Button>
      </form>
    </div>
  );
}
