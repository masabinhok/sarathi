"use client";

import { useEffect, useState } from "react";
import DatePair from "@/components/DatePair";
import { fetchNotices, type NoticeFeed } from "@/lib/api";

const SOURCE_ORDER = ["entrance", "ioe", "tu", "pcampus"];

export default function Notices() {
  const [feed, setFeed] = useState<NoticeFeed | null>(null);
  const [failed, setFailed] = useState(false);
  const [source, setSource] = useState<string>("all");

  useEffect(() => {
    fetchNotices()
      .then(setFeed)
      .catch(() => setFailed(true));
  }, []);

  const notices = feed?.notices ?? [];
  const shown = source === "all" ? notices : notices.filter((n) => n.source === source);
  const available = SOURCE_ORDER.filter((key) => notices.some((n) => n.source === key));

  return (
    <section aria-labelledby="notices-heading">
      <div className="border-line mb-4 flex items-baseline justify-between border-b pb-2">
        <h2 id="notices-heading" className="font-serif text-lg font-semibold">
          Notice board
        </h2>
        {feed?.updated_at && (
          <p className="text-ink-faint text-xs">
            collected {new Date(feed.updated_at).toLocaleDateString()}
          </p>
        )}
      </div>

      {available.length > 1 && (
        <div className="mb-3 flex flex-wrap gap-1.5">
          {["all", ...available].map((key) => {
            const label =
              key === "all" ? "All sources" : (feed?.sources[key]?.label ?? key);
            const active = source === key;
            return (
              <button
                key={key}
                onClick={() => setSource(key)}
                className={`rounded-full border px-2.5 py-1 text-xs transition ${
                  active
                    ? "border-ink bg-ink text-paper"
                    : "border-line text-ink-soft hover:border-line-strong hover:text-ink"
                }`}
              >
                {label}
              </button>
            );
          })}
        </div>
      )}

      {failed && (
        <p className="border-line text-ink-soft rounded border border-dashed p-4 text-sm">
          The notice cache could not be read. Start the backend, then run{" "}
          <code className="font-mono text-xs">uv run ioe-notices</code>.
        </p>
      )}

      {!failed && notices.length === 0 && (
        <p className="border-line text-ink-soft rounded border border-dashed p-4 text-sm">
          No notices collected yet. Run{" "}
          <code className="font-mono text-xs">uv run ioe-notices</code> to fetch them.
        </p>
      )}

      <ul className="divide-line divide-y">
        {shown.map((notice) => (
          <li key={notice.url}>
            <a
              href={notice.url}
              target="_blank"
              rel="noreferrer"
              className="hover:bg-paper-raised group flex gap-4 py-3 transition"
            >
              <div className="w-[104px] shrink-0 pt-0.5">
                <DatePair bs={notice.bs_label} ad={notice.date} />
              </div>
              <div className="min-w-0">
                <p className="group-hover:text-sky text-[13.5px] leading-snug">
                  {notice.title}
                </p>
                <p className="eyebrow mt-1">{notice.source_label}</p>
              </div>
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
