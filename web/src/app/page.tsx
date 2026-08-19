import Chat from "@/components/Chat";
import Deadlines from "@/components/Deadlines";
import Notices from "@/components/Notices";

export default function Home() {
  return (
    <div className="mx-auto w-full max-w-6xl px-5 py-8">
      <div className="grid gap-10 lg:grid-cols-[minmax(0,1.55fr)_minmax(0,1fr)]">
        <div className="flex flex-col gap-10">
          <Chat />
          <Deadlines />
        </div>
        <Notices />
      </div>
    </div>
  );
}
