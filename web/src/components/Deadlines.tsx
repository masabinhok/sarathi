"use client";

import { useEffect, useState } from "react";
import Dateline from "@/components/Dateline";
import { fetchDeadlines, type Deadline, type DeadlineFeed } from "@/lib/api";

function offset(days: number) {
  if (days === 0) return "today";
  if (days > 0) return days === 1 ? "tomorrow" : `in ${days} days`;
  return days === -1 ? "yesterday" : `${Math.abs(days)} days ago`;
}

function Row({ item }: { item: Deadline }) {
  const passed = item.status === "passed";
  return (
    <li className="border-rule border-b py-4">
      <Dateline bs={item.bs_date} ad={item.ad_date} />
      {/* The one place colour is allowed: a date that has already gone. */}
      <p
        className={`mt-2 font-mono text-[0.6875rem] ${passed ? "text-crimson" : "text-mute"}`}
      >
        {offset(item.days)}
      </p>
      <p className="mt-1.5 text-[0.875rem] leading-snug">{item.snippet}</p>
      <p className="text-faint mt-1.5 text-[0.6875rem]">
        {item.url ? (
          <a
            href={item.url}
            target="_blank"
            rel="noreferrer noopener"
            className="decoration-rule-strong hover:decoration-current underline underline-offset-2"
          >
            {item.document}
          </a>
        ) : (
          item.document
        )}
      </p>
    </li>
  );
}

export default function Deadlines() {
  const [feed, setFeed] = useState<DeadlineFeed | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let live = true;
    fetchDeadlines()
      .then((value) => live && setFeed(value))
      .catch(() => live && setFailed(true));
    return () => {
      live = false;
    };
  }, []);

  if (failed) return null;

  const upcoming = feed?.upcoming ?? [];
  const passed = feed?.passed ?? [];

  return (
    <section aria-label="Key dates" className="text-[0.8125rem]">
      <h2 className="eyebrow border-ink border-b pb-2">Key dates</h2>

      {!feed ? (
        <p className="text-faint py-4 text-[0.75rem]">Loading…</p>
      ) : (
        <>
          {upcoming.length > 0 ? (
            <ul>
              {upcoming.map((item) => (
                <Row key={`${item.file}-${item.bs_date}`} item={item} />
              ))}
            </ul>
          ) : (
            <p className="text-mute py-4 text-[0.8125rem] leading-relaxed">
              Every dated obligation in the indexed notices has passed. Dates
              for the next stage are published as each phase opens.
            </p>
          )}

          {passed.length > 0 && (
            <>
              <h3 className="eyebrow border-rule mt-8 border-b pb-2">
                Already passed
              </h3>
              <ul>
                {passed.slice(0, 6).map((item) => (
                  <Row key={`${item.file}-${item.bs_date}`} item={item} />
                ))}
              </ul>
            </>
          )}
        </>
      )}
    </section>
  );
}
