"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Chat from "@/components/Chat";
import ChatHistory from "@/components/ChatHistory";
import NoticeRail from "@/components/NoticeRail";
import { deleteThread, fetchThreads, type Thread } from "@/lib/api";
import { showThreadInUrl, takeHandoff, threadFromUrl } from "@/lib/handoff";

const THREAD_KEY = "ioe.thread_id";

/**
 * The three columns of /ask, and the one place that knows which conversation is open.
 *
 * Chat and ChatHistory are siblings that have to agree — opening a thread on the left
 * has to change the transcript in the middle, and a new conversation started in the
 * middle has to appear on the left — so the id they agree on is held here rather than
 * in either of them.
 *
 * Above xl the page itself does not scroll: the three columns each scroll on their own,
 * so reading a long answer never carries the notice rail off the top of the screen.
 * Below xl that would trap a phone in a 14rem column, so the layout collapses back to
 * one ordinary scrolling page with the history behind a toggle.
 */
export default function AskWorkspace() {
  const [threads, setThreads] = useState<Thread[] | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [streaming, setStreaming] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [pending, setPending] = useState("");
  // Held in a ref, not read again from session storage: the effect below runs twice in
  // development, and the second run would find the question already taken and lose it.
  const handed = useRef<string | undefined>(undefined);

  useEffect(() => {
    let live = true;
    if (handed.current === undefined) handed.current = takeHandoff();
    const question = handed.current;
    // A question carried over from the landing page opens its own conversation; the one
    // this browser was last in stays in the sidebar rather than being appended to.
    // Otherwise the address names the conversation, and failing that the last one read.
    const saved = question
      ? null
      : (threadFromUrl() ?? localStorage.getItem(THREAD_KEY));

    fetchThreads()
      .then((value) => {
        if (!live) return;
        setThreads(value);
        // Restored only if the server still holds it. A conversation the browser
        // remembers but the server has forgotten would otherwise open as an empty
        // transcript with no explanation for where it went.
        if (saved && value.some((thread) => thread.thread_id === saved)) {
          setActiveId(saved);
        } else if (saved) {
          localStorage.removeItem(THREAD_KEY);
          showThreadInUrl(null);
        }
        setPending(question);
      })
      .catch(() => {
        if (!live) return;
        setThreads([]);
        setPending(question);
      });

    return () => {
      live = false;
    };
  }, []);

  // The address follows the conversation, so a refresh reopens the transcript from the
  // server instead of replaying whatever the URL used to carry. Held back until the
  // listing has arrived, since until then the conversation the address names is exactly
  // what is being looked up.
  useEffect(() => {
    if (threads === null) return;
    showThreadInUrl(activeId);
  }, [activeId, threads]);

  const remember = useCallback((threadId: string | null) => {
    setActiveId(threadId);
    if (threadId) localStorage.setItem(THREAD_KEY, threadId);
    else localStorage.removeItem(THREAD_KEY);
  }, []);

  /** Fold a titled conversation into the list, newest first, without a round trip. */
  const upsert = useCallback((threadId: string, title: string) => {
    setThreads((prev) => {
      const rest = (prev ?? []).filter((t) => t.thread_id !== threadId);
      const was = (prev ?? []).find((t) => t.thread_id === threadId);
      const now = new Date().toISOString();
      return [
        {
          thread_id: threadId,
          title,
          created_at: was?.created_at ?? now,
          updated_at: now,
          turns: was?.turns ?? 1,
        },
        ...rest,
      ];
    });
  }, []);

  /** A follow-up turn: no new title, but the conversation is the most recent again. */
  const touch = useCallback((threadId: string | null) => {
    if (!threadId) return;
    setThreads((prev) => {
      const was = (prev ?? []).find((t) => t.thread_id === threadId);
      if (!was) return prev;
      return [
        { ...was, turns: was.turns + 1, updated_at: new Date().toISOString() },
        ...(prev ?? []).filter((t) => t.thread_id !== threadId),
      ];
    });
  }, []);

  const open = useCallback(
    (threadId: string) => {
      remember(threadId);
      setShowHistory(false);
    },
    [remember],
  );

  const startNew = useCallback(() => {
    remember(null);
    setShowHistory(false);
  }, [remember]);

  const forget = useCallback((threadId: string) => {
    setThreads((prev) => (prev ?? []).filter((t) => t.thread_id !== threadId));
    // The conversation being read is the one being deleted, so the transcript goes too.
    setActiveId((id) => {
      if (id !== threadId) return id;
      localStorage.removeItem(THREAD_KEY);
      return null;
    });
    void deleteThread(threadId);
  }, []);

  const history = (bare: boolean) => (
    <ChatHistory
      threads={threads}
      activeId={activeId}
      busy={streaming}
      onOpen={open}
      onNew={startNew}
      onDelete={forget}
      bare={bare}
    />
  );

  return (
    <main className="mx-auto grid w-full max-w-[86rem] min-h-0 flex-1 grid-cols-1 px-5 sm:px-8 xl:grid-cols-[14rem_minmax(0,1fr)_17rem] xl:gap-0 xl:px-8">
      {/* On a phone the history is a disclosure, not a column: it is the thing you
          want occasionally, and the conversation is the thing you came for. Its bar
          doubles as the heading, so the list below it renders bare -- one
          "Conversations" on the screen, not two. */}
      <div
        className={`border-rule py-3 xl:hidden ${showHistory ? "" : "border-b"}`}
      >
        <div className="flex items-baseline gap-2">
          <button
            onClick={() => setShowHistory((shown) => !shown)}
            aria-expanded={showHistory}
            className="eyebrow hover:text-ink flex flex-1 items-baseline gap-2 text-left transition"
          >
            Conversations
            <span className="text-faint">
              {threads?.length ? `· ${threads.length}` : ""}
            </span>
            <span className="ml-auto">{showHistory ? "Hide" : "Show"}</span>
          </button>
          {showHistory && (
            <button
              onClick={startNew}
              className="text-mute hover:text-ink pl-4 text-[0.6875rem] transition"
            >
              + New
            </button>
          )}
        </div>
        {showHistory && <div className="mt-3">{history(true)}</div>}
      </div>

      <div className="pane border-rule hidden min-h-0 pt-8 pr-6 pb-10 xl:block xl:border-r xl:overflow-y-auto">
        {history(false)}
      </div>

      <div className="pane flex min-h-0 min-w-0 flex-col xl:overflow-y-auto xl:px-9">
        <Chat
          initial={pending}
          threadId={activeId}
          onThread={remember}
          onActivity={touch}
          onTitle={upsert}
          onStreaming={setStreaming}
          onNew={startNew}
        />
      </div>

      {/* No rule down its left: the conversation is given the room to the right of it
          rather than being boxed in, and the rail reads as the far edge of the page. */}
      <div className="border-rule pane min-h-0 border-t pt-8 pb-10 xl:border-t-0 xl:pt-8 xl:pr-3 xl:pl-8 xl:overflow-y-auto">
        <NoticeRail />
      </div>
    </main>
  );
}
