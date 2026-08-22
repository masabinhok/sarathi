import AskWorkspace from "@/components/AskWorkspace";
import Header from "@/components/Header";

export const metadata = { title: "Ask — Sarathi" };

export default async function AskPage({ searchParams }: PageProps<"/ask">) {
  const params = await searchParams;
  const initial = typeof params.q === "string" ? params.q : "";

  return (
    // On a wide screen the shell is exactly the viewport and the three columns inside it
    // scroll independently. Narrower than that it becomes an ordinary page again, since
    // a fixed-height shell on a phone means a chat column a few centimetres tall.
    <div className="flex min-h-dvh flex-col xl:h-dvh xl:overflow-hidden">
      <Header />
      <AskWorkspace initial={initial} />
    </div>
  );
}
