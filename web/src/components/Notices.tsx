"use client";

import { useEffect, useMemo, useState } from "react";
import DateStamp from "@/components/DateStamp";
import Skeleton from "@/components/Skeleton";
import { fetchNotices, type NoticeFeed } from "@/lib/api";

const SOURCE_ORDER = ["entrance", "ioe", "tu", "pcampus"];
const FRESH_DAYS = 7;

function daysSince(iso: string) {
  if (!iso) return Infinity;
  const then = Date.parse(iso);
  if (Number.isNaN(then)) return Infinity;
  return Math.floor((Date.now() - then) / 86_400_000);
}

export default function Notices() {
  const [feed, setFeed] = useState<NoticeFeed | null>(null);
  const [failed, setFailed] = useState(false);
  const [source, setSource] = useState("all");
  const [query, setQuery] = useState("");

  useEffect(() => {
    let live = true;
    fetchNotices()
      .then((value) => live && setFeed(value))
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, []);

  const loading = feed === null && !failed;
  const notices = useMemo(() => feed?.notices ?? [], [feed]);
  const sources = SOURCE_ORDER.filter((key) =>
    notices.some((n) => n.source === key),
  );

  const shown = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return notices.filter(
      (notice) =>
        (source === "all" || notice.source === source) &&
        (!needle || notice.title.toLowerCase().includes(needle)),
    );
  }, [notices, source, query]);

  return (
    <div className="flex flex-col gap-3">
      <div className="relative">
        <svg
          viewBox="0 0 24 24"
          className="text-faint pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2"
          fill="none"
          aria-hidden
        >
          <circle
            cx="11"
            cy="11"
            r="6.5"
            stroke="currentColor"
            strokeWidth="1.7"
          />
          <path
            d="m16 16 4 4"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinecap="round"
          />
        </svg>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search notices"
          aria-label="Search notices"
          className="border-line bg-card focus:border-blue placeholder:text-faint w-full rounded-xl border py-2 pr-3 pl-9 text-[13.5px] outline-none transition"
        />
      </div>

      {!loading && sources.length > 1 && (
        <div className="no-scrollbar flex gap-1.5 overflow-x-auto pb-0.5">
          {["all", ...sources].map((key) => {
            const label =
              key === "all" ? "All" : (feed?.sources[key]?.label ?? key);
            const active = source === key;
            return (
              <button
                key={key}
                onClick={() => setSource(key)}
                className={`shrink-0 rounded-full border px-2.5 py-1 text-xs font-medium whitespace-nowrap transition ${
                  active
                    ? "border-blue bg-blue text-white"
                    : "border-line text-mute hover:border-line-strong hover:text-ink"
                }`}
              >
                {label}
              </button>
            );
          })}
        </div>
      )}

      {failed && (
        <p className="border-line text-mute rounded-xl border border-dashed p-4 text-sm">
          The notice cache could not be read. Start the backend, then run{" "}
          <code className="font-mono text-xs">uv run ioe-notices</code>.
        </p>
      )}

      {loading && <Skeleton />}

      {!failed && !loading && notices.length === 0 && (
        <p className="border-line text-mute rounded-xl border border-dashed p-4 text-sm">
          No notices collected yet. Run{" "}
          <code className="font-mono text-xs">uv run ioe-notices</code> to fetch
          them.
        </p>
      )}

      {!failed && notices.length > 0 && shown.length === 0 && (
        <p className="border-line text-mute rounded-xl border border-dashed p-4 text-sm">
          Nothing matches “{query}”. Try a shorter word, or clear the source
          filter.
        </p>
      )}

      <ul className="flex flex-col gap-2">
        {shown.map((notice, i) => {
          const fresh = daysSince(notice.date) <= FRESH_DAYS;
          return (
            <li
              key={notice.url}
              className="rise"
              style={{ animationDelay: `${Math.min(i, 14) * 20}ms` }}
            >
              <a
                href={notice.url}
                target="_blank"
                rel="noreferrer"
                className="border-line bg-card hover:border-blue/50 group flex gap-3.5 rounded-xl border p-3 transition hover:shadow-[0_2px_10px_rgba(15,23,42,0.06)]"
              >
                <DateStamp bs={notice.bs_date} ad={notice.date} />
                <div className="min-w-0 flex-1">
                  <div className="mb-1.5 flex items-center gap-1.5">
                    <span className="tag bg-line/70 text-mute">
                      {notice.source_label}
                    </span>
                    {/* Recency is a dot, not a second label: the feed is already sorted
                        newest first, so the source tag is the only word worth reading. */}
                    {fresh && (
                      <span
                        role="img"
                        aria-label={`Published in the last ${FRESH_DAYS} days`}
                        title={`Published in the last ${FRESH_DAYS} days`}
                        className="bg-emerald size-1.5 rounded-full"
                      />
                    )}
                  </div>
                  <p className="group-hover:text-blue text-[13.5px] leading-snug transition">
                    {notice.title}
                  </p>
                </div>
                <svg
                  viewBox="0 0 24 24"
                  className="text-faint group-hover:text-blue mt-0.5 size-3.5 shrink-0 opacity-0 transition group-hover:opacity-100"
                  fill="none"
                  aria-hidden
                >
                  <path
                    d="M7 17 17 7m0 0H8m9 0v9"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </a>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
