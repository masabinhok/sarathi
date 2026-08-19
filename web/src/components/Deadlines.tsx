"use client";

import { useEffect, useState } from "react";
import DatePair from "@/components/DatePair";
import { fetchDeadlines, type Deadline, type DeadlineFeed } from "@/lib/api";

function offset(days: number) {
  if (days === 0) return "today";
  if (days > 0) return days === 1 ? "tomorrow" : `in ${days} days`;
  return days === -1 ? "yesterday" : `${Math.abs(days)} days ago`;
}

function Row({ item }: { item: Deadline }) {
  const passed = item.status === "passed";
  return (
    <li
      className={`border-l-2 py-3 pl-3 ${passed ? "border-crimson/40" : "border-gold"}`}
    >
      <div className="flex items-start justify-between gap-3">
        <DatePair bs={item.bs_label} ad={item.ad_date} />
        <span
          className={`shrink-0 font-mono text-[11px] tracking-wide ${
            passed ? "text-crimson" : "text-gold"
          }`}
        >
          {offset(item.days)}
        </span>
      </div>
      <p className="text-ink-soft mt-1.5 text-[13px] leading-snug">{item.snippet}</p>
      <p className="eyebrow mt-1.5">
        {item.url ? (
          <a
            href={item.url}
            target="_blank"
            rel="noreferrer"
            className="hover:text-ink underline underline-offset-2"
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
    fetchDeadlines()
      .then(setFeed)
      .catch(() => setFailed(true));
  }, []);

  const upcoming = feed?.upcoming ?? [];
  const passed = feed?.passed ?? [];

  return (
    <section aria-labelledby="deadlines-heading">
      <div className="border-line mb-4 flex items-baseline justify-between border-b pb-2">
        <h2 id="deadlines-heading" className="font-serif text-lg font-semibold">
          Admission calendar
        </h2>
        <p className="text-ink-faint text-xs">from indexed notices</p>
      </div>

      {failed && (
        <p className="border-line text-ink-soft rounded border border-dashed p-4 text-sm">
          Could not read the calendar. Check that the backend is running.
        </p>
      )}

      {!failed && (
        <>
          <p className="eyebrow mb-2">Ahead</p>
          {upcoming.length > 0 ? (
            <ul className="mb-6">
              {upcoming.map((item) => (
                <Row key={`${item.file}-${item.bs_date}`} item={item} />
              ))}
            </ul>
          ) : (
            <p className="border-line text-ink-soft mb-6 rounded border border-dashed p-3 text-[13px]">
              Nothing ahead in the indexed notices. Dates for the next stage are published
              on admission.ioe.edu.np as each phase opens.
            </p>
          )}

          {passed.length > 0 && (
            <>
              <p className="eyebrow mb-2">Behind</p>
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
