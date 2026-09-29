import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "../ui/Button";
import { UnderstandingChips } from "./UnderstandingChips";
import { extractLocalPreview, type LocalPreviewItem } from "@/lib/nlp-preview";
import { requestsService } from "@/services/requests";
import { useDebounce } from "@/hooks/useDebounce";
import { useToast } from "@/hooks/useToast";
import type { ExtractedRequest } from "@/types/request";
import { Send, Sparkles } from "lucide-react";

export function RequestBox() {
  const [text, setText] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [localPreviews, setLocalPreviews] = useState<LocalPreviewItem[]>([]);
  const [backendExtracted, setBackendExtracted] = useState<ExtractedRequest | null>(null);

  const debouncedText = useDebounce(text, 400);
  const navigate = useNavigate();
  const { error: toastError, success: toastSuccess } = useToast();

  // Instant local regex preview
  useEffect(() => {
    if (text.trim().length >= 3) {
      setLocalPreviews(extractLocalPreview(text));
    } else {
      setLocalPreviews([]);
      setBackendExtracted(null);
    }
  }, [text]);

  // Debounced authoritative backend parse call
  useEffect(() => {
    let isCancelled = false;

    if (debouncedText.trim().length >= 10) {
      requestsService
        .parseRequestText(debouncedText)
        .then((res) => {
          if (!isCancelled && res.extracted) {
            setBackendExtracted(res.extracted);
          }
        })
        .catch(() => {
          // If parse fails or offline, local preview remains visible
        });
    } else {
      setBackendExtracted(null);
    }

    return () => {
      isCancelled = true;
    };
  }, [debouncedText]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanText = text.trim();
    if (!cleanText) {
      toastError("Please enter your request before finding help.");
      return;
    }

    setIsSubmitting(true);
    try {
      const created = await requestsService.createRequest({ text: cleanText });
      toastSuccess("Request created successfully! Finding community matches...");
      navigate(`/requests/${created.id}`);
    } catch (err: unknown) {
      const errorMsg =
        err && typeof err === "object" && "response" in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : "Failed to create request. Please check your connection.";
      toastError(typeof errorMsg === "string" ? errorMsg : "Request creation failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="relative rounded-card bg-white dark:bg-brand-dark-card border border-gray-200/80 dark:border-brand-dark-border p-4 md:p-6 shadow-soft focus-within:ring-2 focus-within:ring-brand-primary focus-within:border-brand-primary transition-all">
        <label
          htmlFor="natural-request-input"
          className="block text-base md:text-lg font-bold font-heading text-gray-900 dark:text-gray-100 mb-2 flex items-center gap-2"
        >
          <Sparkles className="w-5 h-5 text-amber-500" />
          What do you need help with?
        </label>

        <textarea
          id="natural-request-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="I'm moving to Whitefield for my first IT job. I need a PG under ₹10,000 and affordable vegetarian food."
          rows={4}
          className="w-full bg-transparent resize-none border-0 p-0 text-base md:text-lg text-gray-900 dark:text-gray-100 placeholder:text-gray-400 dark:placeholder:text-gray-500 focus:outline-none focus:ring-0 leading-relaxed"
        />

        {/* Understanding Chips area */}
        <div className="mt-4 pt-4 border-t border-gray-100 dark:border-brand-dark-border/50">
          <UnderstandingChips
            extracted={backendExtracted}
            previewItems={localPreviews}
            isPreview={true}
          />
        </div>

        <div className="mt-4 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Describe naturally: mention location, budget, dietary habits, or commute needs.
          </p>

          <Button
            type="submit"
            isLoading={isSubmitting}
            disabled={!text.trim()}
            size="md"
            rightIcon={<Send className="w-4 h-4" />}
            className="w-full sm:w-auto"
          >
            Find Help
          </Button>
        </div>
      </div>
    </form>
  );
}
