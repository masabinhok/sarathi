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

### `data/<campus>_priority_<year>.csv` — who applied for what

The published priority applications: one row per candidate, with their merit rank, their
ordered programme codes, and their quota group. `src/ioe/priority.py` walks these in merit
order and places each applicant into the best still-open programme on their own list,
which reconstructs that year's allocation exactly — IOE admits by a serial dictatorship,
so the outcome is fully determined by data that is already public.

Only `pulchowk_priority_2083.csv` exists. The filename is the interface: drop in
`thapathali_priority_2084.csv` and add that campus's priority-code table to
`priority.CODES`, and it is covered with no other change.

Seat counts come from `seats.py`, never from this file, so the booklet is transcribed once
and a disagreement between the two is a `verify()` failure rather than a silent drift.

### `data/cutoffs.csv` — 2079–2082 first-list cutoffs

The rank each programme's first admission list **closed at** — the last rank admitted,
per campus, per category, per year. The source's own note is "a lower numerical entrance
rank is better", so the figure is the largest number that still got a place, and a
student is inside it when their number is smaller. The column is `closing_rank` for that
reason; it was briefly `lowest_rank_admitted`, which reads as rank 1 and inverts the
meaning. `src/ioe/cutoffs.py` answers "what rank got in last time" from it, and
`notes/scrape_cutoffs.py` rebuilds it when a new year publishes.

228 rows: four campuses (Pulchowk, Thapathali, Pashchimanchal, Purwanchal) × four years
× the programmes each ran, split Regular and Full-fee. **Open/general category and first
admission list only.** `cutoffs.py` states every one of those limits in the block it
builds, because a student reading their rank against the wrong category is exactly the
mistake this data makes possible.

`source_url` is the **official campus admission list** each figure derives from, not the
aggregator the scrape reads. Some Purwanchal rows have no link and carry an empty
`source_url`: an empty cell is a known gap, and a wrong citation is a student sent to the
wrong document.

`cutoffs.verify()` cross-checks the file rather than trusting it. Every programme with a
cutoff must have seats at that campus in `seats.py` — transcribed from the booklet by a
completely different route — and every Full-fee cutoff must sit deeper than its Regular
counterpart, because a Regular seat is cheaper for the same degree and fills first. Both
hold across all 228 rows.

**Not covered, and not derivable from anything else here.** Chitwan publishes no
comparable figures. No affiliated college is covered. Reserved-quota competition is a
different pool entirely. And the pass list in
`03_BE_BArch_Entrance_Result_2083_pass_list.csv` cannot stand in for any of it: it carries
form number, rank, name, gender and district and **no programme or campus column**, so it
cannot say what anyone applied for or where.

For the current year, `src/ioe/priority.py` reaches further where it can: it simulates the
actual allocation over the published priority applications rather than reading last year's
outcome.
