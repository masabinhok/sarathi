# Defense — the questions, and the answers

One page to hold. Not slides. Each answer is one or two sentences; the numbers are all real
and all reproducible from the repo.

---

## The one they will actually ask

**"Did you just wire up an LLM?"**

No, and the deck is arranged to answer this before it is asked. The model chooses which
evidence a question needs; the *application* decides what reaches the prompt and in what
order, and there is a deterministic floor underneath so total tool-selection failure
degrades to the previous pipeline rather than to nothing. Most of the figures a student
acts on are computed in Python and asserted against the published notice — the model
writes the sentence around them.

---

## Method and correctness

**"How do you know the answers are correct?"**
Two independent layers. The data checks itself — every total is derived from line items
and asserted against what the notice printed, and all 228 cutoff rows are cross-checked
against a seat table transcribed by a completely separate route. And the 66-case suite
asserts *which evidence reached the model*, which is a fact rather than a judgement.

**"Why not test the answers themselves?"**
Because that needs a judge, and a judge needs golden answers that go stale every admission
cycle. Whether the worked fee figures were in front of the model is checkable in
milliseconds and is the thing that actually breaks. We do read answers by hand too — the
Nepali translation bug was found that way, not by the suite.

**"What are the two failures?"**
The same weak-evidence gap both times: an off-topic question finds a plausible-looking
document and gets answered instead of declined. Measured — off-topic questions score
0.357–0.576 against the corpus, genuine ones 0.562–0.701. The distributions overlap and
the worst off-topic beats two real questions, so no threshold separates them. Raising it
would start refusing real students.

**"Why RAG rather than fine-tuning?"**
The corpus changes every cycle, so fine-tuning means retraining every year — and it still
could not cite a source. Retrieval also fails *visibly*: you can see that nothing matched.
A fine-tuned model fails silently and fluently.

---

## Design

**"What is actually novel here?"**
Not the retrieval. It is that tool results never reach the answering model directly — the
app re-renders them into blocks in a fixed order it controls. With a 7B model whatever
sits nearest the question wins, and letting tool-call order decide placement means letting
the model decide it. Placed ahead of the retrieved documents, the worked fee block was
ignored and the model went back to the raw tables and multiplied them itself.

**"Why a local model? Wouldn't a bigger one be better?"**
Better, yes; available, no — and the constraint is what produced the architecture.
`qwen2.5:7b` scored 7/8 on a tool-calling probe and `gemma3` advertises no tool capability
at all, so everything the model cannot be trusted with is done in code. Also: no
per-student cost, works without internet, and no candidate's result ever leaves the
building.

**"Why LangGraph and not a plain loop?"**
We deliberately did not use the prebuilt agent. `bind_tools(tool_choice=...)` is a no-op on
Ollama, so a tool call cannot be forced — "retrieval always runs" is inexpressible inside
that loop. The graph is hand-built for exactly that reason.

---

## Data

**"Your cutoff data comes from a third-party site."**
It does. That site states each figure is recalculated from the campus-published admission
lists, and links them — those primary lists are what our citations point at. 214 of 228
rows carry one; the remaining 14 are left empty rather than given a wrong citation.

**"What happens when a source website changes?"**
Each of the seven has its own small parser and its own error entry, so one site breaking
degrades that source and leaves the rest intact. Two of the seven were unreachable until
their admission portals exposed feeds — the code comment saying so is now deleted.

**"How do you keep the corpus current?"**
Notices are re-scraped in the background. Extracting their text is automatic; *publishing*
it is not — extraction stops at a review queue and a person approves before anything is
indexed. A wrong figure in the corpus is a student paying the wrong amount.

**"Isn't scraping fragile / is it allowed?"**
`robots.txt` permits it, we fetch listings only, and the cache is read at request time so
the app never depends on a third-party site being up mid-conversation.

---

## Scope and safety

**"How do you stop it giving wrong admission advice?"**
Chances are stated as a count of years — "cleared in 2 of the 4 recorded years" — never as
a percentage, never "safe", and always with the statement that nobody can guarantee a
place. The system prompt forbids producing a cutoff from anywhere but a cutoff block, and
forbids comparing a rank against a seat count.

**"What if it doesn't know?"**
It says so. That is a designed path, not a fallback — when no source matches, the app
tells the model the evidence is empty rather than letting it improvise.

**"Could this be extended to other institutions?"**
The retrieval, notice, extraction and evaluation layers are institution-agnostic. Fees,
seats, cutoffs and priority encode IOE's published rules and would be rewritten per
institution. That split is deliberate.

---

## If pushed

**"Why should we believe the measurements?"**
Every one is reproducible from the repo: `uv run python -m ioe.eval`, and each module's
`verify()` runs from its own `__main__`. The project log records the failures as well as
the fixes — including three occasions where a claim we had written down turned out to be
contradicted by the data and was corrected.

**Numbers to have ready, but do not volunteer:**
6,660 lines of Python · 2,652 of TypeScript · 217 indexed chunks · 7,179-row pass list ·
228 cutoff figures · 1,701 priority applications · 9 tools · 11 ordered blocks ·
56 commits · 32 tracked issues, 28 closed.

---

## Demo runbook

Before you start: `docker compose up -d --build`, then open the deck and check slide 4
loads the app. Ollama must be running.

1. How many computer engineering seats does Pulchowk have? → **36 Regular / 60 Full Fee**
2. Did form 2083-4001 pass? → **yes, rank 1, Manan Shrestha, Morang**
3. What was the cutoff for Civil at Thapathali? → **387, 2082 first list**

If anything fails, press **→ once**. Slide 5 replays all three with their citations and you
can keep talking. Do not improvise a fourth question live.
