/** Placeholder rows shaped like the ones they stand in for, so an index does not jump
 *  and does not briefly claim to be empty while the request is still in flight. */
export default function Skeleton({ rows = 4 }: { rows?: number }) {
  return (
    <ul aria-hidden>
      {Array.from({ length: rows }, (_, i) => (
        <li
          key={i}
          className="border-rule flex animate-pulse gap-4 border-b py-4"
          style={{ animationDelay: `${i * 90}ms` }}
        >
          <div className="dateline space-y-1.5">
            <div className="bg-rule h-3 rounded-xs" />
            <div className="bg-rule/60 h-2.5 rounded-xs" />
          </div>
          <div className="flex-1 space-y-2">
            <div className="bg-rule h-3 rounded-xs" />
            <div className="bg-rule h-3 w-2/3 rounded-xs" />
            <div className="bg-rule/60 h-2.5 w-20 rounded-xs" />
          </div>
        </li>
      ))}
    </ul>
  );
}
