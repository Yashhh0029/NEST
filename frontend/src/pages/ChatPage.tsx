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
  translateChatMessage,
  getConversationPresence,
} from "@/services/chat";
import { getConnectionById } from "@/services/connections";
import { useToast } from "@/hooks/useToast";
import { useChatSocket } from "@/hooks/useChatSocket";
import { refreshCoordinator } from "@/services/refreshCoordinator";
import type {
  ConversationItem,
  MessageItem,
  ConversationPresenceResponse,
} from "@/types/chat";
import { LanguageDropdown } from "@/components/chat/LanguageDropdown";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { BlockConfirmModal } from "@/components/safety/BlockConfirmModal";
import { ReportModal } from "@/components/safety/ReportModal";
import { ReactivateConfirmModal } from "@/components/common/ReactivateConfirmModal";
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
  ShieldAlert,
  Flag,
  Languages,
  RotateCcw,
} from "lucide-react";

const LANGUAGE_LABELS: Record<string, string> = {
  en: "English",
  hi: "Hindi",
  ml: "Malayalam",
  mr: "Marathi",
  ta: "Tamil",
  te: "Telugu",
  kn: "Kannada",
  bn: "Bengali",
  gu: "Gujarati",
  pa: "Punjabi",
  ur: "Urdu",
};

interface MessageTranslation {
  translatedText: string;
  sourceLang: string;
  targetLang: string;
  loading: boolean;
  showOriginal: boolean;
  error?: string | null;
}

function formatLastSeen(lastSeenAt?: string | null): string {
  if (!lastSeenAt) return "Offline";
  try {
    const date = new Date(lastSeenAt);
    if (isNaN(date.getTime())) return "Offline";
    const now = Date.now();
    const diffSec = Math.max(0, Math.floor((now - date.getTime()) / 1000));
    if (diffSec < 60) return "Active just now";
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `Last seen ${diffMin}m ago`;
    const diffHour = Math.floor(diffMin / 60);
    if (diffHour < 24) return `Last seen ${diffHour}h ago`;
    const diffDay = Math.floor(diffHour / 24);
    if (diffDay < 7) return `Last seen ${diffDay}d ago`;
    return `Last seen ${date.toLocaleDateString()}`;
  } catch {
    return "Offline";
  }
}

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

  const [showBlockModal, setShowBlockModal] = useState<boolean>(false);
  const [showReportModal, setShowReportModal] = useState<boolean>(false);
  const [showReactivateModal, setShowReactivateModal] = useState<boolean>(false);
  const [reportingMessageId, setReportingMessageId] = useState<string | undefined>(undefined);
  const [isPartnerBlocked, setIsPartnerBlocked] = useState<boolean>(false);
  const [connectionStatus, setConnectionStatus] = useState<string | null>(null);
  const { success: toastSuccess } = useToast();

  // Multilingual translation state
  const [targetLang, setTargetLang] = useState<string>("en");
  const [translations, setTranslations] = useState<Record<string, MessageTranslation>>({});

  // Real-time partner presence state
  const [partnerPresence, setPartnerPresence] = useState<ConversationPresenceResponse | null>(null);

  const targetLangRef = useRef<string>(targetLang);
  useEffect(() => {
    targetLangRef.current = targetLang;
  }, [targetLang]);

  const requestSeqRef = useRef<Record<string, number>>({});

  const handleToggleShowOriginal = (msgId: string) => {
    setTranslations((prev) => {
      const cur = prev[msgId];
      if (!cur) return prev;
      return {
        ...prev,
        [msgId]: {
          ...cur,
          showOriginal: !cur.showOriginal,
        },
      };
    });
  };

  const handleTranslateMessage = async (msg: MessageItem, customLang?: string) => {
    const selectedTarget = customLang || targetLangRef.current || targetLang;
    const current = translations[msg.id];

    // If already translated for this exact target language without error:
    if (
      current &&
      current.targetLang === selectedTarget &&
      current.translatedText &&
      !current.error
    ) {
      handleToggleShowOriginal(msg.id);
      return;
    }

    const seq = (requestSeqRef.current[msg.id] || 0) + 1;
    requestSeqRef.current[msg.id] = seq;

    setTranslations((prev) => ({
      ...prev,
      [msg.id]: {
        translatedText: prev[msg.id]?.translatedText || "",
        sourceLang: prev[msg.id]?.sourceLang || "auto",
        targetLang: selectedTarget,
        loading: true,
        error: null,
        showOriginal: false,
      },
    }));

    try {
      // Always translate from original text msg.content
      const result = await translateChatMessage(msg.content, selectedTarget, "auto", msg.id);
      if (requestSeqRef.current[msg.id] !== seq) return;

      setTranslations((prev) => ({
        ...prev,
        [msg.id]: {
          translatedText: result.translated_text,
          sourceLang: result.detected_source_language,
          targetLang: result.target_language,
          loading: false,
          error: null,
          showOriginal: false,
        },
      }));
    } catch (err: any) {
      if (requestSeqRef.current[msg.id] !== seq) return;
      const detail = err?.response?.data?.detail || "Translation failed. Please retry.";
      setTranslations((prev) => ({
        ...prev,
        [msg.id]: {
          translatedText: prev[msg.id]?.translatedText || "",
          sourceLang: prev[msg.id]?.sourceLang || "",
          targetLang: selectedTarget,
          loading: false,
          showOriginal: false,
          error: detail,
        },
      }));
    }
  };

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const messageContainerRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const syncLatestMessages = useCallback(async (convId: string) => {
    try {
      const msgs = await getMessages(convId);
      setMessages((prev) => {
        const existingIds = new Set(prev.map((m) => m.id));
        const newMsgs = msgs.messages.filter((m) => !existingIds.has(m.id));
        if (newMsgs.length === 0) return prev;
        setTimeout(scrollToBottom, 50);
        return [...prev, ...newMsgs];
      });
    } catch {
      // silently handle fallback error
    }
  }, []);

  const handleIncomingRealtimeMessage = useCallback((incoming: MessageItem) => {
    setMessages((prev) => {
      if (prev.some((m) => m.id === incoming.id)) {
        return prev.map((m) => (m.id === incoming.id ? incoming : m));
      }
      return [...prev, incoming];
    });
    setTimeout(scrollToBottom, 50);
  }, []);

  const loadPresence = useCallback(async (convId: string) => {
    try {
      const pres = await getConversationPresence(convId);
      setPartnerPresence(pres);
    } catch {
      // Silently keep previous or null
    }
  }, []);

  const handlePresenceReceived = useCallback(
    (presence: { user_id: string; is_online: boolean; last_seen_at?: string | null }) => {
      setPartnerPresence((prev) => {
        if (!prev) {
          return {
            conversation_id: conversation?.id || "",
            partner_id: presence.user_id,
            is_online: presence.is_online,
            last_seen_at: presence.last_seen_at || null,
          };
        }
        if (prev.partner_id === presence.user_id) {
          return {
            ...prev,
            is_online: presence.is_online,
            last_seen_at: presence.last_seen_at !== undefined ? presence.last_seen_at : prev.last_seen_at,
          };
        }
        return prev;
      });
    },
    [conversation?.id]
  );

  const { isConnected } = useChatSocket({
    conversationId: conversation?.id,
    onMessageReceived: handleIncomingRealtimeMessage,
    onPresenceReceived: handlePresenceReceived,
    onReconnect: () => {
      if (conversation?.id) {
        syncLatestMessages(conversation.id);
        loadPresence(conversation.id);
      }
    },
  });

  // Periodic partner presence sync & tab visibility listener
  useEffect(() => {
    if (!conversation?.id) return;

    const intervalTimer = setInterval(() => {
      if (refreshCoordinator.isTabVisible() && refreshCoordinator.isOnline()) {
        loadPresence(conversation.id);
      }
    }, 30000);

    const unsubscribe = refreshCoordinator.subscribe((scopes) => {
      if (scopes.includes("visibility_visible") || scopes.includes("network_online")) {
        loadPresence(conversation.id);
      }
    });

    return () => {
      clearInterval(intervalTimer);
      unsubscribe();
    };
  }, [conversation?.id, loadPresence]);

  // Background fallback polling ONLY when WebSocket is disconnected
  useEffect(() => {
    if (isConnected || !conversation?.id) return;

    let timer: ReturnType<typeof setTimeout> | null = null;
    let isCancelled = false;

    const pollFallback = async () => {
      if (refreshCoordinator.isTabVisible() && refreshCoordinator.isOnline()) {
        await syncLatestMessages(conversation.id);
      }
      if (!isCancelled && !isConnected) {
        timer = setTimeout(pollFallback, 10000); // 10s fallback polling only when disconnected
      }
    };

    timer = setTimeout(pollFallback, 10000);

    return () => {
      isCancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [isConnected, conversation?.id, syncLatestMessages]);

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
        loadPresence(conv.id);
        if (conv.connection_status) {
          setConnectionStatus(conv.connection_status);
        }

        try {
          const connData = await getConnectionById(connectionId);
          if (isMounted && connData?.status) {
            setConnectionStatus(connData.status);
          }
        } catch {
          // Fallback to conv.connection_status
        }

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
      refreshCoordinator.invalidate(["notifications", "chat"]);
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
    <div className="max-w-3xl mx-auto flex flex-col h-[calc(100dvh-9rem)] sm:h-[calc(100vh-8rem)] min-h-[380px] sm:min-h-[500px] bg-white dark:bg-brand-dark-card rounded-2xl border border-gray-200 dark:border-brand-dark-border shadow-soft overflow-hidden">
      {/* Header */}
      <div className="px-3 sm:px-4 py-2.5 sm:py-3 border-b border-gray-200 dark:border-brand-dark-border bg-gray-50/70 dark:bg-brand-dark-muted/20 flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 sm:gap-3 min-w-0">
          <Link
            to="/connections"
            className="p-1.5 rounded-lg text-gray-500 hover:text-gray-900 dark:hover:text-gray-100 hover:bg-gray-200 dark:hover:bg-brand-dark-muted transition-colors min-h-[44px] min-w-[44px] flex items-center justify-center shrink-0"
            title="Back to Connections"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>

          <div className="relative shrink-0">
            <div className="w-9 h-9 sm:w-10 sm:h-10 rounded-xl bg-teal-100 dark:bg-brand-dark-muted text-brand-primary dark:text-teal-300 flex items-center justify-center font-bold font-heading text-sm sm:text-base">
              {partner?.name?.charAt(0) || "U"}
            </div>
            {partnerPresence?.is_online && (
              <span
                className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-500 border-2 border-white dark:border-brand-dark-card rounded-full"
                title="Online"
              />
            )}
          </div>

          <div className="min-w-0">
            <div className="flex items-center gap-1.5 sm:gap-2">
              <h2 className="font-bold text-xs sm:text-base text-gray-900 dark:text-gray-100 font-heading truncate max-w-[110px] sm:max-w-[200px]">
                {partner?.name || "Community Member"}
              </h2>
              <span className="hidden sm:inline-flex">
                <Badge
                  variant={connectionStatus === "COMPLETED" ? "neutral" : "primary"}
                  size="sm"
                >
                  {connectionStatus === "COMPLETED" ? "Completed" : "Connected"}
                </Badge>
              </span>
            </div>
            <div className="flex items-center gap-1.5 text-[11px] sm:text-xs text-gray-500 dark:text-gray-400 truncate">
              {partnerPresence?.is_online ? (
                <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium shrink-0">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                  Online
                </span>
              ) : (
                <span className="flex items-center gap-1 text-gray-500 dark:text-gray-400 shrink-0">
                  <span className="w-1.5 h-1.5 rounded-full bg-gray-400 dark:bg-gray-500" />
                  {formatLastSeen(partnerPresence?.last_seen_at)}
                </span>
              )}
              {(partner?.headline || partner?.city || partner?.area) && (
                <span className="text-gray-300 dark:text-gray-600">•</span>
              )}
              {partner?.headline && (
                <span className="truncate">{partner.headline}</span>
              )}
              {partner?.headline && (partner?.city || partner?.area) && (
                <span className="text-gray-300 dark:text-gray-600">•</span>
              )}
              {(partner?.city || partner?.area) && (
                <span className="flex items-center gap-0.5 truncate shrink-0">
                  <MapPin className="w-3 h-3 text-brand-primary shrink-0" />
                  <span className="truncate">{[partner.area, partner.city].filter(Boolean).join(", ")}</span>
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Header Right Actions */}
        <div className="flex items-center gap-1 sm:gap-2 shrink-0">
          {/* Multilingual Translation Preference */}
          <LanguageDropdown value={targetLang} onChange={setTargetLang} />

          {partner && (
            <div className="flex items-center gap-0.5 sm:gap-1">
              <button
                type="button"
                onClick={() => {
                  setReportingMessageId(undefined);
                  setShowReportModal(true);
                }}
                className="p-1.5 sm:px-2 sm:py-1 rounded-lg text-gray-500 hover:text-amber-600 dark:hover:text-amber-400 hover:bg-gray-100 dark:hover:bg-brand-dark-muted transition-colors flex items-center gap-1 text-xs min-h-[36px] min-w-[36px] sm:min-h-0 sm:min-w-0 justify-center"
                title="Report user"
              >
                <Flag className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Report</span>
              </button>
              <button
                type="button"
                onClick={() => setShowBlockModal(true)}
                className="p-1.5 sm:px-2 sm:py-1 rounded-lg text-gray-500 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-gray-100 dark:hover:bg-brand-dark-muted transition-colors flex items-center gap-1 text-xs min-h-[36px] min-w-[36px] sm:min-h-0 sm:min-w-0 justify-center"
                title="Block user"
              >
                <ShieldAlert className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Block</span>
              </button>
            </div>
          )}

          {connectionStatus === "COMPLETED" && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowReactivateModal(true)}
              className="text-xs h-8 px-2 sm:px-3 text-brand-primary border-brand-primary/40 hover:bg-brand-primary/10"
              title="Reactivate this conversation to resume messaging"
            >
              <RotateCcw className="w-3.5 h-3.5 mr-1" />
              <span className="hidden sm:inline">Reactivate conversation</span>
              <span className="sm:hidden">Reactivate</span>
            </Button>
          )}

          {/* Real Human Presence Badge */}
          <div
            className="flex items-center gap-1 text-xs border-l border-gray-200 dark:border-brand-dark-border pl-1.5 sm:pl-2.5"
            title={partnerPresence?.is_online ? "Partner is currently online" : formatLastSeen(partnerPresence?.last_seen_at)}
          >
            {partnerPresence?.is_online ? (
              <span className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 font-medium text-[11px] sm:text-xs">
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                <span className="hidden sm:inline">Online</span>
              </span>
            ) : (
              <span className="flex items-center gap-1.5 text-gray-500 dark:text-gray-400 text-[11px] sm:text-xs">
                <span className="w-2 h-2 rounded-full bg-gray-400 dark:bg-gray-500" />
                <span className="hidden sm:inline">{formatLastSeen(partnerPresence?.last_seen_at)}</span>
                <span className="sm:hidden">Offline</span>
              </span>
            )}
          </div>
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
            const isDeleted = Boolean(msg.deleted_at);
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

                      {/* Multilingual Translation Details Box */}
                      {translations[msg.id] && !isDeleted && (
                        <div
                          className={`mt-2 pt-1.5 border-t text-[11px] leading-relaxed rounded-lg p-2 ${
                            isMine
                              ? "border-teal-400/40 bg-teal-800/30 text-teal-100"
                              : "border-gray-200 dark:border-brand-dark-border bg-gray-50 dark:bg-brand-dark-muted/40 text-gray-700 dark:text-gray-200"
                          }`}
                        >
                          {translations[msg.id].loading ? (
                            <div className="flex items-center gap-1.5 py-0.5">
                              <Loader2 className="w-3 h-3 animate-spin text-brand-primary" />
                              <span>
                                Translating to {LANGUAGE_LABELS[translations[msg.id].targetLang] || translations[msg.id].targetLang}...
                              </span>
                            </div>
                          ) : translations[msg.id].error ? (
                            <div className="flex items-center justify-between text-rose-500 dark:text-rose-400 text-[10px]">
                              <span>{translations[msg.id].error}</span>
                              <button
                                type="button"
                                onClick={() => handleTranslateMessage(msg)}
                                className="underline font-semibold ml-2 hover:opacity-80"
                              >
                                Retry
                              </button>
                            </div>
                          ) : (
                            <div className="space-y-1">
                              <div className="flex items-center justify-between gap-2 text-[10px]">
                                <span className="font-semibold flex items-center gap-1 text-teal-600 dark:text-teal-400">
                                  <Languages className="w-3 h-3" />
                                  Language: {LANGUAGE_LABELS[translations[msg.id].targetLang] || translations[msg.id].targetLang}
                                  {translations[msg.id].sourceLang && translations[msg.id].sourceLang !== "auto" && (
                                    <span className="opacity-75 font-normal">
                                      (detected: {LANGUAGE_LABELS[translations[msg.id].sourceLang] || translations[msg.id].sourceLang})
                                    </span>
                                  )}
                                </span>
                                <div className="flex items-center gap-2">
                                  {translations[msg.id].targetLang !== targetLang && (
                                    <button
                                      type="button"
                                      onClick={() => handleTranslateMessage(msg, targetLang)}
                                      className="underline hover:opacity-100 text-[10px] text-teal-600 dark:text-teal-300 font-medium"
                                    >
                                      Translate to {LANGUAGE_LABELS[targetLang] || targetLang}
                                    </button>
                                  )}
                                  <button
                                    type="button"
                                    onClick={() => handleToggleShowOriginal(msg.id)}
                                    className="underline cursor-pointer hover:opacity-100 text-[10px]"
                                  >
                                    {translations[msg.id].showOriginal
                                      ? "Show translation"
                                      : "Show original"}
                                  </button>
                                </div>
                              </div>
                              {translations[msg.id].showOriginal ? (
                                <p className="italic opacity-80 text-[10px]">
                                  Original: "{msg.content}"
                                </p>
                              ) : (
                                <div className="text-xs font-medium">
                                  <span className="opacity-75 font-normal">Translated: </span>
                                  {translations[msg.id].translatedText}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}

                      <div
                        className={`flex items-center justify-end gap-2 mt-1 text-[10px] ${
                          isMine
                            ? "text-teal-100/90"
                            : "text-gray-500 dark:text-gray-400"
                        }`}
                      >
                        {/* Inline translate toggle for quick access */}
                        {!isDeleted && (
                          <button
                            type="button"
                            onClick={() => handleTranslateMessage(msg)}
                            className="flex items-center gap-0.5 hover:underline opacity-75 hover:opacity-100 transition-opacity"
                            title={
                              translations[msg.id] && translations[msg.id].targetLang !== targetLang
                                ? `Translate to ${LANGUAGE_LABELS[targetLang] || targetLang}`
                                : "Translate message"
                            }
                          >
                            <Languages className="w-2.5 h-2.5" />
                            <span>
                              {translations[msg.id]
                                ? (translations[msg.id].targetLang !== targetLang
                                    ? `Translate (${targetLang.toUpperCase()})`
                                    : "Translated")
                                : "Translate"}
                            </span>
                          </button>
                        )}
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

                  {/* Actions for sender: Translate, Edit & Delete */}
                  {isMine && !isDeleted && !isEditingThis && (
                    <div className="hidden group-hover:flex items-center gap-1 absolute -top-3 right-0 bg-white dark:bg-brand-dark-card border border-gray-200 dark:border-brand-dark-border rounded-lg shadow-sm px-1 py-0.5 text-gray-600 dark:text-gray-300">
                      <button
                        onClick={() => handleTranslateMessage(msg)}
                        title="Translate message"
                        className="p-1 hover:text-brand-primary transition-colors flex items-center gap-0.5 text-[10px]"
                      >
                        <Languages className="w-3 h-3" />
                      </button>
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

                  {/* Actions for recipient: Translate & Report */}
                  {!isMine && !isDeleted && (
                    <div className="hidden group-hover:flex items-center gap-1 absolute -top-3 right-0 bg-white dark:bg-brand-dark-card border border-gray-200 dark:border-brand-dark-border rounded-lg shadow-sm px-1.5 py-0.5 text-gray-600 dark:text-gray-300">
                      <button
                        onClick={() => handleTranslateMessage(msg)}
                        title="Translate message"
                        className="p-0.5 hover:text-brand-primary transition-colors flex items-center gap-1 text-[11px]"
                      >
                        <Languages className="w-3 h-3" />
                        <span>Translate</span>
                      </button>
                      <button
                        onClick={() => {
                          setReportingMessageId(msg.id);
                          setShowReportModal(true);
                        }}
                        title="Report this message"
                        className="p-0.5 hover:text-amber-600 dark:hover:text-amber-400 transition-colors flex items-center gap-1 text-[11px]"
                      >
                        <Flag className="w-3 h-3" />
                        <span>Report</span>
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

      {/* Composer or Blocked/Completed Notice */}
      {isPartnerBlocked ? (
        <div className="p-4 border-t border-gray-200 dark:border-brand-dark-border bg-gray-50/90 dark:bg-brand-dark-muted/40 text-center text-xs text-gray-500 space-y-1">
          <p className="font-semibold text-gray-700 dark:text-gray-300">
            This user is blocked.
          </p>
          <p>
            Historical messages remain readable for your records, but no further messages can be sent or received.
          </p>
        </div>
      ) : connectionStatus === "COMPLETED" ? (
        <div className="p-4 border-t border-gray-200 dark:border-brand-dark-border bg-gray-50/90 dark:bg-brand-dark-muted/30 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs">
          <div className="space-y-0.5 text-center sm:text-left">
            <p className="font-semibold text-gray-800 dark:text-gray-200">
              This interaction has been marked as completed.
            </p>
            <p className="text-gray-500 dark:text-gray-400">
              Messaging is currently closed. You can reactivate this conversation to message each other again.
            </p>
          </div>
          <Button
            variant="primary"
            size="sm"
            onClick={() => setShowReactivateModal(true)}
            className="shrink-0 min-h-[36px]"
          >
            <RotateCcw className="w-4 h-4 mr-1.5" />
            Reactivate conversation
          </Button>
        </div>
      ) : (
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
      )}

      {/* Safety Modals */}
      {showBlockModal && partner && (
        <BlockConfirmModal
          isOpen={showBlockModal}
          targetUserId={partner.id}
          targetName={partner.name}
          onClose={() => setShowBlockModal(false)}
          onSuccess={() => setIsPartnerBlocked(true)}
        />
      )}

      {showReportModal && (
        <ReportModal
          isOpen={showReportModal}
          targetUserId={partner?.id}
          targetMessageId={reportingMessageId}
          targetName={reportingMessageId ? `Message by ${partner?.name || "user"}` : partner?.name}
          onClose={() => {
            setShowReportModal(false);
            setReportingMessageId(undefined);
          }}
        />
      )}

      {/* Reactivate Modal */}
      {showReactivateModal && connectionId && (
        <ReactivateConfirmModal
          isOpen={showReactivateModal}
          connectionId={connectionId}
          partnerName={partner?.name}
          onClose={() => setShowReactivateModal(false)}
          onSuccess={() => {
            setConnectionStatus("ACCEPTED");
            setConversation((prev) =>
              prev ? { ...prev, connection_status: "ACCEPTED" } : prev
            );
            toastSuccess("Conversation reactivated ✓");
            refreshCoordinator.invalidate(["connections", "chat", "notifications"]);
          }}
        />
      )}
    </div>
  );
}
