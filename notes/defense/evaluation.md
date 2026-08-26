# Sarathi — the evaluation suite

`src/ioe/eval.py` · run with `uv run python -m ioe.eval`

A document for the defense panel. It explains what the suite asserts, why it asserts that
rather than something else, what it has caught, and what it cannot see.

---

## 1. The design decision

**The suite asserts which evidence reached the model, not the prose the model wrote.**

A question about the *dharauti* must put the worked fee figures in front of the model. A
question carrying a form number must put the pass-list record there. Whether the sentence
around the figure reads well is a judgement and needs a judge. Whether the figure was in
front of the model at all is a **fact**.

Three properties follow, and they are the reason for the choice:

| Property | Consequence |
| --- | --- |
| Deterministic | The same input gives the same verdict. No sampling, no grading, no variance in the measurement itself. |
| No golden answers | Nothing to maintain when the 2084 notices replace the 2083 ones. A golden-answer suite goes stale every admission cycle; this one does not. |
| Fast | ~3 minutes for the whole suite, because most cases stop the graph before generation. |

And it targets the failure this architecture is *most* exposed to: **the model quietly
deciding not to retrieve.** A system that answers from parametric memory instead of from
the notices fails silently and fluently, which is precisely the failure the project exists
to prevent.

### Why not measure answer accuracy directly?

Because it needs a judge. Either a human grades every run — which is not repeatable and
does not scale to a suite run dozens of times a day — or a second language model grades
it, which substitutes one unreliable instrument for another and cannot be defended as
ground truth. Neither is stronger than checking a fact that is already checkable.

We do read answers by hand as well. §5 records what that found, and §4 records what we
added to the suite because of it.

---

## 2. What a case looks like

```python
(group, question, must be present, must be absent)

("fees",    "how much is the dharauti",        {FEES},      {DECLINED})
("fees",    "how much is the entrance exam fee", set(),     {FEES, DECLINED})
("results", "did form 2083-99999 pass",        {LOOKUP},    {DECLINED})
("cutoffs", "who is rank 340",                 {LOOKUP},    {CUTOFFS, DECLINED})
```

**`must be absent` is as load-bearing as `must be present`**, and is where the subtle
regressions show up:

- A fee question that *also* refuses is broken even though the figures arrived.
- The **entrance examination fee** is different money from the study fee. Answering it
  from the fee table is a specific, known failure, so those cases assert that the fee
  block does **not** fire.
- `did form 2083-99999 pass` — a number that is not on the list — must still reach the
  lookup. Saying "not found" is the correct answer; inventing a candidate is the failure.
- `who is rank 340` must fetch the pass-list record. `can i get computer with rank 340`
  must **not** — there the number is the student's own, stated hypothetically, and looking
  it up would print a stranger's name and district beside real cutoff figures.

The evidence vocabulary is eleven named blocks: `documents`, `lookup`, `fees`, `seats`,
`priority`, `chances`, `cutoffs`, `notices`, `dates`, `summary`, `uncovered` — plus
`declined` for a refusal.

---

## 3. Composition — 71 checks

| Group | Cases | What it protects |
| --- | ---: | --- |
| `fees` | 15 | Worked fee totals fire; entrance/form fee does **not** |
| `scope` | 10 | Off-topic refused or declared uncovered; genuine questions answered |
| `results` | 7 | Pass-list lookup by form number, rank, name, district, topper |
| `cutoffs` | 7 | Closing ranks fire; a hypothetical rank is not looked up |
| `docs` | 6 | Ordinary retrieval over the thirteen notices |
| `chances` | 6 | The 2083 allocation and the published cut-offs stay in their own lanes |
| `language` | 3 | A Nepali or Hindi question still reaches the documents |
| **Single-turn total** | **54** | |
| `issue24` · `follow-up` · `hygiene` | 12 turns | Multi-turn threads — see below |
| Figure checks | 5 | The stated number appears in the answer — see §4 |

Plus a **detector precision check**: `scope.is_task_substitution` must catch all 10 of a
fixed task list (`write me a python function`, `solve x^2 + 5x + 6 = 0`, …) **and stay
silent on every one of the 66 questions in the suite.** Its danger is not missing a task —
it is firing on a genuine question, which is how an earlier scope guard broke conversations.

### The conversation threads

Single-turn cases cannot test continuity, and continuity is where the system's reported
defects lived. Three threads run turn by turn against one checkpointed conversation:

- **`issue24`** — the reported transcript verbatim, including the typo. `hi` → a fee
  question → a request to write Python → `and what other cateogry i could study in` →
  `what is its source` → `foreign?`. Every follow-up here is answerable and every one is
  meaningless read on its own.
- **`follow-up`** — `what is the entrance exam fee` → `how do i pay it?` → `and the
  deadline?` → `what did i just ask you about?`
- **`hygiene`** — a Nepali fee question, then `thanks!`, asserting that turn-scoped state
  is cleared between turns.

---

## 4. The figure checks — added because the suite had a blind spot

The design in §1 has a cost, and it is worth stating to the panel rather than being asked
about it.

**A block can be correct, the evidence assertion can pass, and the model can still read the
wrong line out of it.**

That happened. Asked *"What does the whole degree cost at full fee?"*, the assistant
answered **218,070** — the admission-day total, printed on the line directly above the
right one. The fee block was correct. The evidence assertion passed. The suite reported
success. Told it was wrong, the model produced **190,456**, a figure that appears in no
table in the corpus.

So five cases now run the answer through generation and assert that one specific figure —
already printed in a block — appears in it. This is not grading prose. It is checking
whether a number that was handed to the model survives into its answer.

| Check | Must contain |
| --- | --- |
| `What does the whole degree cost at full fee?` | `591,632` |
| …then `you are so wrong` | `591,632` *(it must not capitulate)* |
| …then `for regular` | `72,287` *(a two-word follow-up carrying no intent of its own)* |
| `rank 40 … pulchowk computer engineering full fee` | `179` *(Full-fee, not the Regular 27)* |
| `how much do i pay on admission day as a regular student` | `19,269` |

They are slow, which is why there are five and not fifty. They run last and can be run
alone with `uv run python -m ioe.eval figures`.

**These checks caught two regressions during the fix they prompted** — cases that looked
fixed by inspection and were not.

---

## 5. What the suite has actually caught

Not a hypothetical list. Each of these was found by the suite or by a reading prompted by
it, and each is fixed:

| Defect | How it presented |
| --- | --- |
| **Devanagari fee terms unreachable** | Five terms sat inside `\b(…)\b`. A Devanagari word ends in a combining vowel sign, which Python does not count as a word character — so `धरौती` was not unreliable, it was *unmatchable*. Every Nepali fee question was being refused. |
| **A tool-argument schema failure** | The planner emitted `category: "full_fee"` against a strict enum. Validation failed, the call errored, and **nine cases lost their figures** while every other tool in the same batch succeeded — 49/53 → 44/53. |
| **A stranger's identity beside real cut-offs** | `i got rank 660, what can i study` looked 660 up in the pass list and printed that candidate's name and district next to cutoff figures. |
| **A block that came and went** | Whether the priority *rules* appeared was left to the planner — they appeared in one run and not the next, for the section stating that an applicant who declines a lower priority is excluded from the process entirely. |
| **A translation that changed the question** | `धरौती कति हो` — *how much is the deposit* — was translated as *"How many districts are there"*. The fee block was correct; the model answered the question it was given. **The suite could not see this**: the evidence was right and only the prose was wrong. It was found by reading an answer. |

That last row is the honest one. It is why §4 exists.

---

## 6. Results

```
$ uv run python -m ioe.eval
...
detector   10/10 caught, silent on all 66 questions in this suite
...
69/71 passed
```

**The two failures are the same known gap, and it is measured rather than assumed.**

Both are the *weak-evidence* case: an off-topic question that finds a plausible-looking
passage and is answered instead of declined — `how do i apply to Kathmandu University`,
and `and what other cateogry i could study in`.

It cannot be fixed by moving the relevance threshold, and that is a measurement, not an
opinion:

| | Best passage score |
| --- | --- |
| Off-topic questions | 0.357 – **0.576** |
| Genuine questions | **0.562** – 0.701 |

**The distributions overlap.** The worst off-topic question (`how do i apply to Kathmandu
University`, 0.576) outscores two genuine ones (0.562, 0.570). Any threshold that catches
the first also begins refusing real students — and a student turned away with a genuine
question has no recourse, while an off-topic answer costs a few seconds. The asymmetry is
why the gap is accepted and documented rather than closed with a number that would look
better and behave worse.

This is the same negative result the report records for scope adjudication in §4.7.3, from
an independent measurement.

---

## 7. What the suite does **not** establish

Stated plainly, because it is what an examiner should ask:

1. **It is not an accuracy figure.** 69/71 is a pass rate over a curated set built around
   known failure modes. It is not a population-level estimate of how often the assistant
   is right, and no number here should be read as one.
2. **The set is curated, not sampled.** Cases were written from real defects, not drawn at
   random from student questions. It is a regression suite, not a survey.
3. **Only five checks look at the answer text**, and each checks for one figure. Fluency,
   completeness, tone and helpfulness are unmeasured.
4. **No user study.** Every claim is about the system, not about students using it.
5. **Generation is not deterministic.** The evidence assertions are; the five figure
   checks run a language model and are stable at roughly nine runs in ten. A failure there
   is re-run before it is believed.

---

## 8. How to run it

```bash
uv run python -m ioe.eval                 # everything, ~3 minutes
uv run python -m ioe.eval fees            # one group
uv run python -m ioe.eval cutoffs chances # several
uv run python -m ioe.eval figures         # only the answer-text checks
```

Exit status is the number of failures, so it is usable as a gate.

Alongside it, four data modules verify themselves and are run the same way:

```bash
uv run python -m ioe.fees        # 20 published totals re-derived from line items
uv run python -m ioe.seats       # 17 derived totals against the booklet
uv run python -m ioe.cutoffs     # 228 rows, cross-checked against seats.py
uv run python -m ioe.priority    # the code table against seats.py; the simulation's own output
```

Each returns an empty problem list when every derived figure agrees with the published
one. A typo in a fee table fails loudly instead of quietly teaching the assistant a wrong
number.
