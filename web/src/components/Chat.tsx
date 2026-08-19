"use client";

import { useEffect, useRef, useState } from "react";
import { fetchHistory, sendMessage, type Message } from "@/lib/api";

const THREAD_KEY = "ioe.thread_id";

// Phrased the way a student would actually ask, and each one exercises a different path:
// retrieval, the pass list, the date logic, the payment guides.
const PROMPTS = [
  "What subjects are on the BE entrance exam?",
  "Did form 2083-4001 pass?",
  "Has the quota document deadline passed?",
  "How do I pay the entrance fee with eSewa?",
];

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const threadId = useRef<string | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  // Restore the previous conversation so a refresh doesn't lose the thread.
  useEffect(() => {
    const saved = localStorage.getItem(THREAD_KEY);
    if (!saved) return;
    threadId.current = saved;
    fetchHistory(saved)
      .then(setMessages)
      .catch(() => {});
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

  function reset() {
    localStorage.removeItem(THREAD_KEY);
    threadId.current = null;
    setMessages([]);
    setError(null);
  }

  const empty = messages.length === 0;

  return (
    <section
      aria-labelledby="ask-heading"
      className="border-line bg-paper-raised rounded-sm border shadow-[0_1px_0_rgba(15,36,56,0.04)]"
    >
      <div className="border-line flex items-baseline justify-between border-b px-5 py-3">
        <h2 id="ask-heading" className="font-serif text-lg font-semibold">
          Ask about admission
        </h2>
        {!empty && (
          <button
            onClick={reset}
            className="text-ink-faint hover:text-ink text-xs underline underline-offset-2 transition"
          >
            Start over
          </button>
        )}
      </div>

      <div className="max-h-[26rem] min-h-[15rem] overflow-y-auto px-5 py-5">
        {empty ? (
          <div className="py-2">
            <p className="text-ink-soft max-w-xl text-[15px] leading-relaxed">
              Answers come from the official IOE notices for 2083 — the syllabus, the
              admission booklet, quota and payment notices, and the published pass list.
              When the notices don&apos;t cover something, this says so instead of guessing.
            </p>
            <p className="eyebrow mt-6 mb-2">Try asking</p>
            <div className="flex flex-wrap gap-2">
              {PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  onClick={() => ask(prompt)}
                  className="border-line text-ink-soft hover:border-line-strong hover:text-ink rounded-full border px-3 py-1.5 text-[13px] transition"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-5">
            {messages.map((message, i) => (
              <div key={i}>
                <p className="eyebrow mb-1.5">
                  {message.role === "user" ? "You asked" : "Assistant"}
                </p>
                <div
                  className={
                    message.role === "user"
                      ? "border-line-strong border-l-2 pl-3 text-[15px] leading-relaxed whitespace-pre-wrap"
                      : "text-ink-soft text-[15px] leading-relaxed whitespace-pre-wrap"
                  }
                >
                  {message.content ||
                    (streaming && i === messages.length - 1 ? (
                      <span className="text-ink-faint inline-block animate-pulse">
                        reading the notices…
                      </span>
                    ) : null)}
                </div>
              </div>
            ))}
            <div ref={bottom} />
          </div>
        )}

        {error && (
          <p className="border-crimson/30 text-crimson mt-4 rounded-sm border-l-2 bg-transparent py-1 pl-3 text-[13px]">
            {error}
          </p>
        )}
      </div>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          void ask(input.trim());
        }}
        className="border-line border-t px-5 py-4"
      >
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="e.g. What documents do I need for a quota application?"
            aria-label="Your question"
            className="border-line focus:border-sky placeholder:text-ink-faint flex-1 rounded-sm border bg-transparent px-3 py-2.5 text-[15px] outline-none transition"
          />
          <button
            type="submit"
            disabled={streaming || !input.trim()}
            className="bg-ink text-paper rounded-sm px-5 py-2.5 text-sm font-medium transition disabled:opacity-30"
          >
            {streaming ? "…" : "Ask"}
          </button>
        </div>
      </form>
    </section>
  );
}
