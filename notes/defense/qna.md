# Defense — question sheet

One page to hold. Every figure below is from the submitted report, with its section, so an
examiner can follow you into it.

---

## The three they are most likely to open with

**"Why not just use ChatGPT?"** — §1.4
It has no access to these notices, and the year-specific facts an applicant needs are
exactly what a language model is least able to recall — so it answers confidently and
wrongly. Sarathi answers only from the indexed notices, names the document, and declines
what they do not cover. It also removes recurring cost, removes a network dependency a
Nepali deployment cannot assume, and keeps queries naming real candidates on the machine.

**"Why retrieval-augmented rather than fine-tuned?"** — §1.4
The corpus is small, closed, authoritative and revised annually — the exact conditions
where RAG beats fine-tuning. The knowledge is external, so next year's cycle is thirteen
replaced documents and a rebuilt index, with no retraining and no code change. And every
answer stays traceable to a notice the student can open.

**"What is the contribution — isn't this just a wrapper?"** — §6.1
The contribution is the principle that organises it: *every quantity a student may act
upon is computed, never generated.* Pass-list membership, fee totals, BS dates and
programme cut-offs are settled in code and handed to the model as authoritative context.
The model writes the sentence around the figure; it never produces the figure.

---

## Corpus and ingestion — §3.6, §4.4.1

**"How large is the corpus?"**
Fifteen source PDFs acquired; thirteen translated notices indexed — 171,402 characters
into **216 chunks**, mean 781 characters, median 828, largest 1,199. Two tabular documents
(the 7,179-row pass list, the 1,700-row priority applications) are transcribed to CSV and
deliberately excluded from the vector index — embedding a table is useless.

**"Why translate at all? bge-m3 is multilingual."**
Retrieval does not need it — the embedding model matches English queries against Nepali
text perfectly well. The *generator* needs it: qwen2.5:7b answers in English and degrades
when it has to translate context while reasoning over it.

**"How do you know the translations are right?"**
We do not claim they are beyond error, and §1.6 lists it as a limitation: a translation
error propagates to every answer from that passage, and the original Nepali PDF remains
authoritative. What we did control: semantic translation with Nepali terms retained in
parentheses, Devanagari numerals converted, **BS dates left unconverted** so the conversion
machinery resolves them rather than the translator, and each document records its own
translation type so reproduced text is distinguishable from translated text.

**"Why 1,200 characters and 150 overlap?"**
Splitting is two-stage: first on the document's own h1/h2/h3 headings, so a chunk carries
its own context, then a recursive character split only for sections still oversized. The
size bound is what keeps a chunk inside the retrieval budget; the overlap keeps a sentence
spanning a boundary retrievable from either side.

---

## Retrieval — §4.4.2

**"Walk me through retrieval."**
Over-fetch 2k candidates for a target of k = 6, so a demoted passage can genuinely be
displaced rather than merely reordered. Then a domain rerank: foreign-applicant documents
are demoted by λ = 0.10 unless the query signals a foreign applicant. Then a relevance
floor τ = 0.45, keeping the best six above it.

**"Why λ = 0.10?"**
Measured, not chosen. Competing passages on a quota question separate by about 0.03, so
0.10 reliably reorders — while staying small enough that a foreign-only document still
surfaces when nothing else matches.

**"Why is the floor so low at 0.45?"**
Because its job is to exclude passages when a question misses the corpus entirely, not to
arbitrate among plausible ones. Measured separation on this corpus is wide: about 0.6
on-topic against 0.3 off-topic.

**"Then why doesn't the floor decide scope?"** — §4.7.3
Because the distributions overlap. In-scope questions scored 0.435–0.700 and off-scope
0.357–0.573, and *"how do I apply to Kathmandu University"* at 0.573 outranks *"how many
seats are there in Pulchowk"* at 0.478. Relevance alone cannot adjudicate scope, which is
why the guard uses three signals and why scope is a node in the graph rather than a
sentence in a prompt.

---

## Results — §5.1

| | |
| --- | --- |
| Scope classification, 39-question probe | 26/39 → **36/39** |
| Off-topic refused / genuine answered, live | 10/10 · 10/10 |
| Bare conversational follow-ups | 8/8 |
| English-only enforcement | 0/4 → **24/24** |
| Published fee totals reproduced | **20/20** |
| Cut-off pairs resolved, 1,647 applicants | **16/16** |

**"Which result are you proudest of?"**
That **reliability came from the pipeline, not the model.** Not one improvement above came
from changing the generator. Scope rose ten points through a change of *framing*; English
enforcement went from 0/4 to 24/24 by *deleting* an instruction rather than strengthening
one; and the single most consequential defect was that the instruction had been silently
discarded all along.

**"Explain the classifier framing result."** — §5.1.3
The same model on the same probe set differed by ten points between framings. "IN or OUT of
scope" scored 26/39 and its error profile was inverted against our cost structure — it
refused 13 of 22 genuine questions. "Could this plausibly be about IOE? When in doubt, say
YES" scored 36/39. A student turned away with a genuine question has no recourse; an
off-topic answer costs a few seconds.

**"Explain the cut-off reconstruction."** — §5.1.7, §2.1.7
IOE admits by walking the merit list from rank 1 and placing each applicant into the best
still-open programme on their own list. That is a serial dictatorship, so given the
published priority applications the outcome is *determined* — we recompute it rather than
estimate it. 1,700 published rows reduce to 1,647 distinct applicants after quota
deduplication; all 624 Pulchowk seats fill, so all sixteen programme–category pairs yield a
cut-off. Computer Regular closed at rank 55, less than half the next programme.

**"Why is Regular always sharper than Full-fee?"**
Empirically true for every programme, and it confirms the ordering advice the system gives:
a Regular seat placed above its Full-fee counterpart costs a candidate nothing, because a
candidate who does not reach Regular still falls through to Full-fee at the same rank.

---

## Challenges — §4.7

**"What was the hardest bug?"**
The system instruction was being discarded. No context window was specified, so the runtime
served 4,096 tokens against a grounded prompt of 5,318 — 2,131 of it the instruction
itself. Overflow is dropped silently and the instruction, being first, goes first.
Confirmed directly rather than inferred: an 8,040-token probe evaluated 2,050 tokens and
answered from the filler; the same prompt at 8,192 evaluated 8,037 and answered correctly.

**"Why 16,384 and not 8,192?"**
8,192 costs less VRAM — 4.99 GB against 5.47 GB of 8.19 GB — but leaves too little slack
against the worst-case prompt, and silent truncation is the failure being fixed. The
constant is applied to *every* model client in the process, because the window is a
load-time option: two clients disagreeing makes the runtime hold two model instances, and
two do not fit on an eight-gigabyte card.

**"Why strip the language request instead of instructing the model?"**
Four prompt formulations were tried and each failed differently. The pattern common to all
four is that naming the request in the prompt is what keeps it alive. So the request is not
named — it is removed from the question, and the application emits its own fixed sentence.

---

## Limitations — §1.6, §5.2.2

Corpus currency (a snapshot; newer notices are visible as listings only) · translation
dependency · model capacity at seven billion parameters · computation covers Pulchowk,
whose fee schedule alone is published in full · no authentication, the browser identifier
is not a security boundary · latency in seconds, not milliseconds · **evaluation scale —
curated probe sets of tens of questions; no figure is a population-level accuracy
estimate, and no user study was conducted.**

Say these before you are asked. They are in the report; owning them reads as rigour.

---

## Demo runbook

Before starting: `docker compose up -d --build`, Ollama running, then open the deck and
check slide 10 loads the app.

1. What documents do I need for the women's quota? → ordinary retrieval, the project's core
2. Did form 2083-4001 pass? → exact lookup: rank 1, Manan Shrestha, Morang
3. What was the cutoff for Civil at Thapathali? → 387, 2082 first list

If anything fails, **press → once**. Slide 11 replays all three with citations and you keep
talking. Do not improvise a fourth question live.
