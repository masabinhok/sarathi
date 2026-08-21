"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import Dateline from "@/components/Dateline";
import ThemeToggle from "@/components/ThemeToggle";
import Wordmark from "@/components/Wordmark";
import { fetchToday, type Today } from "@/lib/api";

const NAV = [
  { href: "/ask", label: "Ask" },
  { href: "/notices", label: "Notices" },
  { href: "/about", label: "About" },
];

/** Masthead: name, where you can go, and what day it is. The crest, the descriptor and
 *  the Devanagari subline moved to the landing page and the footer, where there is room
 *  to actually read them. */
export default function Header() {
  const pathname = usePathname();
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
    <header className="border-rule bg-paper/90 sticky top-0 z-20 border-b backdrop-blur">
      <div className="mx-auto flex h-14 max-w-[80rem] items-center gap-6 px-5 sm:px-8">
        <Wordmark />

        <nav className="flex items-center gap-5 text-[0.8125rem] font-medium">
          {NAV.map(({ href, label }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={
                  active
                    ? "text-ink border-ink border-b pb-0.5"
                    : "text-mute hover:text-ink border-b border-transparent pb-0.5 transition"
                }
              >
                {label}
              </Link>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-4">
          {/* The masthead scale of the dateline. */}
          {today && (
            <Dateline
              bs={today.bs_date}
              ad={today.ad_date}
              className="hidden sm:block"
            />
          )}
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
