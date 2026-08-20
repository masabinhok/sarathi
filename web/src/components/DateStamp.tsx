/**
 * The ledger rail. Bikram Sambat above, Gregorian below, a hairline between them, in a
 * fixed-width monospace column. Students read notices in BS and live the rest of their
 * lives in AD, so neither calendar is a footnote to the other — and because every rail
 * is the same width, the hairlines align down the feed into one continuous rule.
 */
export default function DateStamp({
  bs,
  ad,
  dark = false,
  className = "",
}: {
  bs: string;
  ad: string;
  dark?: boolean;
  className?: string;
}) {
  return (
    <div className={`rail ${dark ? "rail-dark" : ""} ${className}`}>
      <div className="rail-bs">{bs || "—"}</div>
      <div className="rail-ad">{ad || "undated"}</div>
    </div>
  );
}
