"use client";

import { useEffect, useRef, useState } from "react";
import Markdown from "@/components/Markdown";
import Sources from "@/components/Sources";
import {
  fetchHistory,
  sendMessage,
  type Message,
  type Source,
} from "@/lib/api";

// Phrased the way a student actually asks, and each one exercises a different path:
// retrieval, the pass list, the date logic, the payment guides.
const CHIPS = [
  "What's on the entrance syllabus?",
  "Did form 2083-4001 pass?",
  "Has the quota deadline passed?",
  "How do I pay the fee with eSewa?",
];

type Props = {
  /** A question handed over from the landing page, asked once on arrival. */
  initial?: string;
  /** The conversation to show. Null starts an unsaved one. */
  threadId: string | null;
  /** The server assigned an id to a conversation that did not have one. */
  onThread: (threadId: string) => void;
  /** A turn began, so the sidebar can move this conversation to the top. */
  onActivity: (threadId: string | null) => void;
  /** The conversation was named. Arrives twice on a first turn: question, then title. */
  onTitle: (threadId: string, title: string) => void;
  onStreaming: (streaming: boolean) => void;
  onNew: () => void;
};

export default function Chat({
  initial = "",
  threadId,
  onThread,
  onActivity,
  onTitle,
  onStreaming,
  onNew,
}: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const current = useRef<string | null>(threadId);
  // Which thread the transcript on screen belongs to. Starts undefined rather than null
  // so the first run always loads, even when there is no thread to load.
  const shown = useRef<string | null | undefined>(undefined);
  const bottom = useRef<HTMLDivElement>(null);
  // A question handed over from the landing page must be asked exactly once, even
  // though effects run twice in development.
  const handedOver = useRef(false);

  // Swap the transcript when the sidebar opens a different conversation. The guard is
  // for the id this component itself just caused: a new conversation gets its id from
  // the server mid-stream, and reloading then would wipe the answer being written.
  useEffect(() => {
    if (threadId === shown.current) return;
    shown.current = threadId;
    current.current = threadId;
    setError(null);
    setMessages([]);
    if (!threadId) return;

    let live = true;
    fetchHistory(threadId)
      .then((value) => live && setMessages(value))
      .catch(() => {});
    return () => {
      live = false;
    };
  }, [threadId]);

  useEffect(() => {
    if (initial && !handedOver.current) {
      handedOver.current = true;
      void ask(initial);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initial]);

  useEffect(() => {
    if (messages.length) bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  async function ask(text: string) {
    if (!text || streaming) return;

    setInput("");
    setError(null);
    setStreaming(true);
    onStreaming(true);
    onActivity(current.current);
    setMessages((prev) => [
      ...prev,
      { role: "user", content: text },
      { role: "assistant", content: "" },
    ]);

    const updateLast = (change: (message: Message) => Message) =>
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = change(next[next.length - 1]);
        return next;
      });

    try {
      await sendMessage(text, current.current, {
        onToken: (chunk: string) =>
          updateLast((message) => ({
            ...message,
            content: message.content + chunk,
          })),
        onSources: (sources: Source[]) =>
          updateLast((message) => ({ ...message, sources })),
        onTitle,
        onThread: (id) => {
          current.current = id;
          shown.current = id;
          onThread(id);
        },
        onError: setError,
      });
    } catch (err) {
      setError(
        err instanceof Error && err.message.includes("fetch")
          ? "Can't reach the assistant right now. It may still be starting up."
          : err instanceof Error
            ? err.message
            : "The request failed.",
      );
    } finally {
      setStreaming(false);
      onStreaming(false);
    }
  }

  const empty = messages.length === 0;

  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col">
      {/* Only a conversation in progress stretches to fill the column; an empty
          one would otherwise open with the composer stranded at the bottom. */}
      <div className={`pt-10 pb-6 ${empty ? "" : "flex-1"}`}>
        {empty ? (
          <div className="max-w-lg">
            <h1 className="font-display text-[2rem] leading-[1.15] font-medium tracking-[-0.02em]">
              Ask about the IOE entrance exam and admission.
            </h1>
            <p className="text-mute mt-4 text-[0.9375rem] leading-relaxed">
              Answers come from the official 2083 notices — the syllabus, the
              admission booklet, the quota and payment notices, and the
              published pass list. Dates are given in both calendars. When the
              notices don&apos;t cover something, this says so instead of
              guessing.
            </p>
            <ul className="mt-7 space-y-px">
              {CHIPS.map((chip) => (
                <li key={chip} className="border-rule border-b first:border-t">
                  <button
                    onClick={() => ask(chip)}
                    className="group text-mute hover:text-ink flex w-full items-center gap-3 py-3 text-left text-[0.9375rem] transition"
                  >
                    <span className="flex-1">{chip}</span>
                    <span className="text-faint group-hover:text-ink transition">
                      →
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <div className="flex flex-col gap-8">
            {messages.map((message, i) => {
              const waiting = streaming && i === messages.length - 1;
              if (message.role === "user") {
                return (
                  <div key={i}>
                    <p className="eyebrow mb-2">You asked</p>
                    <p className="font-display text-[1.25rem] leading-snug font-medium">
                      {message.content}
                    </p>
                  </div>
                );
              }
              return (
                <div key={i} className="border-rule border-t pt-5">
                  {message.content ? (
                    <Markdown text={message.content} streaming={waiting} />
                  ) : (
                    <p className="text-faint animate-pulse text-[0.9375rem]">
                      Reading the notices…
                    </p>
                  )}
                  {/* Citations arrive once the answer is complete, so they appear
                      under a finished answer rather than above a growing one. */}
                  {message.sources && message.sources.length > 0 && (
                    <Sources sources={message.sources} />
                  )}
                </div>
              );
            })}
            <div ref={bottom} />
          </div>
        )}

        {error && (
          <p className="border-crimson text-crimson mt-6 border-l-2 pl-3 text-[0.875rem]">
            {error}
          </p>
        )}
      </div>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          void ask(input.trim());
        }}
        className="bg-paper/90 sticky bottom-0 pt-3 pb-6 backdrop-blur"
      >
        <div className="border-rule-strong focus-within:border-ink bg-card flex items-center gap-2 rounded-[10px] border px-3.5 py-2.5 transition">
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="What documents do I need for a quota application?"
            aria-label="Your question"
            className="field text-ink placeholder:text-faint min-w-0 flex-1 bg-transparent text-[0.9375rem] outline-none"
          />
          <button
            type="submit"
            disabled={streaming || !input.trim()}
            aria-label="Ask"
            className="bg-ink text-paper grid size-8 shrink-0 place-items-center rounded-[7px] transition disabled:opacity-25"
          >
            {streaming ? (
              <span className="border-paper/40 border-t-paper size-3 animate-spin rounded-full border-2" />
            ) : (
              <svg
                viewBox="0 0 24 24"
                className="size-4"
                fill="none"
                aria-hidden
              >
                <path
                  d="M5 12h13m0 0-5-5m5 5-5 5"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
          </button>
        </div>
        {!empty && (
          <button
            onClick={onNew}
            type="button"
            className="text-faint hover:text-ink mt-2.5 text-[0.75rem] transition"
          >
            Start a new conversation
          </button>
        )}
      </form>
    </div>
  );
}
