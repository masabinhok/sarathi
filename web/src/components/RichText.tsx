import { Fragment, type ReactNode } from "react";

/**
 * The model answers in plain prose, but it reaches for bullets when it lists documents,
 * for numbered steps when it walks through a procedure, for **bold** when it names a
 * date, and for a markdown link when a document carries a URL. Those are the forms it
 * produces reliably, so those are the forms rendered.
 *
 * The parsing is deliberately forgiving rather than strict. A 7B model does not follow
 * formatting instructions closely enough to trust: told to keep lists flat it still
 * indents sub-points under a numbered step, and told to avoid links it still writes one.
 * Anything unhandled reaches the student as raw punctuation, so the renderer absorbs
 * what the model actually does instead of what it was asked to do.
 */

const ORDERED = /^\d+[.)]\s+/;
const MARKER = /^(?:[-*•]|\d+[.)])\s+/;
const LINK = /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g;

type Item = { text: string; children: string[] };
type Block =
  | { kind: "p"; text: string }
  | { kind: "list"; ordered: boolean; items: Item[] };

/** Split a block into list items, or null if it is not a list. Indented lines attach
 *  to the item above them, which is how the model writes sub-points under a step. */
function parseList(
  lines: string[],
): { items: Item[]; ordered: boolean } | null {
  const items: Item[] = [];
  let ordered = true;

  for (const line of lines) {
    const bare = line.trim();
    if (!MARKER.test(bare)) return null;
    const content = bare.replace(MARKER, "");

    if (/^\s/.test(line) && items.length) {
      items[items.length - 1].children.push(content);
    } else {
      if (!ORDERED.test(bare)) ordered = false;
      items.push({ text: content, children: [] });
    }
  }

  return items.length ? { items, ordered } : null;
}

/** Group the answer into paragraphs and lists.
 *
 *  Adjacent lists of the same kind are merged. The model habitually puts a blank line
 *  between numbered steps, which would otherwise split one procedure into a run of
 *  separate lists each restarting at 1 -- the exact confusion numbering exists to avoid. */
function toBlocks(text: string): Block[] {
  const out: Block[] = [];

  for (const chunk of text.split(/\n{2,}/)) {
    if (!chunk.trim()) continue;
    const list = parseList(chunk.split("\n"));

    if (!list) {
      out.push({ kind: "p", text: chunk });
      continue;
    }

    const prev = out[out.length - 1];
    if (prev?.kind === "list" && prev.ordered === list.ordered) {
      prev.items.push(...list.items);
    } else {
      out.push({ kind: "list", ordered: list.ordered, items: list.items });
    }
  }

  return out;
}

/** Render **bold** and [text](url) inside one line of text. */
function inline(text: string, keyBase: string): ReactNode[] {
  const nodes: ReactNode[] = [];

  text.split(/(\*\*[^*]+\*\*)/g).forEach((chunk, c) => {
    const bold =
      chunk.startsWith("**") && chunk.endsWith("**") && chunk.length > 4;
    const body = bold ? chunk.slice(2, -2) : chunk;
    const key = `${keyBase}-${c}`;

    // Split the remaining text on markdown links, keeping both halves of each match.
    const parts = body.split(LINK);
    const rendered: ReactNode[] = [];
    for (let i = 0; i < parts.length; i += 3) {
      if (parts[i])
        rendered.push(<Fragment key={`${key}-t${i}`}>{parts[i]}</Fragment>);
      const label = parts[i + 1];
      const href = parts[i + 2];
      if (label && href) {
        rendered.push(
          <a
            key={`${key}-a${i}`}
            href={href}
            target="_blank"
            rel="noreferrer noopener"
            className="text-blue underline decoration-current/40 underline-offset-2 hover:decoration-current"
          >
            {label}
          </a>,
        );
      }
    }

    nodes.push(
      bold ? (
        <strong key={key} className="font-semibold">
          {rendered}
        </strong>
      ) : (
        <Fragment key={key}>{rendered}</Fragment>
      ),
    );
  });

  return nodes;
}

export default function RichText({
  text,
  caret = false,
}: {
  text: string;
  caret?: boolean;
}) {
  const blocks = toBlocks(text);
  const last = blocks.length - 1;

  return (
    <>
      {blocks.map((block, b) => {
        const tail = caret && b === last;

        if (block.kind === "list") {
          // A procedure is only followable if its steps keep their numbers, so an
          // all-numbered block becomes an ordered list. The numbering is re-derived
          // from position: the model sometimes restarts the count partway down.
          const { items, ordered } = block;
          const List = ordered ? "ol" : "ul";

          return (
            <List key={b} className="my-2 space-y-1.5 first:mt-0 last:mb-0">
              {items.map((item, i) => {
                const lastItem = i === items.length - 1;
                return (
                  <li key={i} className="flex gap-2.5">
                    {ordered ? (
                      <span className="text-emerald min-w-[1.1rem] shrink-0 text-right font-mono text-[0.8em] tabular-nums">
                        {i + 1}.
                      </span>
                    ) : (
                      <span className="text-emerald mt-[0.55em] size-1 shrink-0 rounded-full bg-current" />
                    )}
                    <span className="min-w-0">
                      {inline(item.text, `${b}-${i}`)}
                      {tail && lastItem && !item.children.length && (
                        <span className="caret" />
                      )}
                      {item.children.length > 0 && (
                        <ul className="mt-1.5 space-y-1.5">
                          {item.children.map((child, c) => (
                            <li key={c} className="flex gap-2.5">
                              <span className="bg-current/50 mt-[0.55em] size-1 shrink-0 rounded-full" />
                              <span className="min-w-0">
                                {inline(child, `${b}-${i}-${c}`)}
                                {tail &&
                                  lastItem &&
                                  c === item.children.length - 1 && (
                                    <span className="caret" />
                                  )}
                              </span>
                            </li>
                          ))}
                        </ul>
                      )}
                    </span>
                  </li>
                );
              })}
            </List>
          );
        }

        return (
          <p key={b} className="my-2 first:mt-0 last:mb-0">
            {inline(block.text, String(b))}
            {tail && <span className="caret" />}
          </p>
        );
      })}
    </>
  );
}
