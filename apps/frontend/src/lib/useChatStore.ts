import { create } from "zustand";

export type BwanaMessageSource = "faq" | "llm" | "escalated";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  source?: BwanaMessageSource;
}

const SESSION_KEY = "zedapply_bwana_session_id";

function newMessageId(): string {
  return `msg-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

export function getOrCreateBwanaSessionId(): string {
  if (typeof window === "undefined") return "";
  let id = localStorage.getItem(SESSION_KEY);
  if (!id) {
    id =
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : `sess-${Date.now()}`;
    localStorage.setItem(SESSION_KEY, id);
  }
  return id;
}

interface ChatState {
  messages: ChatMessage[];
  sessionId: string;
  isSending: boolean;
  error: string | null;
  addUserMessage: (content: string) => void;
  addAssistantMessage: (content: string, source: BwanaMessageSource) => void;
  setSending: (v: boolean) => void;
  setError: (msg: string | null) => void;
  resetConversation: () => void;
  ensureSession: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  sessionId: "",
  isSending: false,
  error: null,

  ensureSession: () => {
    const id = getOrCreateBwanaSessionId();
    if (get().sessionId !== id) {
      set({ sessionId: id });
    }
  },

  addUserMessage: (content) =>
    set((s) => ({
      messages: [
        ...s.messages,
        { id: newMessageId(), role: "user", content },
      ],
    })),

  addAssistantMessage: (content, source) =>
    set((s) => ({
      messages: [
        ...s.messages,
        { id: newMessageId(), role: "assistant", content, source },
      ],
    })),

  setSending: (isSending) => set({ isSending }),
  setError: (error) => set({ error }),

  resetConversation: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem(SESSION_KEY);
    }
    set({ messages: [], sessionId: "", error: null });
  },
}));
