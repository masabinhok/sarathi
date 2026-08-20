import Chat from "@/components/Chat";
import Feed from "@/components/Feed";
import Header from "@/components/Header";

export default function Home() {
  return (
    /* The split is the design: on the left you ask, on the right sits what the campuses
       actually published. They meet at a single hairline with no gutter between them. */
    <div className="flex min-h-dvh flex-col lg:h-dvh lg:min-h-0 lg:overflow-hidden">
      <Header />
      <div className="grid min-h-0 flex-1 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
        <Chat />
        <Feed />
      </div>
    </div>
  );
}
