"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import Dateline from "@/components/Dateline";
import { fetchNotices, type Notice } from "@/lib/api";

/** How many fit in the right gutter without turning it into a second column. */
const SHOWN = 5;

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
    fetchNotices()
      .then((feed) => live && setNotices(feed.notices.slice(0, SHOWN)))
      .catch(() => live && setNotices([]));
    return () => {
      live = false;
    };
  }, []);

  return (
    <aside aria-label="Latest notices" className="text-[0.8125rem]">
      <div className="border-ink flex items-baseline gap-3 border-b pb-2">
        <h2 className="eyebrow">Latest notices</h2>
        <Link
          href="/notices"
          className="text-mute hover:text-ink ml-auto text-[0.6875rem] transition"
        >
          All →
        </Link>
      </div>

      {notices === null ? (
        <p className="text-faint py-4 text-[0.75rem]">Loading…</p>
      ) : notices.length === 0 ? (
        <p className="text-faint py-4 text-[0.75rem] leading-relaxed">
          No notices collected yet. An administrator refreshes these from the
          IOE, TU and campus sites.
        </p>
      ) : (
        <ul>
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
                <h3 className="font-display group-hover:decoration-rule-strong mt-2 text-[0.9375rem] leading-snug font-medium underline decoration-transparent underline-offset-2 transition">
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
