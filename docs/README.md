# Source documents

```
downloads/    original PDFs as published, kept for provenance -- never indexed
translated/   English Markdown, indexed into the retrieval store
data/         lookup tables (CSV), queried exactly, never indexed
```

Every `.md` file under `translated/` is indexed and can be quoted back to a student.
Treat it as the bot's ground truth: if a number is wrong here, the bot states it
confidently and a student may act on it.

`downloads/` and `data/` are skipped by the indexer, along with files beginning with `_`
and this README.

## What belongs in `data/` rather than `translated/`

Long keyed tables -- pass lists, seat matrices, anything a student looks up by their own
number. Vector search over names and roll numbers returns near-noise, and 7,000 rows of
table would flood the chunk store without answering a question anyone phrases in words.
These are answered by exact lookup in `src/ioe/results.py` instead.

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
audience: foreign     # omit unless the document applies ONLY to foreign applicants
---
```

`audience: foreign` marks a document that applies only to foreign applicants. Those
chunks are demoted during retrieval unless the question signals a foreign applicant, so
that a generally-phrased question is answered for the majority of students. Omit the
field entirely for documents that apply to everyone -- do not write `audience: all`.

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
