/** Placeholder rows shaped like the cards they stand in for, so the feed does not jump
 *  and does not briefly claim to be empty while the request is still in flight. */
export default function Skeleton({ rows = 4 }: { rows?: number }) {
  return (
    <ul className="flex flex-col gap-2" aria-hidden>
      {Array.from({ length: rows }, (_, i) => (
        <li
          key={i}
          className="border-line bg-card flex animate-pulse gap-3.5 rounded-xl border p-3"
          style={{ animationDelay: `${i * 90}ms` }}
        >
          <div className="rail space-y-1.5">
            <div className="bg-line h-3 rounded" />
            <div className="bg-line/60 h-2.5 rounded" />
          </div>
          <div className="flex-1 space-y-2">
            <div className="bg-line/70 h-2.5 w-16 rounded" />
            <div className="bg-line h-3 rounded" />
            <div className="bg-line h-3 w-2/3 rounded" />
          </div>
        </li>
      ))}
    </ul>
  );
}
