"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchToday, type Today } from "@/lib/api";

export default function Masthead() {
  const [today, setToday] = useState<Today | null>(null);

  useEffect(() => {
    fetchToday()
      .then(setToday)
      .catch(() => {});
  }, []);

  return (
    <header className="border-line bg-paper-raised border-b">
      {/* Seal rule: the one gold line on the page, standing in for the stamp across the
          top of an official notice. */}
      <div className="bg-gold h-[3px] w-full" />

      <div className="mx-auto flex w-full max-w-6xl items-start justify-between gap-6 px-5 py-5">
        <Link href="/" className="group flex items-start gap-4">
          <div className="border-line-strong text-gold mt-0.5 flex size-11 shrink-0 items-center justify-center rounded-full border font-serif text-lg leading-none">
            IOE
          </div>
          <div className="leading-tight">
            <p className="text-ink text-[15px] font-medium">
              त्रिभुवन विश्वविद्यालय, इन्जिनियरिङ अध्ययन संस्थान
            </p>
            <p className="text-ink-soft text-[13px]">
              Tribhuvan University &middot; Institute of Engineering
            </p>
            <h1 className="text-ink group-hover:text-sky mt-1.5 font-serif text-xl leading-none font-semibold">
              Admission Assistant
            </h1>
          </div>
        </Link>

        <div className="flex shrink-0 items-start gap-5">
          <div className="hidden text-right sm:block">
            <p className="eyebrow mb-1">आज / Today</p>
            {today ? (
              <span className="datepair items-end">
                <span className="datepair-bs">{today.bs_label}</span>
                <span className="datepair-ad">
                  {today.ad_label} &middot; {today.weekday}
                </span>
              </span>
            ) : (
              <span className="text-ink-faint font-mono text-xs">—</span>
            )}
          </div>
          <Link
            href="/admin"
            className="border-line text-ink-soft hover:border-line-strong hover:text-ink mt-1 rounded border px-2.5 py-1 text-xs transition"
          >
            Admin
          </Link>
        </div>
      </div>
    </header>
  );
}
