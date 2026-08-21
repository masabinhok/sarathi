import Link from "next/link";

/** The things a student should know about this app but should not have to read
 *  before asking a question. */
export default function Footer() {
  return (
    <footer className="border-rule mt-auto border-t">
      <div className="text-mute mx-auto flex max-w-[80rem] flex-col gap-4 px-5 py-8 text-[0.8125rem] sm:flex-row sm:items-start sm:gap-10 sm:px-8">
        <div className="max-w-md">
          <p className="font-devanagari text-ink text-[0.8125rem]">
            त्रिभुवन विश्वविद्यालय · इन्जिनियरिङ अध्ययन संस्थान
          </p>
          <p className="mt-2 leading-relaxed">
            Sarathi is unofficial and its answers are generated. Confirm
            anything you act on against{" "}
            <a
              href="https://entrance.ioe.edu.np"
              target="_blank"
              rel="noreferrer noopener"
              className="text-ink decoration-rule-strong hover:decoration-current underline underline-offset-2"
            >
              entrance.ioe.edu.np
            </a>{" "}
            or your campus admission office.
          </p>
        </div>

        <div className="flex flex-col gap-1.5 sm:ml-auto">
          <Link href="/about" className="hover:text-ink transition">
            About and goals
          </Link>
          <Link href="/notices" className="hover:text-ink transition">
            All notices
          </Link>
          <Link href="/admin" className="hover:text-ink transition">
            Admin
          </Link>
        </div>
      </div>
      <p className="text-faint mx-auto max-w-[80rem] px-5 pb-6 text-[0.6875rem] sm:px-8">
        TU crest vectorised by Samir Lamsal.
      </p>
    </footer>
  );
}
