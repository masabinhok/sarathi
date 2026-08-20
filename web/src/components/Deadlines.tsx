"use client";

import { useEffect, useState } from "react";
import DateStamp from "@/components/DateStamp";
import Skeleton from "@/components/Skeleton";
import { fetchDeadlines, type Deadline, type DeadlineFeed } from "@/lib/api";

function offset(days: number) {
  if (days === 0) return "today";
  if (days > 0) return days === 1 ? "tomorrow" : `in ${days} days`;
  return days === -1 ? "yesterday" : `${Math.abs(days)} days ago`;
}

function Row({ item, index }: { item: Deadline; index: number }) {
  const passed = item.status === "passed";
  return (
    <li
      className="rise"
      style={{ animationDelay: `${Math.min(index, 14) * 20}ms` }}
    >
      <div className="border-line bg-card rounded-xl border p-3">
        <div className="flex gap-3.5">
          <DateStamp bs={item.bs_date} ad={item.ad_date} />
          <div className="min-w-0 flex-1">
            <span
              className={`tag ${passed ? "bg-rose/12 text-rose" : "bg-emerald/12 text-emerald"}`}
            >
              {offset(item.days)}
            </span>
            <p className="mt-1.5 text-[13.5px] leading-snug">{item.snippet}</p>
            <p className="text-faint mt-1.5 font-mono text-[11px]">
              {item.url ? (
                <a
                  href={item.url}
                  target="_blank"
                  rel="noreferrer"
                  className="hover:text-blue underline underline-offset-2 transition"
                >
                  {item.document}
                </a>
              ) : (
                item.document
              )}
            </p>
          </div>
        </div>
      </div>
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

  if (failed) {
    return (
      <p className="border-line text-mute rounded-xl border border-dashed p-4 text-sm">
        Could not read the calendar. Check that the backend is running.
      </p>
    );
  }

  if (!feed) return <Skeleton rows={3} />;

  const upcoming = feed?.upcoming ?? [];
  const passed = feed?.passed ?? [];

  return (
    <div className="flex flex-col gap-5">
      <section>
        <h3 className="text-mute mb-2 text-xs font-semibold">Still ahead</h3>
        {upcoming.length > 0 ? (
          <ul className="flex flex-col gap-2">
            {upcoming.map((item, i) => (
              <Row key={`${item.file}-${item.bs_date}`} item={item} index={i} />
            ))}
          </ul>
        ) : (
          <p className="border-line text-mute rounded-xl border border-dashed p-3.5 text-[13px] leading-relaxed">
            Every dated obligation in the indexed notices has passed. Dates for
            the next stage go up on{" "}
            <a
              href="https://admission.ioe.edu.np"
              target="_blank"
              rel="noreferrer"
              className="text-blue underline underline-offset-2"
            >
              admission.ioe.edu.np
            </a>{" "}
            as each phase opens.
          </p>
        )}
      </section>

      {passed.length > 0 && (
        <section>
          <h3 className="text-mute mb-2 text-xs font-semibold">
            Already passed
          </h3>
          <ul className="flex flex-col gap-2">
            {passed.slice(0, 8).map((item, i) => (
              <Row key={`${item.file}-${item.bs_date}`} item={item} index={i} />
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
