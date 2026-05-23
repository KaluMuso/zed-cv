"use client";

import { useCallback, useEffect, useState } from "react";
import { MessageCircle, Send, X } from "lucide-react";

import { ApiError, bwana } from "@/lib/api";
import {
  getOrCreateBwanaSessionId,
  useChatStore,
  type BwanaMessageSource,
} from "@/lib/useChatStore";
import { cn } from "@/lib/utils";

const SUGGESTED_PROMPTS = [
  "How do I apply?",
  "Pricing?",
  "Where's my CV?",
  "Talk to human",
] as const;

const INTRO_MESSAGE =
  "Hey — I'm Bwana, your ZedApply assistant. Ask about matches, billing, or careers. Pick a prompt below or type your question.";

interface BwanaChatWidgetProps {
  userName?: string;
}

function sourceBadgeLabel(source: BwanaMessageSource): string {
  switch (source) {
    case "faq":
      return "FAQ";
    case "escalated":
      return "Escalated to human";
    default:
      return "AI";
  }
}

export function BwanaChatWidget({ userName }: BwanaChatWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const {
    messages,
    sessionId,
    isSending,
    error,
    ensureSession,
    addUserMessage,
    addAssistantMessage,
    setSending,
    setError,
  } = useChatStore();

  useEffect(() => {
    if (isOpen) {
      ensureSession();
    }
  }, [isOpen, ensureSession]);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isSending) return;

      const sid = sessionId || getOrCreateBwanaSessionId();
      ensureSession();
      setError(null);
      addUserMessage(trimmed);
      setDraft("");
      setSending(true);

      try {
        const result = await bwana.chat(trimmed, sid);
        if (result.session_id && typeof window !== "undefined") {
          localStorage.setItem("zedapply_bwana_session_id", result.session_id);
        }
        addAssistantMessage(result.response, result.source);
      } catch (err) {
        const detail =
          err instanceof ApiError
            ? err.detail
            : "Bwana is unavailable right now. Try again shortly.";
        setError(detail);
      } finally {
        setSending(false);
      }
    },
    [
      isSending,
      sessionId,
      ensureSession,
      addUserMessage,
      addAssistantMessage,
      setSending,
      setError,
    ],
  );

  const toggleOpen = () => setIsOpen((prev) => !prev);

  const greeting =
    userName && userName !== "there"
      ? `Hey ${userName} — I'm Bwana, your ZedApply assistant.`
      : INTRO_MESSAGE;

  const showIntro = messages.length === 0;

  return (
    <div
      className="fixed right-4 z-50 flex flex-col items-end gap-3 md:right-6"
      style={{ bottom: "calc(var(--mobile-tabbar-offset, 0px) + 1rem)" }}
    >
      {isOpen ? (
        <div
          role="dialog"
          aria-label="Bwana career assistant chat"
          className="flex w-[min(100vw-2rem,22rem)] flex-col overflow-hidden rounded-xl border border-white/10 bg-[#121212] shadow-2xl sm:w-[22rem]"
        >
          <header className="flex items-center gap-2 border-b border-white/10 px-4 py-3">
            <span
              className="size-2 shrink-0 rounded-full bg-[#22c55e]"
              aria-hidden
            />
            <h2 className="text-sm font-medium text-white">
              Bwana - Career assistant online
            </h2>
            <button
              type="button"
              onClick={toggleOpen}
              className="ml-auto rounded-md p-1 text-white/60 transition-colors hover:bg-white/10 hover:text-white"
              aria-label="Close chat"
            >
              <X className="size-4" strokeWidth={2} />
            </button>
          </header>

          <div className="flex max-h-[min(50vh,20rem)] flex-col gap-3 overflow-y-auto scroll-thin px-4 py-4">
            {showIntro ? (
              <>
                <MessageBubble variant="ai">{greeting}</MessageBubble>
                <div className="flex flex-wrap gap-2">
                  {SUGGESTED_PROMPTS.map((label) => (
                    <button
                      key={label}
                      type="button"
                      disabled={isSending}
                      onClick={() => void sendMessage(label)}
                      className="rounded-full border border-white/15 bg-[#1e1e1e] px-3 py-1.5 text-xs text-white/80 transition-colors hover:border-[#0E5C3A]/50 hover:text-white disabled:opacity-50"
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </>
            ) : null}
            {messages.map((msg) => (
              <div key={msg.id} className="flex flex-col gap-1">
                <MessageBubble variant={msg.role === "user" ? "user" : "ai"}>
                  {msg.content}
                </MessageBubble>
                {msg.role === "assistant" && msg.source ? (
                  <span className="px-1 text-[10px] uppercase tracking-wide text-white/40">
                    {sourceBadgeLabel(msg.source)}
                  </span>
                ) : null}
              </div>
            ))}
            {isSending ? (
              <p className="text-xs text-white/50">Bwana is typing…</p>
            ) : null}
            {error ? (
              <p className="text-xs text-red-400" role="alert">
                {error}
              </p>
            ) : null}
          </div>

          <form
            className="flex items-center gap-2 border-t border-white/10 px-3 py-3"
            onSubmit={(e) => {
              e.preventDefault();
              void sendMessage(draft);
            }}
          >
            <input
              type="text"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Ask Bwana anything..."
              className="min-h-[40px] flex-1 rounded-lg border border-white/10 bg-[#1e1e1e] px-3 text-sm text-white placeholder:text-white/40 outline-none focus-visible:border-[#0E5C3A] focus-visible:ring-1 focus-visible:ring-[#0E5C3A]"
              aria-label="Message to Bwana"
              disabled={isSending}
            />
            <button
              type="submit"
              className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-[#0E5C3A] text-white transition-colors hover:bg-[#0b4a2f] disabled:opacity-50"
              aria-label="Send message"
              disabled={!draft.trim() || isSending}
            >
              <Send className="size-4" strokeWidth={2} />
            </button>
          </form>
        </div>
      ) : null}

      <button
        type="button"
        onClick={toggleOpen}
        className={cn(
          "flex size-14 items-center justify-center rounded-full shadow-lg transition-transform hover:scale-105 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0E5C3A]",
          isOpen
            ? "bg-[#2a2a2a] text-white"
            : "bg-[#0E5C3A] text-white hover:bg-[#0b4a2f]",
        )}
        aria-label={isOpen ? "Close Bwana chat" : "Open Bwana chat"}
        aria-expanded={isOpen}
      >
        {isOpen ? (
          <X className="size-6" strokeWidth={2} />
        ) : (
          <MessageCircle className="size-6" strokeWidth={2} />
        )}
      </button>
    </div>
  );
}

function MessageBubble({
  variant,
  children,
}: {
  variant: "ai" | "user";
  children: string;
}) {
  const isUser = variant === "user";

  return (
    <div className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <p
        className={cn(
          "max-w-[90%] rounded-2xl px-3.5 py-2.5 text-sm leading-relaxed",
          isUser
            ? "rounded-br-md bg-[#0E5C3A] text-white"
            : "rounded-bl-md bg-[#2a2a2a] text-white/90",
        )}
      >
        {children}
      </p>
    </div>
  );
}
