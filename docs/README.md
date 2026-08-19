# Source documents

Every `.md` file in this folder is indexed into the retrieval store and can be quoted
back to a student. Treat it as the bot's ground truth: if a number is wrong here, the
bot states it confidently and a student may act on it.

Files beginning with `_` and this README are skipped by the indexer.

## Frontmatter

Each document needs YAML frontmatter. `title` and `source` are required; the rest are
optional but strongly recommended, since they are what the bot cites.

```yaml
---
title: BE/BArch Entrance Examination Syllabus
source: IOE Entrance Exam Board
url: https://entrance.ioe.edu.np/
year: 2081            # admission year in BS, omit for evergreen process docs
level: undergraduate  # undergraduate | postgraduate | general
---
```

`year` matters. Anything year-specific (dates, fees, cutoffs, seat counts) must carry it
so the bot can say "per the 2081 notice" rather than implying the figure is permanent.
Leave `year` off only for documents that do not change year to year.

## Writing the content

- Use `##` headings for each distinct topic. Chunks are split on headings, so a heading
  boundary is a retrieval boundary — one topic per section.
- Keep sections self-contained. A chunk is retrieved alone, without its neighbours, so
  a section reading "as described above" loses its referent.
- Preserve exact figures, program names, and dates from the original document. Do not
  round, paraphrase, or convert BS dates to AD silently.
- Tables are fine and survive chunking, as long as one table stays inside one section.

## Translation

Documents are translated to English before being added here. Retrieval itself does not
need this — `bge-m3` is multilingual and matches English queries against Nepali text
perfectly well — but the generator (`qwen2.5:7b`) answers in English and degrades when
it has to translate context while reasoning over it.

When translating, the failure mode that matters is numeric drift: marks, fees,
percentages, quota splits, and dates being silently altered. Verify those against the
original after translating. Keeping the original Nepali line beneath a translated figure
is a reasonable safety net — `bge-m3` indexes both without issue.

## Rebuilding the index

After adding or editing files:

```bash
uv run ioe-index
```

Nothing is picked up until that runs.
