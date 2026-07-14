import { FormEvent, useEffect, useRef, useState } from "react";
import { Sparkles } from "./icons";
import {
  INSURANCE_AI_QUICK_ACTIONS,
  INSURANCE_AI_WELCOME_MESSAGE,
  isNumericListSelection,
  processInsuranceAiListSelection,
  processInsuranceAiMessage,
  type InsuranceAiQuestionId,
  type InsuranceAiSelectableItem,
} from "../../lib/insurance/ai-assistant-queries";

type InsuranceAiAssistantPanelProps = {
  open: boolean;
  organizationId: number;
  onClose: () => void;
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

function createMessageId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function InsuranceAiAssistantPanel({
  open,
  organizationId,
  onClose,
}: InsuranceAiAssistantPanelProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [draft, setDraft] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [selectableItems, setSelectableItems] = useState<InsuranceAiSelectableItem[] | null>(null);
  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!open) return;
    setMessages([
      {
        id: createMessageId(),
        role: "assistant",
        content: INSURANCE_AI_WELCOME_MESSAGE,
      },
    ]);
    setDraft("");
    setIsLoading(false);
    setSelectableItems(null);
  }, [open, organizationId]);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  async function submitPrompt(rawPrompt: string, questionId?: InsuranceAiQuestionId) {
    const prompt = rawPrompt.trim();
    if (!prompt || isLoading) return;

    const userMessage: ChatMessage = { id: createMessageId(), role: "user", content: prompt };
    setMessages((current) => [...current, userMessage]);
    setDraft("");
    setIsLoading(true);

    try {
      if (selectableItems?.length && isNumericListSelection(prompt)) {
        const { response } = await processInsuranceAiListSelection(selectableItems, prompt);
        setMessages((current) => [
          ...current,
          { id: createMessageId(), role: "assistant", content: response },
        ]);
        return;
      }

      setSelectableItems(null);

      const { response, selectableItems: nextSelectableItems } = await processInsuranceAiMessage(
        organizationId,
        prompt,
        questionId,
      );
      if (nextSelectableItems?.length) {
        setSelectableItems(nextSelectableItems);
      }
      setMessages((current) => [
        ...current,
        { id: createMessageId(), role: "assistant", content: response },
      ]);
    } catch {
      setMessages((current) => [
        ...current,
        {
          id: createMessageId(),
          role: "assistant",
          content: "I couldn't fetch live data right now. Please try again in a moment.",
        },
      ]);
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    void submitPrompt(draft);
  }

  function handleChipClick(id: InsuranceAiQuestionId, label: string) {
    void submitPrompt(label, id);
  }

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[70] flex justify-end">
      <button
        type="button"
        aria-label="Close AI assistant"
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />

      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby="insurance-ai-assistant-title"
        className="relative flex h-full w-full max-w-lg flex-col border-l border-white/10 bg-[#070b16]/95 shadow-[0_24px_80px_-32px_rgba(88,28,135,0.45)] backdrop-blur-xl"
      >
        <div className="border-b border-white/10 bg-gradient-to-r from-[#8B5CF6]/10 via-transparent to-[#14B8A6]/10 px-4 py-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 items-center gap-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-2xl border border-[#8B5CF6]/30 bg-gradient-to-br from-[#8B5CF6]/20 to-[#14B8A6]/20 shadow-[0_0_24px_rgba(139,92,246,0.15)]">
                <Sparkles className="h-4 w-4 text-[#C4B5FD]" />
              </div>
              <div className="min-w-0">
                <h2 id="insurance-ai-assistant-title" className="truncate text-base font-semibold text-white">
                  AI Assistant
                </h2>
                <p className="flex items-center gap-1.5 text-[11px] text-slate-400">
                  <span className="inline-block h-1.5 w-1.5 rounded-full bg-[#14B8A6] shadow-[0_0_8px_#14B8A6]" />
                  Online • SIMI Intelligence
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="rounded-xl border border-white/10 bg-white/5 px-2.5 py-1.5 text-sm text-slate-300 transition hover:bg-white/10"
            >
              ✕
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-4">
          <div className="space-y-3">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {message.role === "assistant" ? (
                  <div className="mr-10 max-w-[92%] rounded-2xl rounded-tl-md border border-[#8B5CF6]/20 bg-gradient-to-br from-white/[0.06] to-[#8B5CF6]/[0.08] px-3.5 py-2.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
                    <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-slate-100">
                      {message.content}
                    </p>
                  </div>
                ) : (
                  <div className="ml-10 max-w-[92%] rounded-2xl rounded-tr-md border border-[#14B8A6]/25 bg-[#14B8A6]/10 px-3.5 py-2.5">
                    <p className="whitespace-pre-wrap text-[13px] leading-relaxed text-white">{message.content}</p>
                  </div>
                )}
              </div>
            ))}

            {isLoading ? (
              <div className="flex justify-start">
                <div className="mr-10 flex items-center gap-2 rounded-2xl rounded-tl-md border border-[#8B5CF6]/20 bg-white/[0.04] px-3.5 py-2.5">
                  <span className="inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-[#8B5CF6] border-t-transparent" />
                  <span className="text-[13px] text-slate-400">Analyzing live policy data…</span>
                </div>
              </div>
            ) : null}

            <div ref={chatEndRef} />
          </div>
        </div>

        <div className="border-t border-white/10 bg-[#060912]/90 px-4 py-3 backdrop-blur-md">
          <div className="mb-2.5 flex flex-wrap gap-1.5">
            {INSURANCE_AI_QUICK_ACTIONS.map((action) => (
              <button
                key={action.id}
                type="button"
                disabled={isLoading}
                onClick={() => handleChipClick(action.id, action.label)}
                className="rounded-full border border-[#8B5CF6]/25 bg-[#8B5CF6]/10 px-2.5 py-1 text-[11px] font-medium text-[#DDD6FE] transition hover:border-[#14B8A6]/35 hover:bg-[#14B8A6]/10 hover:text-[#99F6E4] disabled:cursor-not-allowed disabled:opacity-50"
              >
                {action.label}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="flex items-center gap-2">
            <input
              ref={inputRef}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              disabled={isLoading}
              placeholder="Ask about policies, renewals, follow-ups..."
              className="h-10 flex-1 rounded-2xl border border-white/10 bg-white/[0.04] px-3.5 text-sm text-white outline-none placeholder:text-slate-500 focus:border-[#14B8A6]/40 focus:ring-2 focus:ring-[#14B8A6]/15 disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={isLoading || !draft.trim()}
              className="inline-flex h-10 shrink-0 items-center justify-center rounded-2xl border border-[#14B8A6]/30 bg-gradient-to-r from-[#8B5CF6]/80 to-[#14B8A6]/80 px-4 text-sm font-medium text-white transition hover:from-[#8B5CF6] hover:to-[#14B8A6] disabled:cursor-not-allowed disabled:opacity-50"
            >
              Send
            </button>
          </form>
        </div>
      </aside>
    </div>
  );
}
