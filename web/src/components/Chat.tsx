"use client";

import { useEffect, useRef, useState } from "react";
import RichText from "@/components/RichText";
import {
  fetchHealth,
  fetchHistory,
  sendMessage,
  type Health,
  type Message,
} from "@/lib/api";

const THREAD_KEY = "ioe.thread_id";

// Phrased the way a student actually asks, and each one exercises a different path:
// retrieval, the pass list, the date logic, the payment guides.
const CHIPS = [
  "What's on the entrance syllabus?",
  "Did form 2083-4001 pass?",
  "Has the quota deadline passed?",
  "Pay the fee with eSewa",
];

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  // Distinguishes "not asked yet" from "asked and it is down", so the status line
  // never claims the assistant is offline before the first request has returned.
  const [reachable, setReachable] = useState<boolean | null>(null);
  const threadId = useRef<string | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let live = true;
    fetchHealth()
      .then((value) => {
        if (!live) return;
        setHealth(value);
        setReachable(value.status === "ok");
      })
      .catch(() => live && setReachable(false));

    // Restore the previous conversation so a refresh doesn't lose the thread.
    const saved = localStorage.getItem(THREAD_KEY);
    if (saved) {
      threadId.current = saved;
      fetchHistory(saved)
        .then((value) => live && setMessages(value))
        .catch(() => {});
    }
    return () => {
      live = false;
    };
  }, []);

  useEffect(() => {
    if (messages.length) bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  async function ask(text: string) {
    if (!text || streaming) return;

    setInput("");
    setError(null);
    setStreaming(true);
    setMessages((prev) => [
      ...prev,
      { role: "user", content: text },
      { role: "assistant", content: "" },
    ]);

    const appendToLast = (chunk: string) =>
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = {
          role: "assistant",
          content: next[next.length - 1].content + chunk,
        };
        return next;
      });

    try {
      await sendMessage(text, threadId.current, {
        onToken: appendToLast,
        onThread: (id) => {
          threadId.current = id;
          localStorage.setItem(THREAD_KEY, id);
        },
        onError: setError,
      });
    } catch (err) {
      setError(
        err instanceof Error && err.message.includes("fetch")
          ? "Can't reach the assistant. Check that the backend is running on port 8000."
          : err instanceof Error
            ? err.message
            : "The request failed.",
      );
    } finally {
      setStreaming(false);
    }
  }

  function startOver() {
    localStorage.removeItem(THREAD_KEY);
    threadId.current = null;
    setMessages([]);
    setError(null);
  }

  const empty = messages.length === 0;

  return (
    <section
      aria-label="Ask the assistant"
      className="bg-shell flex min-h-0 min-w-0 flex-col lg:h-full"
    >
      {/* Status line: what is answering, and what it is answering from. */}
      <div className="border-shell-line-soft flex items-center gap-2.5 border-b px-4 py-2.5 sm:px-5">
        <span className="relative flex size-2 shrink-0">
          {reachable === true && (
            <span className="bg-emerald absolute inline-flex size-full animate-ping rounded-full opacity-60" />
          )}
          <span
            className={`relative inline-flex size-2 rounded-full ${
              reachable === true
                ? "bg-emerald"
                : reachable === false
                  ? "bg-rose"
                  : "bg-shell-mute animate-pulse"
            }`}
          />
        </span>
        <span className="text-shell-ink text-[13px] font-medium">
          {reachable === true
            ? "Assistant online"
            : reachable === false
              ? "Assistant unreachable"
              : "Connecting…"}
        </span>
        {health && (
          <span className="text-shell-mute hidden font-mono text-[11px] sm:inline">
            {health.model} · {health.documents} documents · {health.chunks}{" "}
            passages
          </span>
        )}
        {!empty && (
          <button
            onClick={startOver}
            className="text-shell-mute hover:text-shell-ink ml-auto shrink-0 text-xs font-medium transition"
          >
            New chat
          </button>
        )}
      </div>

      {/* Quick actions stay put, so they are still one click away mid-conversation. */}
      <div className="no-scrollbar border-shell-line-soft flex gap-2 overflow-x-auto border-b px-4 py-2.5 sm:px-5">
        {CHIPS.map((chip) => (
          <button
            key={chip}
            onClick={() => ask(chip)}
            disabled={streaming}
            className="border-shell-line text-shell-mute hover:border-blue hover:text-shell-ink shrink-0 rounded-full border px-3 py-1.5 text-xs whitespace-nowrap transition disabled:opacity-40"
          >
            {chip}
          </button>
        ))}
      </div>

      <div className="scroll-thin-dark min-h-[18rem] flex-1 overflow-y-auto px-4 py-6 sm:px-5">
        {empty ? (
          <div className="flex h-full flex-col justify-center py-6">
            <h2 className="text-shell-ink max-w-md text-[22px] leading-snug font-semibold tracking-[-0.02em]">
              Ask about the IOE entrance exam and admission.
            </h2>
            <p className="text-shell-mute mt-3 max-w-md text-sm leading-relaxed">
              Answers are drawn from the official 2083 notices — the syllabus,
              the admission booklet, quota and payment notices, and the
              published pass list. When the notices don&apos;t cover something,
              this says so rather than guessing.
            </p>
          </div>
        ) : (
          <div className="flex flex-col gap-5">
            {messages.map((message, i) => {
              const waiting = streaming && i === messages.length - 1;
              if (message.role === "user") {
                return (
                  <div key={i} className="flex justify-end">
                    <div className="bg-blue max-w-[85%] rounded-xl rounded-br-sm px-3.5 py-2.5 text-[14.5px] leading-relaxed text-white">
                      {message.content}
                    </div>
                  </div>
                );
              }
              return (
                <div key={i} className="flex justify-start">
                  <div className="border-shell-line text-shell-ink max-w-[92%] rounded-xl rounded-bl-sm border bg-white/[0.045] px-4 py-3 text-[14.5px] leading-relaxed backdrop-blur-sm">
                    {message.content ? (
                      <RichText text={message.content} caret={waiting} />
                    ) : (
                      <span className="text-shell-mute animate-pulse text-sm">
                        Reading the notices…
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
            <div ref={bottom} />
          </div>
        )}

        {error && (
          <div className="border-rose/40 text-rose mt-4 rounded-xl border bg-white/[0.03] px-3.5 py-2.5 text-[13px]">
            {error}
          </div>
        )}
      </div>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          void ask(input.trim());
        }}
        className="border-shell-line-soft bg-shell/85 sticky bottom-0 border-t px-4 py-3 backdrop-blur sm:px-5"
      >
        <div className="border-shell-line focus-within:border-blue flex items-end gap-2 rounded-xl border bg-white/[0.04] px-3 py-2 transition">
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="What documents do I need for a quota application?"
            aria-label="Your question"
            className="text-shell-ink placeholder:text-shell-mute/70 min-w-0 flex-1 bg-transparent py-1 text-[14.5px] outline-none"
          />
          <button
            type="submit"
            disabled={streaming || !input.trim()}
            aria-label="Send question"
            className="bg-blue grid size-8 shrink-0 place-items-center rounded-lg text-white transition hover:brightness-110 disabled:opacity-30 disabled:hover:brightness-100"
          >
            {streaming ? (
              <span className="size-3 animate-spin rounded-full border-2 border-white/40 border-t-white" />
            ) : (
              <svg
                viewBox="0 0 24 24"
                className="size-4"
                fill="none"
                aria-hidden
              >
                <path
                  d="M12 19V5m0 0-6 6m6-6 6 6"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            )}
          </button>
        </div>
      </form>
    </section>
  );
}
