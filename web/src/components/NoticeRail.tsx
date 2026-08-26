"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Dateline from "@/components/Dateline";
import { fetchNotices, type Notice } from "@/lib/api";

// How many the rail holds. About five fit in the gutter before it reads as a second
// column, so the rest are reachable by scrolling rather than by being fetched and
// thrown away -- which is what this did when it sliced to five at fetch time, with
// seven sources publishing twelve notices each behind it.
const HELD = 15;

// Roughly five rows. Set in rem against the row height rather than as a row count,
// because a two-line Nepali headline makes rows uneven and a fixed count of them
// would make the rail's height jump around with the news.
const RAIL_HEIGHT = "26rem";

/**
 * The notice index, as a newspaper prints one: no cards, no radius, no per-item
 * background, no search. Just a dateline, a headline, and a source, separated by the
 * same hairline used everywhere else. Searching and filtering live on /notices, which
 * is where somebody actually hunting for a notice goes.
 */
export default function NoticeRail() {
  const [notices, setNotices] = useState<Notice[] | null>(null);

  useEffect(() => {
    let live = true;
    fetchNotices(HELD)
      .then((feed) => live && setNotices(feed.notices))
      .catch(() => live && setNotices([]));
    return () => {
      live = false;
    };
  }, []);

  return (
    <aside aria-label="Latest notices" className="text-[0.8125rem]">
      <div className="border-lapis flex items-baseline gap-3 border-b pb-2">
        <h2 className="eyebrow">Latest notices</h2>
        <Link
          href="/notices"
          className="text-mute hover:text-lapis ml-auto text-[0.6875rem] transition"
        >
          All →
        </Link>
      </div>

      {notices === null ? (
        <p className="text-faint py-4 text-[0.75rem]">Loading…</p>
      ) : notices.length === 0 ? (
        <p className="text-faint py-4 text-[0.75rem] leading-relaxed">
          No notices collected yet. An administrator refreshes these from the
          IOE boards and the campus admission portals.
        </p>
      ) : (
        // pane carries the thin lapis scrollbar, overscroll-behavior: contain so the
        // page does not scroll on once the rail bottoms out, and a stable gutter so
        // nothing shifts when the bar appears.
        <ul className="pane overflow-y-auto" style={{ maxHeight: RAIL_HEIGHT }}>
          {notices.map((notice, i) => (
            <li key={notice.url} className="border-rule border-b">
              <a
                href={notice.url}
                target="_blank"
                rel="noreferrer noopener"
                className="rise group block py-3.5"
                style={{ animationDelay: `${i * 35}ms` }}
              >
                <Dateline bs={notice.bs_date} ad={notice.date} />
                <h3 className="font-display group-hover:decoration-lapis mt-2 text-[0.9375rem] leading-snug font-medium underline decoration-transparent underline-offset-2 transition">
                  {notice.title}
                </h3>
                <p className="text-faint mt-1 text-[0.6875rem]">
                  {notice.source_label}
                </p>
              </a>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
