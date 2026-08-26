import Deadlines from "@/components/Deadlines";
import Footer from "@/components/Footer";
import Header from "@/components/Header";
import Notices from "@/components/Notices";

export const metadata = { title: "Notices — Sarathi" };

export default function NoticesPage() {
  return (
    <div className="flex min-h-dvh flex-col">
      <Header />
      <main className="mx-auto w-full max-w-[84rem] flex-1 px-5 py-12 sm:px-8">
        <p className="eyebrow">Published notices</p>
        <h1 className="font-display mt-3 max-w-[24ch] text-[clamp(1.875rem,4.5vw,2.5rem)] leading-[1.1] font-medium tracking-[-0.02em]">
          Everything the campuses have posted, newest first.
        </h1>
        <p className="text-mute mt-4 max-w-[46ch] text-[0.9375rem] leading-relaxed">
          Collected from the Entrance Exam Board, the central admission portal,
          and the Pulchowk, Thapathali, Pashchimanchal, Purwanchal and Chitwan
          campuses &mdash; admission and entrance notices only. Links open the
          original notice on the site that published it.
        </p>

        {/* Grid children default to min-width:auto, so without min-w-0 the widest
            nowrap element inside either column widens the whole page. */}
        <div className="mt-12 grid gap-12 lg:grid-cols-[1fr_20rem]">
          <div className="min-w-0">
            <Notices />
          </div>
          <div className="min-w-0">
            <Deadlines />
          </div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
