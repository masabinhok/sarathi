"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import ThemeToggle from "@/components/ThemeToggle";
import { fetchToday, type Today } from "@/lib/api";

export default function Header() {
  const [today, setToday] = useState<Today | null>(null);

  useEffect(() => {
    let live = true;
    fetchToday()
      .then((value) => live && setToday(value))
      .catch(() => {});
    return () => {
      live = false;
    };
  }, []);

  return (
    <header className="bg-shell border-shell-line flex h-14 shrink-0 items-center gap-4 border-b px-4 sm:px-5">
      <Link href="/" className="group flex min-w-0 items-center gap-3">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/tu-crest.svg"
          alt="Tribhuvan University"
          width={30}
          height={30}
          className="size-[30px] shrink-0"
        />
        <span className="min-w-0 leading-tight">
          {/* The name carries the descriptor beside it: "Sarathi" alone tells a
              first-time visitor nothing about what they have landed on. */}
          <span className="block truncate text-[15px] tracking-[-0.01em]">
            <span className="text-shell-ink group-hover:text-blue font-semibold transition">
              Sarathi
            </span>
            <span className="text-shell-mute hidden sm:inline">
              {" \u00b7 IOE Entrance and Admission Assistant"}
            </span>
          </span>
          <span className="text-shell-mute font-deva hidden truncate text-[11px] sm:block">
            त्रिभुवन विश्वविद्यालय · इन्जिनियरिङ अध्ययन संस्थान
          </span>
        </span>
      </Link>

      <div className="ml-auto flex items-center gap-3 sm:gap-4">
        {/* The rail motif, laid on its side to fit the bar. */}
        {today && (
          <div className="border-shell-line hidden items-center gap-2.5 rounded-lg border px-2.5 py-1 font-mono text-[11px] md:flex">
            <span className="text-shell-ink">{today.bs_label}</span>
            <span className="bg-shell-line h-3.5 w-px" />
            <span className="text-shell-mute">{today.ad_date}</span>
          </div>
        )}
        <ThemeToggle />
        <Link
          href="/admin"
          className="border-shell-line text-shell-mute hover:border-blue hover:text-blue rounded-lg border px-2.5 py-1.5 text-xs font-medium transition"
        >
          Admin
        </Link>
      </div>
    </header>
  );
}
