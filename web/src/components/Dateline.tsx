/**
 * The dateline — the one ornament in this design, and the spine of the product.
 *
 * Bikram Sambat above, Gregorian below, a hairline between, in a fixed-width monospace
 * column. Students read notices in BS and live the rest of their lives in AD, so neither
 * calendar is a footnote to the other. Because every dateline is the same width, the
 * hairlines align down a page into one continuous rule.
 *
 * It appears at three scales — masthead, notice row, deadline — and nowhere else.
 */
export default function Dateline({
  bs,
  ad,
  className = "",
}: {
  bs: string;
  ad: string;
  className?: string;
}) {
  return (
    <div className={`dateline ${className}`}>
      <div className="dateline-bs">{bs || "—"}</div>
      <div className="dateline-ad">{ad || "undated"}</div>
    </div>
  );
}
