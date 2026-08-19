"use client";

import { useEffect, useRef, useState } from "react";
import { fetchHistory, sendMessage, type Message } from "@/lib/api";

const THREAD_KEY = "ioe.thread_id";

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
    fetchHistory(saved).then(setMessages).catch(() => {});
  }, []);

  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const text = input.trim();
    if (!text || streaming) return;

    setInput("");
    setError(null);
    setStreaming(true);
    setMessages((prev) => [...prev, { role: "user", content: text }, { role: "assistant", content: "" }]);

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
      setError(err instanceof Error ? err.message : "request failed");
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

  return (
    <div className="flex h-dvh flex-col">
      <header className="flex items-center justify-between border-b border-black/10 px-6 py-4 dark:border-white/10">
        <div>
          <h1 className="text-sm font-semibold tracking-tight">ioe</h1>
          <p className="text-xs opacity-50">qwen2.5:7b via LangGraph</p>
        </div>
        <button
          onClick={reset}
          className="rounded-md border border-black/10 px-3 py-1.5 text-xs transition hover:bg-black/5 dark:border-white/15 dark:hover:bg-white/10"
        >
          New chat
        </button>
      </header>

      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto flex w-full max-w-2xl flex-col gap-4 px-4 py-8">
          {messages.length === 0 && (
            <p className="mt-24 text-center text-sm opacity-40">Ask anything to get started.</p>
          )}

          {messages.map((message, i) => (
            <div
              key={i}
              className={message.role === "user" ? "flex justify-end" : "flex justify-start"}
            >
              <div
                className={
                  message.role === "user"
                    ? "max-w-[85%] rounded-2xl rounded-br-sm bg-black px-4 py-2.5 text-sm whitespace-pre-wrap text-white dark:bg-white dark:text-black"
                    : "max-w-[85%] rounded-2xl rounded-bl-sm bg-black/5 px-4 py-2.5 text-sm whitespace-pre-wrap dark:bg-white/10"
                }
              >
                {message.content ||
                  (streaming && i === messages.length - 1 ? (
                    <span className="inline-block animate-pulse opacity-50">…</span>
                  ) : null)}
              </div>
            </div>
          ))}

          {error && (
            <p className="rounded-md bg-red-500/10 px-3 py-2 text-xs text-red-600 dark:text-red-400">
              {error}
            </p>
          )}
          <div ref={bottom} />
        </div>
      </div>

      <form onSubmit={submit} className="border-t border-black/10 px-4 py-4 dark:border-white/10">
        <div className="mx-auto flex w-full max-w-2xl gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Message…"
            className="flex-1 rounded-lg border border-black/10 bg-transparent px-4 py-2.5 text-sm outline-none placeholder:opacity-40 focus:border-black/30 dark:border-white/15 dark:focus:border-white/40"
          />
          <button
            type="submit"
            disabled={streaming || !input.trim()}
            className="rounded-lg bg-black px-4 py-2.5 text-sm font-medium text-white transition disabled:opacity-30 dark:bg-white dark:text-black"
          >
            {streaming ? "…" : "Send"}
          </button>
        </div>
      </form>
    </div>
  );
}
