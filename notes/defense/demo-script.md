# Sarathi — demo slides script (plain version)

Just slides 10 and 11 — the live demo and its backup — in the simplest words that still
say something real. Each line is what to say out loud; each `[bracket]` is not something
you say, it's you understanding what the slide is actually showing, so a follow-up
question doesn't catch you off guard.

Say the spoken lines in your own words. Don't read them like a script.

Note: slide 11 used to show three *different* questions than slide 10 (an old mismatch
from an earlier draft). That's fixed now — both slides use the same three questions, so
the backup genuinely backs up what you just tried live.

---

## Slide 10 — Live demo

**Say:**

> "Now let's actually see it working. This is the real app, running on this laptop,
> right now — not a recording, not a mockup."

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

## Why bother saying "three different mechanisms" out loud

If a judge asks "isn't this just ChatGPT with your documents attached," this is your
answer in one sentence: `[A plain chatbot would try to answer all three questions the
same way — by guessing from text. Sarathi answers them three different ways on purpose,
because each kind of question has one correct answer, and guessing is the wrong tool for
a question that already has a right answer somewhere.]`
