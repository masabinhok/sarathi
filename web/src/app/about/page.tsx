import Footer from "@/components/Footer";
import Header from "@/components/Header";

export const metadata = { title: "About — Sarathi" };

const GOALS = [
  {
    title: "Answer from the notice, not from memory",
    body: "Every answer is drawn from a translated official document held in the app. When the documents don't cover a question, Sarathi says so and points to the source, rather than producing a confident guess about a fee or a deadline.",
  },
  {
    title: "Give every date in both calendars",
    body: "Notices are dated in Bikram Sambat and life is scheduled in Gregorian. Sarathi converts every date it is given, states plainly whether a deadline has passed, and never performs the arithmetic itself — the conversions are computed and handed to it.",
  },
  {
    title: "Look up a result exactly",
    body: "The published pass list is 7,179 rows. A form number or a merit rank is answered by direct lookup against that table, never by similarity search, so a rank is read rather than guessed.",
  },
  {
    title: "Collect what the campuses publish",
    body: "IOE, TU, the Entrance Exam Board and the Pulchowk, Pashchimanchal and Purwanchal campuses each publish notices on their own site. Sarathi gathers them into one reverse-chronological index, so a student checks one page instead of six.",
  },
];

const LIMITS = [
  "It will not tell you whether your rank is good enough for a campus. No cutoff data exists in the documents, and an estimate would be a guess with real consequences.",
  "It answers in English, and will not switch if you ask it to. Write to it in Nepali or any other language and it will understand you — but its Nepali is not good enough to be trusted with a date or a fee, so the answer comes back in English.",
  "It only handles IOE admission and entrance questions, and refuses everything else.",
  "It is not affiliated with IOE or Tribhuvan University. It reads the same public notices you can.",
];

export default function AboutPage() {
  return (
    <div className="flex min-h-dvh flex-col">
      <Header />

      <main className="mx-auto w-full max-w-[52rem] flex-1 px-5 py-16 sm:px-8">
        <p className="eyebrow">About</p>
        <h1 className="font-display mt-3 text-[clamp(2rem,5vw,2.75rem)] leading-[1.1] font-medium tracking-[-0.02em]">
          Every year, students miss deadlines that were published correctly.
        </h1>
        <p className="text-mute mt-6 max-w-[38rem] text-[1.0625rem] leading-relaxed">
          The notices go up on six different websites, mostly in Nepali, mostly
          as scanned PDFs, dated in a calendar you then have to convert. Nothing
          about that is anyone&apos;s fault, and all of it is avoidable. Sarathi
          reads the notices so a student doesn&apos;t have to hunt for them.
        </p>

        <h2 className="font-display border-lapis mt-16 border-b pb-2 text-[1.5rem] font-medium">
          What it sets out to do
        </h2>
        <ul className="mt-2">
          {GOALS.map(({ title, body }) => (
            <li key={title} className="border-rule border-b py-6">
              <h3 className="font-display text-[1.125rem] font-medium">
                {title}
              </h3>
              <p className="text-mute mt-2 text-[0.9375rem] leading-relaxed">
                {body}
              </p>
            </li>
          ))}
        </ul>

        <h2 className="font-display border-lapis mt-16 border-b pb-2 text-[1.5rem] font-medium">
          What it will not do
        </h2>
        <ul className="mt-2">
          {LIMITS.map((limit) => (
            <li
              key={limit}
              className="border-rule text-mute border-b py-4 text-[0.9375rem] leading-relaxed"
            >
              {limit}
            </li>
          ))}
        </ul>

        <h2 className="font-display border-lapis mt-16 border-b pb-2 text-[1.5rem] font-medium">
          How it is built
        </h2>
        <p className="text-mute mt-6 text-[0.9375rem] leading-relaxed">
          Official notices are translated to English by hand and reviewed, then
          split on their headings and indexed. A question is matched against
          those passages, the current date and any relevant conversions are
          computed and attached, and a language model writes the answer from
          that material. Everything runs locally — the model included — so a
          student&apos;s question never leaves the machine serving this app.
        </p>
      </main>

      <Footer />
    </div>
  );
}
