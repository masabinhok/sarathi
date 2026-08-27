# Sarathi — full defense script (plain version)

Slides 1 through 16, in the simplest words that still say something real. Each spoken
line is what to say out loud — say it in your own words, don't read it like a script.
Each `[bracket]` is *not* something you say — it's you understanding what the slide is
actually showing, so a follow-up question doesn't catch you off guard.

This is the "say this in front of a judge" version. `script.md` (repo root) has the
denser, more technical version of slides 9–17 if you want to go deeper on any point.

---

## Slide 1 — Title

**Say:**

> "Good [morning/afternoon]. I'm Sabin, this is Sachin. Our project is called Sarathi —
> that's Nepali for 'the charioteer,' the one who steers you where you're going. It's an
> assistant that answers the confusing logistics around IOE's entrance exam and admission
> process — fees, seats, results, deadlines — using only the university's own official
> notices, running entirely on our own hardware."

`[Left side is the date in Bikram Sambat with the English date under it, the way the real
notices date themselves. The big word is the project name; the Devanagari underneath it
is the same word written in Nepali script, since the product itself is bilingual. Below
that is one sentence saying what it does. The three columns at the bottom name the two of
us, our supervisor, and our department. The bottom-right line — "qwen2.5:7b + bge-m3,
runs entirely on local hardware" — is worth remembering: it means no OpenAI, no cloud API,
nothing leaves this laptop.]`

---

## Slide 2 — The problem

**Say:**

> "Every year, thousands of students sit the IOE entrance exam. Everything they need
> afterward is published somewhere, officially. The problem isn't that it's missing — it's
> that it's scattered across six different notice boards, mostly in Nepali, dated in the
> Bikram Sambat calendar, and often distributed as scanned PDFs you can't even search or
> copy text from. So people ask general AI chatbots instead, and those chatbots answer
> confidently — and wrongly — because a fee, a deadline, or a seat count is exactly the
> kind of specific fact a language model is worst at remembering. And the cost isn't
> symmetric: get a coding question wrong and you lose ten minutes; get a deadline wrong
> and you lose a year."

`[Four rows on this slide, each making one point: information is scattered across six
boards; it's not in a format you can read or search; general chatbots fill that gap
confidently but wrongly; and the two red ("warn") rows are there on purpose — red is this
deck's color for consequences, so those two rows are the ones you should actually slow
down on if a judge looks up.]`

---

## Slide 3 — Objectives

**Say:**

> "So our goal was to build an assistant that answers accurately, always says where an
> answer came from, and knows the Nepali academic calendar — and to do it running entirely
> on hardware we control, not a cloud API. Four concrete pieces: build and translate the
> official notices into something searchable; answer exact-number questions like fees and
> results by computing them, not guessing at them; always cite the source document; and
> ship it as an actual working website, then measure whether it does what we set out to
> do."

`[This is the "what we promised to build" slide, straight after the "here's the problem"
slide — it exists so a judge can later check the results slide (14) against this one and
see whether we did what we said. The four ruled rows are the four objectives; nothing here
needs defending in detail, it's a checklist you'll come back to.]`

---

## Slide 4 — Scope

**Say:**

> "To keep this achievable, we scoped it to one admission cycle — this year's, 2083 BS —
> and one institution, IOE, covering both the Bachelor's in Engineering and in
> Architecture. Inside that, it answers the general questions — eligibility, fees, the
> exam itself — from thirteen official notices. And on top of that, we built four things
> that go beyond just answering questions from text: exact result lookup, fee computation,
> a historical look at admission cut-offs, and a live feed of new notices."

`[Left column is what "the core" covers — thirteen indexed notices, the everyday
questions. Right column is the four capabilities that go beyond just reading documents —
these are the things this project actually computes rather than retrieves, and they're
what makes this more than "ChatGPT plus some PDFs."]`

---

## Slide 5 — Corpus and ingestion

**Say:**

> "The starting material is fifteen official PDFs, many of them scanned images in Nepali.
> We translate them into English by hand — carefully, meaning-for-meaning, not
> word-for-word — split them into small pieces, and load those pieces into a searchable
> database. That gives us 216 searchable passages. Two documents don't go through this
> pipeline at all: the results list and the priority-form data, because those are tables,
> not paragraphs, and a table doesn't belong in a search index — it belongs in a
> spreadsheet-style lookup, which is a separate part of the system."

`[The five boxes across the middle are the actual pipeline, left to right: the original
scanned PDF, our hand-translated Markdown version, split by headers, split again by size,
then loaded into the search database (Chroma) using an embedding model called bge-m3.
"216 passages" is the final count of searchable chunks. The two callouts below explain why
translation is done carefully — dates are deliberately left unconverted so the date-math
code handles them, not a human translator making an error — and why the results list
(7,179 rows) and priority data (1,700 rows) are kept out of the search index entirely and
handled as exact-lookup tables instead.]`

---

## Slide 6 — How retrieval works

**Say:**

> "Three small decisions between the question and what actually reaches the model. First,
> we fetch more results than we need, so a bad early match can genuinely get pushed out
> by a better one later — not just re-ranked. Second, documents meant for foreign
> applicants get slightly deprioritized unless the question is clearly about a foreign
> applicant, because we measured how close together the competing scores are and tuned the
> penalty to just barely outweigh that gap. Third, there's a relevance cutoff — if nothing
> in the database is actually close enough to the question, we don't force an answer out of
> the nearest thing anyway; we say the question is off-topic."

`[Three ruled rows, each with a number: "2k for k=6" means fetch twice as many candidates
as we'll actually use; "λ = 0.10" is the size of the foreign-applicant penalty, chosen
because real score gaps on quota questions were measured at about 0.03, so 0.10 reliably
wins without permanently hiding the foreign-only document; "τ = 0.45" is the relevance
floor, set well below the real on-topic score band (~0.6) and the off-topic band (~0.3),
so it only fires when a question is genuinely unrelated to anything in the corpus.]`

---

## Slide 7 — Architecture

**Say:**

> "Under the hood this isn't one long prompt to the model — it's a graph, a fixed sequence
> of separate steps: normalize the question, decide what evidence to pull in, compute
> anything that needs computing, assemble it all in order, then generate the actual
> sentence. Because each step is separate, we could test and fix each one on its own —
> which is exactly how we found and fixed the bugs on the next two slides."

`[The row of boxes is the graph itself, read left to right — question comes in, gets
normalized (spelling/language cleaned up, translated if needed), then evidence gets
selected (either searched for or looked up exactly), computed (fees, dates, ranks worked
out), assembled into an ordered block of context, then the model generates the final
answer from that block. The three notes below it call out three side-paths: an
off-topic question gets refused by an actual step in the graph rather than a hopeful
instruction in the prompt; small talk skips the whole search process and answers in under
a second; and citations are taken from what was actually retrieved, decided before the
model even starts writing.]`

---

## Slide 8 — Computed, not generated

**Say:**

> "This is the core design idea of the whole project: any number a student might actually
> act on is never something the model generates — it's computed by our code and handed to
> the model as a fact it's not allowed to change. Results are an exact table lookup. Fees
> are added up from the real published line items and checked against the printed totals.
> Calendar dates are converted before the prompt is even built, so the model never does
> date math. And admission cut-offs are reconstructed by actually simulating the
> university's real seat-allocation rule, not guessed at."

`[Four ruled rows, each a category of "thing the model is not trusted to produce":
7,179-row result list looked up by form number, rank, name, or district; fee totals summed
from line items and checked against the officially printed number before ever reaching the
model; Bikram Sambat dates converted in code, not by the model; and cut-off ranks
reconstructed by simulating the actual serial-dictatorship allocation rule IOE uses. The
sentence at the bottom is the whole point of the slide: the model's only job is the
sentence *around* the number, never the number itself.]`

---

## Slide 9

`[This slide is currently commented out in the deck — it's not shown in the live
presentation, so there's nothing to say for it. If it gets re-enabled later, it covers the
same four extra capabilities as slide 4's right column, in more depth.]`

---

## Slide 10 — Live demo

**Say:**

> "Now let's actually see it working. This is the real app, running on this laptop, right
> now — not a recording, not a mockup."

`[This slide has two halves. The left/center box is a real, live, working copy of the
website embedded directly in the slide — you can literally click into it and type,
because it's the actual app, not a picture of it. The right side just lists the three
questions you're about to ask it, in order, so you don't forget them mid-sentence.]`

Type each question into the box, and pause after each answer long enough for the judges
to actually read it before moving on.

### Question 1 — "help me fill the priority form"

**Say:**

> "First — the priority form. This is the form every student fills out to choose which
> course and which campus they want, in order of preference."

`[When it answers, watch for the rules about "priorities." This isn't the model making up
advice — it's reading out the campus's own official rule sheet, word for word. The one
rule worth pointing at if it comes up: a student who lists a program they don't actually
want, gets offered it, and turns it down is removed from the whole process — they don't
get a second chance at their other choices. That's the "trap" the real notice warns
about, and the app repeats it exactly rather than summarizing it wrong.]`

### Question 2 — "what courses are offered in pulchowk campus and what are the seats available"

**Say:**

> "Next — how many seats are actually open, per course, at Pulchowk."

`[This answer isn't found by searching through a paragraph somewhere — it comes from a
seat table we built directly into the program's code, copied from the official admission
booklet. So there's no chance the model misreads a sentence and gets a seat count wrong;
the numbers are just looked up, like a spreadsheet.]`

### Question 3 — "what is the fee at ioe, for both regular and full fee"

**Say:**

> "Last — the fee. Notice I asked for both categories in one sentence, on purpose."

`[This one used to be a real bug we had: the app would only answer for one fee category
and ignore the other half of the question. It's fixed now — the app reads "regular and
full fee" out of your sentence and works out both totals separately, so you get two
correct numbers instead of one number that might be for the wrong category.]`

**If anything glitches — frozen screen, no internet, container not running:**

> "Let me show you what this looked like when we ran it earlier."

Move straight to slide 11. Don't stop to debug live.

---

## Slide 11 — Backup replay

**Say:**

> "Here's the exact same three questions, already answered and saved, in case the live
> version has any hiccup — same questions, same real answers."

`[This slide is not live. It's a captured replay — real text from a real run of the app,
typed back out with a small blinking cursor so it still feels like it's happening now.
The numbers on it are the true, correct numbers; nothing here is invented for the
slide.]`

**Priority form answer** — `[16 total priority slots, because Pulchowk's 8 courses each
appear twice: once as "Regular" price, once as "Full Fee" price. The "excluded entirely"
line is the one worth repeating out loud if a judge looks confused — it's the part
students actually get tripped up by in real life.]`

**Seats answer** — `[Straight numbers, Regular seats first then Full Fee seats, for every
course at Pulchowk. Computer Engineering is the one most students ask about: 36 Regular,
60 Full Fee.]`

**Fee answer** — `[Two totals side by side: what a Regular student pays for the whole
degree (72,287) versus a Full Fee student (591,632) — and separately, what's due
immediately on the day of admission for each. These four numbers are all independently
checked in our code against the university's own published fee sheet, so they can't
quietly drift out of date without us noticing.]`

**Say, closing:**

> "So — one question the app pulled a real rule from a document, one it looked up in a
> table, and one it computed a total for. Three different ways of getting a correct
> answer, none of which is the model just guessing."

---

## Slide 12 — Challenges I

**Say:**

> "Two of our hardest bugs, and in both cases the obvious symptom wasn't the real cause.
> First: for a while, the rules we'd carefully written into the model's instructions
> seemed to just stop working, and it started inventing course names that don't exist. It
> turned out we'd never told the system how much text it was allowed to read at once, so
> it silently cut off the earliest part of the prompt — which is exactly where our
> instructions lived. One number, set correctly, fixed a whole category of made-up
> answers.
>
> Second: ask it to answer in Nepali, and it would reply in a mix of Hindi and Nepali;
> ask a question in Nepali, and it would invent syllabus content. We tried four different
> ways of phrasing the language instruction inside the prompt, and every single one failed
> differently — because just naming the language request inside the prompt is what kept
> confusing it. The fix was to not name it at all: we strip the language request out of the
> question ourselves and answer with a fixed sentence instead of asking the model to
> decide. That took it from failing every time to passing 24 out of 24."

`[The two red rows on this slide are structured the same way each time: symptom, then
cause, then fix. First bug — "context window" is just the amount of text a model can look
at in one go; ours defaulted to 4,096 tokens (a token is roughly a word-and-a-half) while
our real prompts needed 5,318, so the overflow silently got dropped — and because the
system prompt goes in first, it's what got cut off first. We proved this with a controlled
test before fixing it. Second bug — the fix for the language problem is a good story for a
judge, because it's not "we tried harder," it's "we stopped asking the model to do the
part it was bad at."]`

---

## Slide 13 — Challenges II

**Say:**

> "Two more. A student asked about holiday planning — completely unrelated to admissions —
> and the app answered with a bizarre planning questionnaire. Then every question after
> that came out wrong too, which looked like a separate memory bug. It wasn't — it was the
> same bug. Once that odd questionnaire was sitting in the conversation history, every
> question after it got compared against that instead of against the real admission
> documents. The fix was to make 'is this question even about admissions' its own explicit
> step in the pipeline, not just a hopeful instruction in the prompt.
>
> Second: we'd ask for a total across eight semesters and it would start multiplying and
> just trail off mid-sentence; ask what's refundable and it invented an entire refund
> policy that doesn't exist anywhere in our documents. Retrieval was working fine — the
> actual arithmetic inside the model was the problem. So now every fee total the app could
> possibly need is pre-computed and checked in advance. The model reads a number off a
> line; it never adds anything itself."

`[Same symptom → cause → fix structure. The "bahamas" example (the actual follow-up
question that broke it) is a good one to have ready verbatim if a judge asks for a
concrete example — it makes the bug feel real rather than abstract. The second bug is the
same principle as slide 8, just discovered the hard way: never let the 7-billion-parameter
model do arithmetic when code can do it exactly instead.]`

---

## Slide 14 — Results

**Say:**

> "Here's what we actually measured, against the exact failures we just described. Scope
> classification — telling an admissions question apart from an unrelated one — went from
> 26 out of 39 to 36 out of 39. Off-topic questions get correctly refused 10 out of 10
> times live, and genuine questions get correctly answered 10 out of 10 times live.
> Bare conversational follow-ups — 8 out of 8. Language enforcement went from 0 out of 4 to
> 24 out of 24. All 20 published fee totals reproduce exactly, and all 16 cut-off pairs
> across 1,647 real applicants resolve correctly.
>
> But the finding that actually matters more than any single number: not one of these
> improvements came from making the model itself smarter. They came from changing how we
> feed it information, or from taking a decision away from it entirely and doing it in
> code."

`[This table is the answer to "did you just wire up an LLM and call it a project" before
anyone asks it. Every row on the left is a number that got better, and the column on the
right explains why: not model upgrades, but pipeline changes — better framing for scope,
deletion (not addition) of an instruction for language, and one silently-wrong setting
found and fixed for the context window bug. That's the sentence to have ready if pressed:
"reliability came from the pipeline, not the model."]`

---

## Slide 15 — Limitations

**Say:**

> "We want to be upfront about what this doesn't prove. It's a snapshot of this year's
> admission cycle — a notice published after we built the index isn't read, only listed as
> existing. The system reads English translations of the original Nepali documents, so a
> translation mistake would carry through to every answer built on it — the original
> Nepali PDF stays the actual authority. And our test sets are tens of questions, sized to
> the specific bugs we were chasing, not a large-scale accuracy study.
>
> On top of that: it's a 7-billion-parameter model on a single consumer GPU, which is a
> real capacity ceiling. Fee and priority computation is detailed for Pulchowk campus only,
> since that's the campus whose full schedule is public. And there's no login — each
> browser gets its own separate conversation, which keeps histories apart, but it is not a
> real security boundary."

`[Six honest limitations, split into "what the results don't prove" on the left and
"other known gaps" on the right. Say these plainly and don't undersell them — owning
limitations before being asked is worth more in a defense than being caught not knowing
one. None of these are surprises if a judge asks a follow-up; they're already written down
here.]`

---

## Slide 16 — Conclusions

**Say:**

> "Three things we'd want you to take away. First — the messy, scattered, scanned-PDF
> corpus problem is actually solvable: thirteen documents, translated once with a record
> of how, turn into 216 passages that answer this whole domain, and next year's cycle just
> means swapping in new documents, not rewriting code.
>
> Second — the questions that actually matter to a student, the ones with a real
> consequence if wrong, aren't retrieval problems at all. They have one correct answer, and
> exact lookup and computation can prove that answer is correct — all twenty fee totals,
> all sixteen cut-off pairs.
>
> And third, the one we keep coming back to: every improvement we made came from the
> pipeline around the model, never from the model getting smarter. For future work, we'd
> want to extend the fee and priority computation to the other campuses, actually fetch and
> read full notice text rather than just list that a notice exists, and run a real user
> study during a live admission cycle."

`[Three ruled rows are the three conclusions, in the same order as the "say" above. The
"Future work" line at the bottom is worth having ready in case a judge asks "what would
you do with more time" — it's already answered here, so you don't need to invent an answer
on the spot.]`

---

## Why bother saying "three different mechanisms" out loud

If a judge asks "isn't this just ChatGPT with your documents attached," this is your
answer in one sentence: `[A plain chatbot would try to answer all three questions the
same way — by guessing from text. Sarathi answers them three different ways on purpose,
because each kind of question has one correct answer, and guessing is the wrong tool for
a question that already has a right answer somewhere.]`
