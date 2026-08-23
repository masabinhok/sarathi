import type { Source } from "@/lib/api";

/**
 * The documents an answer was drawn from, printed under it like a newspaper's credit
 * line: numbered, ruled, no cards.
 *
 * These come from the retrieval step, not from anything the model wrote. Asking a 7B
 * model to emit citation markers gives you citations that are usually right, and a
 * usually-right citation is worse than none — a student cannot tell a dropped marker
 * from an answer that was never grounded in the first place.
 */
export default function Sources({ sources }: { sources: Source[] }) {
  return (
    <div className="border-rule mt-6 border-t pt-3">
      <p className="eyebrow">
        {sources.length === 1 ? "Source" : `Sources · ${sources.length}`}
      </p>
      <ol className="mt-2.5 space-y-2.5">
        {sources.map((source, i) => {
          const label = source.url ? (
            <a
              href={source.url}
              target="_blank"
              rel="noreferrer noopener"
              className="text-lapis decoration-lapis/40 hover:decoration-lapis underline underline-offset-2 transition"
            >
              {source.title}
              <span aria-hidden> ↗</span>
            </a>
          ) : (
            <span className="text-mute">{source.title}</span>
          );

          return (
            <li
              key={source.file}
              className="grid grid-cols-[1.75rem_1fr] items-baseline text-[0.8125rem] leading-snug"
            >
              <span className="font-mono text-faint text-[0.6875rem] tabular-nums">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span className="min-w-0">
                {label}
                {/* The year names the admission cycle and the headings name the part of
                    the notice that was read, which is what turns a citation from "it is
                    in this 40-page booklet somewhere" into somewhere to look. */}
                {(source.year || source.sections.length > 0) && (
                  <span className="text-faint block">
                    {source.year && (
                      <span className="font-mono text-[0.6875rem]">
                        {source.year}
                      </span>
                    )}
                    {source.year && source.sections.length > 0 && " · "}
                    {source.sections.join(" · ")}
                  </span>
                )}
              </span>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
