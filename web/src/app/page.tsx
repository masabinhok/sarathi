import Link from "next/link";
import Footer from "@/components/Footer";
import Header from "@/components/Header";
import Hero from "@/components/Hero";
import NoticeRail from "@/components/NoticeRail";

// Three claims, each of which the app actually keeps. Nothing here is aspirational.
const PROMISES = [
  {
    label: "Grounded",
    title: "It quotes the notice, and names it",
    body: "Answers are drawn from translated official documents held in the app, and each one says which document it came from, so you can check it against the original.",
  },
  {
    label: "Both calendars",
    title: "Every date twice, and never calculated",
    body: "Bikram Sambat and Gregorian, side by side. Conversions are computed before the answer is written, so a deadline is never the result of arithmetic done in a model's head.",
  },
  {
    label: "Honest",
    title: "It says when it doesn't know",
    body: "When the notices don't cover your question, Sarathi tells you that and points you to the official source, instead of writing something plausible about a fee or a date.",
  },
];

export default function Home() {
  return (
    <div className="flex min-h-dvh flex-col">
      <Header />
      <main className="flex-1">
        <Hero />

        {/* The one tinted field on the site. These three claims are the app talking
            about itself rather than reporting a notice, so the band is laid in the
            app's own colour -- and it is what keeps the page from opening as three
            screens of white. The rules inside it take the same cast, so the band
            reads as one sheet of paper rather than a warm grid on a cool ground. */}
        <section className="bg-lapis-soft">
          <div className="mx-auto max-w-[84rem] px-5 sm:px-8">
            <div className="grid md:grid-cols-3">
              {PROMISES.map(({ label, title, body }, i) => (
                <article
                  key={label}
                  className={`border-lapis/15 py-10 md:px-8 md:first:pl-0 md:last:pr-0 ${
                    i > 0 ? "border-t md:border-t-0 md:border-l" : ""
                  }`}
                >
                  <p className="eyebrow">{label}</p>
                  <h2 className="font-display mt-3 text-[1.25rem] leading-snug font-medium">
                    {title}
                  </h2>
                  <p className="text-mute mt-2.5 text-[0.9375rem] leading-relaxed">
                    {body}
                  </p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="border-rule border-t">
          <div className="mx-auto grid max-w-[84rem] gap-12 px-5 py-16 sm:px-8 lg:grid-cols-[1fr_24rem]">
            <div className="max-w-[38rem]">
              <h2 className="font-display text-[clamp(1.75rem,4vw,2.25rem)] leading-tight font-medium tracking-[-0.02em]">
                Six notice boards, six websites. This is all of them, in one
                place.
              </h2>
              <p className="text-mute mt-5 text-[1rem] leading-relaxed">
                The Entrance Exam Board, the Institute of Engineering, Tribhuvan
                University, and the Pulchowk, Pashchimanchal and Purwanchal
                campuses each post their own notices. Sarathi collects them into
                a single index, newest first, with the published date in both
                calendars — and you can ask about any of them.
              </p>
              <Link
                href="/notices"
                className="text-lapis decoration-lapis/40 hover:decoration-lapis mt-6 inline-block text-[0.9375rem] font-medium underline underline-offset-4"
              >
                Browse every notice
              </Link>
            </div>
            <NoticeRail />
          </div>
        </section>
      </main>
      <Footer />
    </div>
  );
}
