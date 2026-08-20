"use client";

import { useEffect, useState } from "react";
import Deadlines from "@/components/Deadlines";
import Notices from "@/components/Notices";
import { fetchNotices } from "@/lib/api";

type Tab = "notices" | "dates";

export default function Feed() {
  const [tab, setTab] = useState<Tab>("notices");
  const [meta, setMeta] = useState<{ count: number; updated: string } | null>(
    null,
  );

  useEffect(() => {
    let live = true;
    fetchNotices()
      .then((feed) => {
        if (live)
          setMeta({ count: feed.notices.length, updated: feed.updated_at });
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, []);

  const tabs: { key: Tab; label: string }[] = [
    { key: "notices", label: "Notices" },
    { key: "dates", label: "Key dates" },
  ];

  return (
    <section
      aria-label="Published notices and dates"
      className="bg-feed border-line flex min-h-0 min-w-0 flex-col border-t lg:h-full lg:border-t-0 lg:border-l"
    >
      <div className="border-line flex items-center gap-3 border-b px-4 py-2.5 sm:px-5">
        <div
          role="tablist"
          aria-label="Feed section"
          className="bg-line/50 flex gap-0.5 rounded-lg p-0.5"
        >
          {tabs.map(({ key, label }) => (
            <button
              key={key}
              role="tab"
              aria-selected={tab === key}
              onClick={() => setTab(key)}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition ${
                tab === key
                  ? "bg-card text-ink shadow-[0_1px_2px_rgba(15,23,42,0.08)]"
                  : "text-mute hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        {meta && tab === "notices" && (
          <span className="text-faint ml-auto truncate font-mono text-[11px]">
            {meta.count} notices · {new Date(meta.updated).toLocaleDateString()}
          </span>
        )}
      </div>

      <div className="scroll-thin flex-1 overflow-y-auto px-4 py-4 sm:px-5">
        {tab === "notices" ? <Notices /> : <Deadlines />}
      </div>

      <footer className="border-line text-faint shrink-0 border-t px-4 py-2.5 text-[11px] leading-relaxed sm:px-5">
        Unofficial, and answers are generated — confirm anything you act on
        against{" "}
        <a
          href="https://entrance.ioe.edu.np"
          target="_blank"
          rel="noreferrer"
          className="hover:text-blue underline underline-offset-2 transition"
        >
          entrance.ioe.edu.np
        </a>
        . TU crest vectorized by Samir Lamsal.
      </footer>
    </section>
  );
}
