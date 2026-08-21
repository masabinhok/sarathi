import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Renders the model's answer as real Markdown.
 *
 * This replaced a hand-rolled parser that handled bullets, bold, and links, which meant
 * a table or a heading reached the student as raw punctuation and the system prompt had
 * to forbid the model from producing them. Raw HTML stays disabled — the default — since
 * the text is model output and therefore untrusted.
 *
 * The streaming cursor is a character appended to the source rather than an element
 * spliced into the tree: a renderer that re-parses on every token cannot be relied on to
 * keep a caret node in the last text position.
 */
const CURSOR = "▍";

export default function Markdown({
  text,
  streaming = false,
}: {
  text: string;
  streaming?: boolean;
}) {
  return (
    <div className="answer">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noreferrer noopener">
              {children}
            </a>
          ),
          // A fee table must scroll inside the column rather than widening it.
          table: ({ children }) => (
            <div className="scroll-thin my-3 overflow-x-auto">
              <table>{children}</table>
            </div>
          ),
        }}
      >
        {streaming ? `${text}${CURSOR}` : text}
      </ReactMarkdown>
    </div>
  );
}
