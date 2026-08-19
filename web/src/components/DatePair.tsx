/**
 * The recurring device of this interface: a Bikram Sambat date over its Gregorian
 * equivalent, split by a hairline. Students read notices in BS and live the rest of
 * their lives in AD, so neither calendar is a footnote to the other.
 */
export default function DatePair({
  bs,
  ad,
  align = "left",
}: {
  bs: string;
  ad: string;
  align?: "left" | "right";
}) {
  if (!bs && !ad) {
    return <span className="text-ink-faint font-mono text-xs">undated</span>;
  }
  return (
    <span className={`datepair ${align === "right" ? "items-end" : "items-start"}`}>
      <span className="datepair-bs">{bs || "—"}</span>
      <span className="datepair-ad">{ad || "—"}</span>
    </span>
  );
}
