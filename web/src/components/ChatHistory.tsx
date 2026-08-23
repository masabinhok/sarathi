"use client";

import type { Thread } from "@/lib/api";

/** Recency at a glance, in the same fixed-width figures as every other number here. */
function ago(iso: string): string {
  const then = new Date(
    iso.endsWith("Z") || iso.includes("+") ? iso : `${iso}Z`,
  );
  const minutes = Math.round((Date.now() - then.getTime()) / 60000);
  if (!Number.isFinite(minutes) || minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.round(hours / 24);
  if (days < 7) return `${days}d ago`;
  return then.toISOString().slice(0, 10);
}

type Props = {
  threads: Thread[] | null;
  activeId: string | null;
  /** True while an answer is streaming, when switching away would abandon it. */
  busy: boolean;
  onOpen: (threadId: string) => void;
  onNew: () => void;
  onDelete: (threadId: string) => void;
  /** Suppress the column heading where something outside already provides one. */
  bare?: boolean;
};

/**
 * Past conversations, as an index rather than a menu: a title, when it was last
 * touched, and how many turns are in it.
 *
 * Titles are written by the model from the opening question, so this column reads as a
 * list of subjects — "eSewa payment process" — rather than a list of sentences the
 * student would have to re-read to tell apart. The conversation that is open is marked
 * in lapis -- a rule down its left and a wash behind it -- never in crimson: crimson
 * means a date with a consequence, and an open conversation is not one.
 */
export default function ChatHistory({
  threads,
  activeId,
  busy,
  onOpen,
  onNew,
  onDelete,
  bare = false,
}: Props) {
  return (
    <nav aria-label="Your conversations" className="flex min-h-0 flex-col">
      {/* Everything in this column is indented past the marker rule, header included,
          so the active row is announced by a change of colour rather than by a shift
          of the text beside it. */}
      {!bare && (
        <div className="border-lapis flex items-baseline gap-3 border-b pb-2 pl-3">
          <h2 className="eyebrow">Conversations</h2>
          <button
            onClick={onNew}
            className="text-mute hover:text-lapis ml-auto text-[0.6875rem] transition"
          >
            + New
          </button>
        </div>
      )}

      {threads === null ? (
        <p className="text-faint py-4 text-[0.75rem]">Loading…</p>
      ) : threads.length === 0 ? (
        <p className="text-faint py-4 text-[0.75rem] leading-relaxed">
          Conversations you start are kept here, so you can come back to an
          answer instead of asking for it twice.
        </p>
      ) : (
        <ul>
          {threads.map((thread) => {
            const active = thread.thread_id === activeId;
            return (
              <li
                key={thread.thread_id}
                className={`border-rule group relative border-b border-l-2 pl-3 ${
                  active
                    ? "border-l-lapis bg-lapis-soft"
                    : "border-l-transparent"
                }`}
              >
                <button
                  onClick={() => onOpen(thread.thread_id)}
                  disabled={busy && !active}
                  aria-current={active ? "true" : undefined}
                  className="block w-full py-3 pr-6 text-left disabled:opacity-40"
                >
                  <span
                    className={`font-display block text-[0.875rem] leading-snug font-medium ${
                      active ? "text-lapis" : "text-mute group-hover:text-ink"
                    } transition`}
                  >
                    {thread.title}
                  </span>
                  <span className="text-faint mt-1 block font-mono text-[0.6875rem] tabular-nums">
                    {ago(thread.updated_at)} · {thread.turns}{" "}
                    {thread.turns === 1 ? "question" : "questions"}
                  </span>
                </button>
                {/* Only reachable on hover or by keyboard, so a column being scanned
                    is not also a column of delete buttons. Neither crimson nor lapis
                    on hover: crimson means a date with a consequence, lapis means the
                    conversation you are in, and deleting one is neither. */}
                <button
                  onClick={() => onDelete(thread.thread_id)}
                  aria-label={`Delete conversation: ${thread.title}`}
                  className="text-faint hover:text-ink absolute top-2.5 right-0 opacity-0 transition group-hover:opacity-100 focus-visible:opacity-100"
                >
                  <svg viewBox="0 0 24 24" className="size-3.5" aria-hidden>
                    <path
                      d="M6 6l12 12M18 6L6 18"
                      stroke="currentColor"
                      strokeWidth="2"
                      strokeLinecap="round"
                    />
                  </svg>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </nav>
  );
}
