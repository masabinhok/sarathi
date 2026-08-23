import Link from "next/link";

/** The name, set in the display face and in lapis. Crimson is still refused here --
 *  it means a date with a consequence and a brand mark is not one -- but lapis is the
 *  app's own hand, and there is nothing on the page more the app's own than its name. */
export default function Wordmark({ className = "" }: { className?: string }) {
  return (
    <Link
      href="/"
      className={`font-display text-lapis text-[1.375rem] leading-none font-medium tracking-[-0.01em] ${className}`}
    >
      Sarathi
    </Link>
  );
}
