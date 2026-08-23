"use client";

import { useEffect, useMemo, useState } from "react";
import Dateline from "@/components/Dateline";
import Skeleton from "@/components/Skeleton";
import { fetchNotices, type NoticeFeed } from "@/lib/api";

// Fixed rather than taken from the feed so the chips read in a stable order --
// the boards first, then the campuses. A source missing from this list would be
// listed in the index but not filterable, so it must be extended alongside
// SOURCES in src/ioe/notices.py.
const SOURCE_ORDER = ["entrance", "ioe", "tu", "pcampus", "wrc", "ioepc"];

/** The full notice index: everything the sites have published, newest first.
 *  Search and source filtering live here rather than in the rail, because this is the
 *  page somebody hunting for a particular notice actually opens. */
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

  if (failed) {
    return (
      <p className="border-rule text-mute border border-dashed p-4 text-[0.875rem]">
        Could not read the notice index. The assistant may still be starting up.
      </p>
    );
  }

  return (
    <div>
      <div className="border-rule flex flex-wrap items-center gap-x-5 gap-y-3 border-b pb-3">
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search notices"
          aria-label="Search notices"
          type="search"
          className="text-ink placeholder:text-faint min-w-0 flex-1 bg-transparent text-[0.9375rem] outline-none"
        />
        {/* Always its own line, never beside the search field. Six sources already
            squeeze the field to four characters at 1440, and the list only grows.
            A flex item defaults to min-width:auto, so without min-w-0 the row would
            widen the page instead of scrolling inside itself. */}
        {sources.length > 1 && (
          <div className="no-scrollbar flex w-full min-w-0 gap-4 overflow-x-auto text-[0.75rem]">
            {["all", ...sources].map((key) => {
              const label =
                key === "all" ? "All" : (feed?.sources[key]?.label ?? key);
              const active = source === key;
              return (
                <button
                  key={key}
                  onClick={() => setSource(key)}
                  aria-pressed={active}
                  className={`shrink-0 whitespace-nowrap transition ${
                    active
                      ? "text-lapis border-lapis border-b"
                      : "text-mute hover:text-ink border-b border-transparent"
                  }`}
                >
                  {label}
                </button>
              );
            })}
          </div>
        )}
      </div>

      {!feed ? (
        <Skeleton rows={6} />
      ) : shown.length === 0 ? (
        <p className="text-mute py-10 text-[0.9375rem]">
          {notices.length === 0
            ? "No notices collected yet. An administrator refreshes these from the IOE, TU and campus sites."
            : "No notice matches that search."}
        </p>
      ) : (
        <ul>
          {shown.map((notice, i) => (
            <li key={notice.url} className="border-rule border-b">
              <a
                href={notice.url}
                target="_blank"
                rel="noreferrer noopener"
                className="rise group flex gap-5 py-5"
                style={{ animationDelay: `${Math.min(i, 12) * 25}ms` }}
              >
                <Dateline
                  bs={notice.bs_date}
                  ad={notice.date}
                  className="mt-1"
                />
                <div className="min-w-0 flex-1">
                  <h2 className="font-display group-hover:decoration-lapis text-[1.0625rem] leading-snug font-medium underline decoration-transparent underline-offset-[3px] transition">
                    {notice.title}
                  </h2>
                  <p className="text-faint mt-1.5 text-[0.75rem]">
                    {notice.source_label}
                  </p>
                </div>
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
