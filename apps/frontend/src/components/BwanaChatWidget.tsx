"use client";

import { useState } from "react";
import { MessageCircle, Send, X } from "lucide-react";

import { cn } from "@/lib/utils";

const DEMO_USER_PROMPT = "How to write a cover letter";

const DEMO_AI_COVER_LETTER_REPLY =
  "Cover letters generate per match on Starter. They're 200-250 words, tailored to the role... You can edit before downloading as PDF.";

interface BwanaChatWidgetProps {
  /** Shown in the greeting bubble, e.g. first name from profile */
  userName?: string;
}

export function BwanaChatWidget({ userName = "there" }: BwanaChatWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [draft, setDraft] = useState("");

  const greeting = `Hey ${userName} — I'm Bwana, your ZedApply assistant. Ask me about matches, billing, or careers.`;

  const toggleOpen = () => setIsOpen((prev) => !prev);

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
            <MessageBubble variant="ai">{greeting}</MessageBubble>
            <MessageBubble variant="user">{DEMO_USER_PROMPT}</MessageBubble>
            <MessageBubble variant="ai">{DEMO_AI_COVER_LETTER_REPLY}</MessageBubble>
          </div>

          <form
            className="flex items-center gap-2 border-t border-white/10 px-3 py-3"
            onSubmit={(e) => {
              e.preventDefault();
              setDraft("");
            }}
          >
            <input
              type="text"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Ask Bwana anything..."
              className="min-h-[40px] flex-1 rounded-lg border border-white/10 bg-[#1e1e1e] px-3 text-sm text-white placeholder:text-white/40 outline-none focus-visible:border-[#0E5C3A] focus-visible:ring-1 focus-visible:ring-[#0E5C3A]"
              aria-label="Message to Bwana"
            />
            <button
              type="submit"
              className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-[#0E5C3A] text-white transition-colors hover:bg-[#0b4a2f] disabled:opacity-50"
              aria-label="Send message"
              disabled={!draft.trim()}
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
            : "bg-[#0E5C3A] text-white hover:bg-[#0b4a2f]"
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
            : "rounded-bl-md bg-[#2a2a2a] text-white/90"
        )}
      >
        {children}
      </p>
    </div>
  );
}
