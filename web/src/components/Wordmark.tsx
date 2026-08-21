import Link from "next/link";

/** The name, set in the display face. Deliberately not coloured: crimson is reserved
 *  for dates that carry a consequence, and a brand mark is not one. */
export default function Wordmark({ className = "" }: { className?: string }) {
  return (
    <Link
      href="/"
      className={`font-display text-ink text-[1.375rem] leading-none font-medium tracking-[-0.01em] ${className}`}
    >
      Sarathi
    </Link>
  );
}
