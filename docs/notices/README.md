# Extracted notices

Machine-extracted notice text, kept apart from `../translated/` so a glance at the path
says whether a document was written by a person or pulled out of a PDF by
`src/ioe/extract.py`.

Nothing lands here automatically. Extraction writes to `.cache/pending/` and stops; a file
appears here only when somebody read it in the admin console and pressed approve. That
split is the point: `../README.md` explains that the failure mode which matters is numeric
drift, and machine extraction does not change that — it changes what a reviewer starts
from, not whether there is one.

Each file records `encoding:` in its frontmatter. `preeti` means the source PDF was
typeset in a legacy font that maps Devanagari onto ASCII bytes, and the text was decoded
rather than read directly. Those files carry a warning in the body as well; check any
figure in them against the original PDF before relying on it.
