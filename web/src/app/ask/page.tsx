import Chat from "@/components/Chat";
import Header from "@/components/Header";
import NoticeRail from "@/components/NoticeRail";

export const metadata = { title: "Ask — Sarathi" };

export default async function AskPage({ searchParams }: PageProps<"/ask">) {
  const params = await searchParams;
  const initial = typeof params.q === "string" ? params.q : "";

  return (
    <div className="flex min-h-dvh flex-col">
      <Header />
      {/* The conversation is centred on the viewport, not in the space left over beside
          the notices: the rail lives in the right gutter so it cannot push the column
          off axis. Below xl the rail simply moves underneath. */}
      <main className="mx-auto grid w-full max-w-[84rem] flex-1 grid-cols-1 gap-12 px-5 sm:px-8 xl:grid-cols-[1fr_minmax(0,42rem)_1fr]">
        <div className="hidden xl:block" />
        <Chat initial={initial} />
        <div className="border-rule border-t pt-8 pb-10 xl:border-t-0 xl:pt-12">
          <NoticeRail />
        </div>
      </main>
    </div>
  );
}
