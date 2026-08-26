"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  fetchDeadlines,
  fetchToday,
  type Deadline,
  type Today,
} from "@/lib/api";
import { handOver } from "@/lib/handoff";

/**
 * The hero is not a value proposition — it is the dateline at its largest.
 *
 * Every question in this world reduces to "what day is it, and what have I already
 * missed", so the page opens with today in both calendars and the single date that
 * matters most right now. The date is set in lapis at four and a half rem, which is
 * the dateline at its largest and the loudest the app's own colour ever gets.
 * Crimson appears only if that date has passed.
 */
export default function Hero() {
  const router = useRouter();
  const [today, setToday] = useState<Today | null>(null);
  const [next, setNext] = useState<Deadline | null>(null);
  const [question, setQuestion] = useState("");

  useEffect(() => {
    let live = true;
    fetchToday()
      .then((value) => live && setToday(value))
      .catch(() => {});
    fetchDeadlines()
      .then((feed) => {
        if (!live) return;
        setNext(feed.upcoming[0] ?? feed.passed[0] ?? null);
      })
      .catch(() => {});
    return () => {
      live = false;
    };
  }, []);

  const passed = next ? next.days < 0 : false;

  return (
    <section className="mx-auto w-full max-w-[84rem] px-5 pt-16 pb-20 sm:px-8">
      <p className="eyebrow">Today in Nepal</p>

      <div className="mt-4 flex flex-wrap items-end gap-x-10 gap-y-8">
        {/* The slot keeps its height before the date arrives, so the page does
            not open on a hole where the largest thing on it is about to be. */}
        <div className="font-mono leading-[0.95] tabular-nums">
          <div className="text-lapis text-[clamp(2.75rem,8vw,4.5rem)] font-medium tracking-[-0.03em]">
            {today ? (
              today.bs_date
            ) : (
              <span className="bg-lapis-soft inline-block h-[0.72em] w-[6.2ch] animate-pulse rounded-xs align-baseline" />
            )}
          </div>
          <div className="border-lapis/35 text-faint mt-2 border-t pt-2 text-[clamp(1rem,2.5vw,1.5rem)]">
            {today ? (
              today.ad_date
            ) : (
              <span className="bg-lapis-soft inline-block h-[0.72em] w-[6.2ch] animate-pulse rounded-xs align-baseline" />
            )}
          </div>
        </div>

        {next && (
          <div className="min-w-0 max-w-sm pb-1">
            <p className="eyebrow">
              {passed ? "Most recent deadline" : "Next deadline"}
            </p>
            <p className="font-display mt-1.5 text-[1.0625rem] leading-snug font-medium">
              {next.document}
            </p>
            <p
              className={`mt-1 font-mono text-[0.8125rem] ${
                passed ? "text-crimson" : "text-mute"
              }`}
            >
              {next.bs_date} ·{" "}
              {next.days === 0
                ? "today"
                : passed
                  ? `closed ${Math.abs(next.days)} days ago`
                  : `in ${next.days} days`}
            </p>
          </div>
        )}
      </div>

      <h1 className="font-display mt-16 max-w-[22ch] text-[clamp(2.5rem,6.5vw,4rem)] leading-[1.05] font-medium tracking-[-0.025em]">
        Ask about the IOE entrance exam and admission.
      </h1>
      <p className="text-mute mt-6 max-w-[42ch] text-[1.0625rem] leading-relaxed">
        Answered from the official notices, with every date in both Bikram
        Sambat and Gregorian.
      </p>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          const text = question.trim();
          // Handed over out of band, not as `?q=`: a question in the address bar is
          // asked again on every refresh, and opens a new conversation each time.
          if (text) handOver(text);
          router.push("/ask");
        }}
        className="mt-8 max-w-[36rem]"
      >
        <div className="border-rule-strong focus-within:border-lapis bg-card flex items-center gap-2 rounded-[10px] border px-4 py-3 transition">
          <input
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="What was the cutoff for Civil at Thapathali?"
            aria-label="Your question"
            className="field text-ink placeholder:text-faint min-w-0 flex-1 bg-transparent text-[0.9375rem] outline-none"
          />
          <button
            type="submit"
            aria-label="Ask"
            className="bg-lapis text-paper grid size-8 shrink-0 place-items-center rounded-[7px] transition"
          >
            <svg viewBox="0 0 24 24" className="size-4" fill="none" aria-hidden>
              <path
                d="M5 12h13m0 0-5-5m5 5-5 5"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </button>
        </div>
      </form>
    </section>
  );
}
