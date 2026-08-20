import { Fragment, type ReactNode } from "react";

/**
 * The model answers in plain prose, but it reaches for bullets when it lists documents
 * or fee steps, and for **bold** when it names a date. Rendering just those two forms
 * keeps a long answer scannable; anything richer would be markdown the model does not
 * reliably produce, so it is left as written.
 */

const BULLET = /^\s*(?:[-*•]|\d+[.)])\s+/;

function inline(text: string, keyBase: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith("**") && part.endsWith("**") && part.length > 4 ? (
      <strong key={`${keyBase}-${i}`} className="font-semibold">
        {part.slice(2, -2)}
      </strong>
    ) : (
      <Fragment key={`${keyBase}-${i}`}>{part}</Fragment>
    ),
  );
}

export default function RichText({
  text,
  caret = false,
}: {
  text: string;
  caret?: boolean;
}) {
  const blocks = text.split(/\n{2,}/).filter((block) => block.trim());
  const last = blocks.length - 1;

  return (
    <>
      {blocks.map((block, b) => {
        const lines = block.split("\n");
        if (lines.every((line) => BULLET.test(line))) {
          return (
            <ul key={b} className="my-2 space-y-1.5 first:mt-0 last:mb-0">
              {lines.map((line, i) => (
                <li key={i} className="flex gap-2.5">
                  <span className="text-emerald mt-[0.55em] size-1 shrink-0 rounded-full bg-current" />
                  <span>
                    {inline(line.replace(BULLET, ""), `${b}-${i}`)}
                    {caret && b === last && i === lines.length - 1 && (
                      <span className="caret" />
                    )}
                  </span>
                </li>
              ))}
            </ul>
          );
        }
        return (
          <p key={b} className="my-2 first:mt-0 last:mb-0">
            {inline(block, String(b))}
            {caret && b === last && <span className="caret" />}
          </p>
        );
      })}
    </>
  );
}
