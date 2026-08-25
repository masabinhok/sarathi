# Issues

Numbers are permanent. Issue 14 stays 14 forever, even after it is closed — that is how
they get referred to in conversation ("fix 18", "answer 13"). New issues go on the end of
the open list and take the next free number.

| Status | Meaning |
| --- | --- |
| `OPEN` | Still to do. |
| `FIXED` | Done, verified. |
| `BUILT` | A question that turned into a feature; the decision record is kept with it. |
| `SATISFIED` | Good enough; not being chased further. |

### Open — 4

| # | Issue | Area |
| --- | --- | --- |
| [4](#4--kv-cache) | KV cache | backend |
| [8](#8--rethink-the-apps-scope) | Rethink the app's scope | product |
| [9](#9--guide-the-bot-to-answer-smartly) | Guide the bot to answer smartly | prompt / graph |
| [10](#10--play-with-the-bot-and-fix-what-breaks) | Play with the bot and fix what breaks | prompt / graph |

### Closed — 19

| # | Issue | Status |
| --- | --- | --- |
| [1](#1--fixed--it-cannot-answer-a-rank-question) | It cannot answer a rank question | `FIXED` |
| [2](#2--fixed--it-does-not-know-todays-date) | It does not know today's date | `FIXED` |
| [3](#3--fixed--the-ui-should-feel-like-an-institution-not-a-demo) | The UI should feel like an institution, not a demo | `FIXED` |
| [5](#5--fixed--add-citations) | Add citations | `FIXED` |
| [6](#6--fixed--support-markdown-in-answers) | Support markdown in answers | `FIXED` |
| [7](#7--satisfied--ui-rework) | UI rework | `SATISFIED` |
| [11](#11--fixed--chat-history-sidebar-three-independent-scrolls) | Chat history sidebar, three independent scrolls | `FIXED` |
| [12](#12--fixed--cite-only-what-was-actually-used) | Cite only what was actually used | `FIXED` |
| [13](#13--built--should-we-add-an-internet-search-tool) | Should we add an internet search tool? | `BUILT` |
| [14](#14--fixed--a-refresh-re-asks-the-question) | A refresh re-asks the question | `FIXED` |
| [15](#15--fixed--the-three-column-layout-does-not-fill-the-page) | The three-column layout does not fill the page | `FIXED` |
| [16](#16--fixed--add-a-theme-colour) | Add a theme colour | `FIXED` |
| [17](#17--fixed--scrolling-up-mid-answer-yanks-you-back-down) | Scrolling up mid-answer yanks you back down | `FIXED` |
| [18](#18--fixed--the-streaming-answer-hides-under-the-composer) | The streaming answer hides under the composer | `FIXED` |
| [19](#19--fixed--it-answers-in-hindi-when-asked-for-nepali) | It answers in Hindi when asked for Nepali | `FIXED` |
| [20](#20--fixed--the-theme-colour-barely-shows) | The theme colour barely shows | `FIXED` |
| [21](#21--fixed--the-pass-list-lookup-only-took-a-form-number-or-a-rank) | The pass list lookup only took a form number or a rank | `FIXED` |
| [22](#22--fixed--it-answers-questions-outside-its-scope-and-then-loses-the-thread) | It answers questions outside its scope, and then loses the thread | `FIXED` |
| [23](#23--fixed--it-gets-the-fee-arithmetic-wrong) | It gets the fee arithmetic wrong | `FIXED` |

---

# Open issues

## 4 · KV cache

kv cache

## 8 · Rethink the app's scope

remove unnecessary things, keep things that adds value, rethink on app's scope, extend to
other campus or be limited to pulchowk, add more information to make the bot more robust

## 9 · Guide the bot to answer smartly

Guide the bot to answer smartly to answers

> Standing note: prompt rules do not hold reliably on `qwen2.5:7b`. Both this and 10 most
> likely need a deterministic guard node in the graph — for scope and for rank prediction —
> rather than another paragraph in `SYSTEM_PROMPT`.

## 10 · Play with the bot and fix what breaks

play around with the bot for flaws and fix it.

Known live flaws, none fixed:

- Out-of-scope questions get answered instead of refused. Asked when Kathmandu University
  holds its entrance exam, it gives IOE's date as KU's.
- It will describe what a notice *says* from the title alone, which the notice-feed prompt
  rule explicitly forbids ("The block gives titles, not contents").
- Citation gating is inconsistent for notice records: a short record shares few distinctive
  terms with an answer, and `MIN_SHARED_TERMS = 4` rejects it. Same kind of question, 2
  sources one time and 0 the next.
- "Any new notice this week" under-reports — it listed only the two published that day and
  said there were no others, with three more inside the week.

---

# Closed issues

## 1 · `FIXED` · It cannot answer a rank question

when i ask for rank it can't answer it: but the csv contains rank:form_no,rank,name,gender,district,sno,remarks: its response

```
To provide you with accurate information, I would need the specific form number of the candidate who scored rank 13 in the 2083 entrance examination. The pass list lookup functionality allows us to verify this directly from the published results.

If you have the form number or any other details, please share them so I can perform a pass list lookup for you. If you do not have the form number, visiting the IOE website at [https://entrance.ioe.edu.np](https://entrance.ioe.edu.np) might help you find this information.

If no specific form number is provided, I cannot determine who scored rank 13 based on the available data. Please let me know if you have any additional details or if there's another question I can assist with.
```

## 2 · `FIXED` · It does not know today's date

it is unsure about today'date and hallucinates and gives fake dates both in english and nepali (bs and ad) we might need to add a date tool so it knows today's date and can answer question based on inferencing date: like it already happened, its in this much days. (i dont mean it should say it in every answer, just a capability for our rag bot) a date tool

```
what is today s date
Today's date in Nepal is **2083 Shrawan 9 (2026-07-15)**.

If you need this information for a specific application or process, it's always a good idea to verify with the official IOE website or the entrance examination board.
```

## 3 · `FIXED` · The UI should feel like an institution, not a demo

the ui should be more similar to government websites or ioe/tu/pcampus website, a formal educational institutioal vibe. i think the ui should be more welcoming. yeah the chabot is the main attractino but, we should display relevant notices from all sites, like tu, ioe, pcampus, other contituent campus, exam.ioe.edu.np, also think of adding other features to the app that makes it feel like a real product instead of just a ragbot. (admin side where they can upload the tranlsted docuemjtns, and it goes stays there where he can update the bot from the ui? is it possible???)

## 5 · `FIXED` · Add citations

add citations

## 6 · `FIXED` · Support markdown in answers

support markdown formatting in answers

## 7 · `SATISFIED` · UI rework

ui rework

## 11 · `FIXED` · Chat history sidebar, three independent scrolls

add a chat history on the left sidebar, make all three divs seperatly scrollabale, chat, notices and chat-history !

## 12 · `FIXED` · Cite only what was actually used

include valid citations only, citations for relevant questions and not for out of scope questions, not necessary to mention 4 sources always, just mention where its from.

## 13 · `BUILT` · Should we add an internet search tool?

should we add internet search tool? if added what should it use internet for, because we have to provide relevant information from our own docuemnt chunks, what usefulness will a internet search tool have?

**No general web search. Yes to a notice-fetch tool over the sites we already scrape.**

Measured against the live bot on 2026-08-23:

- Asked "is there any new notice published this week", it answered "there is no new
  official notice published specifically for this week" — while the rail beside it
  was showing one published the day before. 35 notices in cache, newest 2026-08-22.
  `notices.py` already scrapes 4 sites; `graph.py` simply cannot see the cache. Not
  an internet gap.
- Asked the fee for BE Civil at Thapathali, it punted to a link. Section 9 of the
  booklet answers it — the fee table is IOE-wide, not per-campus (Regular NPR
  6,974/sem, 55,792 over 8 semesters). Search would have hidden a retrieval bug
  behind a plausible web answer.
- Asked when Kathmandu University holds its entrance exam, it gave IOE's date as
  KU's. Search would turn that from wrong-and-ungrounded into wrong-with-a-citation,
  which is exactly what the citation gate in 12 exists to prevent.

So the tool to build is a fetch, not a search:

a. Index the *bodies* of the notices we already list, not just their titles. Bounded
   set, known domains, authoritative. Closes the "no new notice" lie.
b. Sources to cover every constituent campus, not just Pulchowk — Thapathali,
   Purwanchal, Pashchimanchal, Chitwan — since the question is about admission and
   admission happens at all of them. More sources to be added over time.
c. Refresh on demand during a chat when the cache is stale, rather than waiting for
   the daily cron: a student asking at 4pm about a list published at 2pm should get
   it. Cron stays as the floor, the chat path can trigger a fetch above it.
d. A staleness guard: let the bot compare the newest notice against its own document
   set and say "6 notices are newer than my documents, here they are" instead of
   denying they exist.

Open web search stays out. The product's promise is that answers come from the
official notices; a general search tool dissolves that promise, and the honest
failure mode of a grounded bot ("I don't have that") is worth more than a confident
answer from a source nobody vetted.

**Built 2026-08-23.** One change to the plan, forced by measurement: (a) indexes the
notice *record* — title, both dates, publisher, link — not the notice page. Sampling
one page per source, every one was a heading over a scanned PDF; the richest held 209
characters, most of it "Click Here" and "in pdf format". Indexing that would have put
site chrome into the index to compete with the translated documents, at one HTTP
request per notice. Worth revisiting only if a source starts publishing real HTML.

Sources went from 4 to 6: added Pashchimanchal (wrc.edu.np) and Purwanchal
(ioepc.edu.np). Thapathali renders its notice list in the browser — its served HTML
contains no notice at all — so it needs a headless browser, which is not worth a
dependency yet. Chitwan publishes no feed and links to tu.edu.np, already a source.
Note that cec.edu.np is *not* Chitwan Engineering Campus; the campus is cec.tu.edu.np.

Result: 57 notices from 6 sources, 57 records indexed. "Is there any new notice this
week" now lists today's two with links instead of denying they exist.

**Two things this build left broken, found and fixed on 2026-08-23 while working on 20.**
`Notices.tsx` filtered its source chips through a hardcoded `SOURCE_ORDER` of the
original four, so Pashchimanchal and Purwanchal notices were listed but not filterable;
that list now carries all six and says in a comment that it must be extended alongside
`SOURCES` in `notices.py`. And the landing, notices and about pages all still said four
sites in prose — "Four campuses publish to four websites" and the like. Adding the two
extra chips also squeezed the notice search field to four characters wide at 1440, so
the filter row now always takes a line of its own.

## 14 · `FIXED` · A refresh re-asks the question

there is a bug, whenever i refresh, the latest query reruns again. its because user query is passed through search params, which is why! it's not the case in major chatbots, how do they handles this, and can we move to that system to fix this bug! also creating new chat history every time i refresh for the same question.

## 15 · `FIXED` · The three-column layout does not fill the page

i kinda don't like the current 3 layout strcutre, we can expand the chat window a little and push the notiecs to right, and without the limiting right border.(the left margin is the sweet spot, we should expand the second layer so that, the right margin equals left margin for the outer container that contains three layers(chatbot, history and notices, and remove the right border from the notices))

## 16 · `FIXED` · Add a theme colour

Let's add one theme color, it looks so off with just black and white

Crimson keeps its existing job — elapsed or imminent state, nothing else. Lapis was added
beside it for the interactive layer only: links, the send button, the conversation you are
in, whatever holds focus. See 20, which asks for more of it.

## 17 · `FIXED` · Scrolling up mid-answer yanks you back down

bug: when it's generating an answer, an i scroll up, it goes back to the answer streams, which is kinda bad ux. fix it!

## 18 · `FIXED` · The streaming answer hides under the composer

issue 17 fixed but created a new error: answer doesnot stream properly or not visible, becuase its stuck and the page doesnot auto scroll to bottom while the answer is generating, the user themself has to do it.

Caused by the 17 fix. `scrollIntoView({block:"end"})` aims at the foot of the scrollport,
which the sticky composer sits over; both the follow scroll and the "still reading" test now
measure against the composer's own top edge.

## 19 · `FIXED` · It answers in Hindi when asked for Nepali

when i asked it to speak in nepali, it started talking in hindi. so we should strictly make
the bot speak in english only. it is incapable of speaking other languages properly.

Confirmed against the live bot before touching anything, and worse than reported. All four
probes switched: asked to reply in Nepali it wrote 762 Devanagari characters, half of them
Hindi; asked in Nepali with no instruction at all it answered in Nepali *and invented
syllabus subjects*; asked for Hindi it answered in Hindi. The rule existed — one bullet,
sixty lines into `SYSTEM_PROMPT` — and `qwen2.5:7b` never looked at it.

Four rounds of prompting could not fix it, each failing differently:

| attempt | result |
| --- | --- |
| the buried bullet, as shipped | 0/4 English |
| hoisted `Language:` section, "refuse then answer" | wrote the refusal *in Nepali* |
| "copy this exact sentence, then answer" | 12/12 English, 3/12 sent the sentence and nothing else |
| "the refusal is handled, ignore the request" | 6/18 — straight back to Nepali |

The pattern across all four is that naming the request in the prompt is what keeps it
alive. So it is not named any more. What runs instead is deterministic:

- **The request is stripped from the question.** A language name alone does not count —
  it takes a language *and* a speech verb, so "is the exam set in Nepali?" survives.
- **If stripping would leave nothing, nothing is stripped.** "Can I answer the exam paper
  in Nepali?" reads as a request by every test, but it *is* the question, so it gets the
  ordinary treatment. Verified: answers correctly about exam language, in English.
- **The app writes the refusal sentence, not the model.** Fixed wording that cannot drift
  and cannot be mistaken for the whole reply. `api._stream` sends it ahead of the first
  token and `chat_node` prepends it to the stored message, so live and reloaded agree.
- **A Nepali question is translated to English before the model reads it.** "Do not mirror
  the student's language" did not hold either. Translating removes the thing being
  mirrored, and it is the same bargain the documents already get. Retrieval gains from it
  too: an English query embeds against an English index instead of across languages.

The student's own words stay in the transcript; only the copy the model reads is rewritten.
The pass list lookup deliberately still reads the raw message — a form number that survives
a paraphrase may not survive a translation, and "फारम नम्बर 2083-4001 पास भयो?" still
resolves to the right candidate.

**24 turns, 8 cases, 3 runs each: every answer in English, every question answered.** Zero
Devanagari in every case that asked for another language or was written in one. The 1-3%
Devanagari left in the English controls is the desirable kind — official Nepali terms
quoted in brackets after the English, which the notices themselves use.

## 20 · `FIXED` · The theme colour barely shows

the whole app still looks black and white, need to include the theme color more!!

The cause was not the pigment, it was its scope. 16 confined lapis to the interactive
layer, and this app's entire interactive surface is one send button and a handful of
links — four coloured pixels on a page. So lapis was given the job it should have had:

    ink      what the notices themselves say — headlines, prose, the answer.
    lapis    the app's own hand — the datelines it computed, the labels it prints
             over other people's words, the controls it offers, the row you are on.
    crimson  consequence. Unchanged, and it still outranks lapis where they meet.

That rule alone put colour on every page, because the dateline and the eyebrow appear
on all of them. The wordmark, the active nav item, the section rules, the answer's list
markers and bullets, the citation ordinals, and the composer's focus border followed
from it. One tinted band on the landing page — the three promises, which are the app
talking about itself — is the only field of colour rather than a mark.

Two things fell out of it. Eyebrows were `--faint`, which cleared 2.9:1 against paper
and failed AA at that size; lapis clears 9.8:1. And inline `code` had been sitting on
`--crimson-soft`, which had quietly broken the rule since 16 — a code span is not a
deadline.

## 21 · `FIXED` · The pass list lookup only took a form number or a rank

make the rank, result look up more advanced with name, districts, for e.g is sabin
shrestha on the list, what rank did he scored, or just first name or just last name,
or just district,

Same discipline as 1 and 2, extended to messier input. A form number or a rank is a key
into an exact index; a name is not — "Sabin Shrestha" turned out not to be on the list at
all, "Shrestha" alone matches 357 of the 7,179 rows, and Nepali names run two to four
words with no reliable split into first/last. So the match is built the same way
`_FORM_RE`/`_RANK_RE` already are: not "does this look like a name", but "is this word or
phrase one a real, published candidate actually has" — the vocabulary is the CSV's own
name and district columns, not a guess at what a name looks like.

Three things had to be caught before this was honest rather than just plausible:

- **A stray common word must not false-trigger a name lookup.** Three real first/last
  names on the list — "Raj", "Dev", "Bal" — are also common enough outside it to fire on
  unrelated text, so single-word matching requires 4+ letters. "Nepali" is a real surname
  (11 candidates) and also the one word this app's own language handling (`19`) makes
  students type constantly and unrelatedly; excluded by name, those 11 stay reachable by
  full name, form number, or rank.
- **Two name words in one question must not read as two unrelated lookups.** "Is Sabin
  Shrestha on the list" matches no full name, so it falls to single-word matching — 15
  Sabins, 357 Shresthas, reported separately that's noise. Fixed to intersect: is there a
  candidate with *both* words? Here, no — and the correct answer is one clean "not found",
  not two "too many to list"s that leave the model to guess whether they overlap.
- **"Who topped from Mustang" must not also answer with the global rank 1.** The topper
  heuristic from issue 1 fires on the word "topped" regardless of context; qualified by a
  district it's a different question the district block already answers correctly, and
  showing both risked the model conflating the global topper with the district's. Now the
  topper heuristic turns itself off whenever a district is also named; an explicit numeral
  ("rank 1") is unaffected either way.

A bare district mention alone doesn't trigger a lookup — "does someone from Kathmandu need
extra documents for the quota" isn't a pass-list question, and dumping 692 names on it
would answer a question nobody asked. It only fires alongside a result-shaped word
("pass", "rank", "topper", "candidate", "list", ...), the same anchoring `_BARE_RE` already
uses for a bare form number.

Ambiguity is reported, never resolved by guessing — extending the rule issue 1 exists for.
Several candidates sharing a name are listed (capped at 8, with the true count stated) and
the model is told explicitly not to pick one. A district lookup names only its five
best-ranked candidates and says so, never implying they're the whole list. And a name that
matches but not the district given back gets its own honest answer — "on the list, but not
from Kathmandu" — rather than a flat "not found" that would wrongly suggest the candidate
never sat the exam at all.

Verified against the live bot: a real non-existent "Sabin Shrestha" correctly reported
absent; a unique name resolved directly to its rank; 357 Shresthas and 5 Aayush Adhikaris
both correctly refused with a request to narrow down; the Kathmandu topper answered
correctly with the subset caveat stated; a real candidate (Prabesh Giri) asked about under
the wrong district (Kathmandu instead of Chitawan) got the honest mismatch answer instead
of a false negative; and the Kathmandu-quota and eSewa control questions were unaffected.

## 22 · `FIXED` · It answers questions outside its scope, and then loses the thread

> the small talk might have slipped, and now it ansers questions out of its main scope,
> also seems like it doesnot even remember the last conversation

The reported transcript: `hello` answered normally, `lets go on a holiday` answered with a
six-point holiday-planning questionnaire, and then `bahamas` — the student answering that
questionnaire — met with confusion about why the Bahamas had come up.

Two complaints, one cause. The memory was never broken: in a clean thread,
`what is the entrance exam fee?` → `hello` → `what did i just ask you about?` recalls the
fee correctly. What breaks memory is the off-scope answer itself. Once a holiday
questionnaire is in the transcript, `bahamas` gets retrieved against and reasoned about as
if it were an IOE question, and every turn after it is incoherent. "It forgot" is the
symptom; answering the holiday question is the bug.

The small-talk gate from the previous change was not the culprit either — `is_small_talk`
returns False for "lets go on a holiday", "bahamas", "holiday" and "lets go". Nothing had
slipped. There simply was no scope check anywhere in the graph: the system prompt asked
the model to stay on topic, and with 6,000 characters of retrieved context in front of it,
it did not.

So the check became a node. `guard` sits between `lookup_result` and `chat_node` and
decides whether the question is answered at all; on a refusal the graph goes to `refuse`,
which emits the app's own sentence with no model call and no citations.

Three signals, cheapest first:

- **An exact pass-list hit passes, free.** A bare form number is in scope by construction.
- **A YES/NO classifier on the student's own words.** Framing mattered more than anything
  else here. The first version asked IN or OUT and scored 26/39 — 17/17 on out-of-topic
  but only 9/22 on real questions, which is the wrong error to make. Reframed as "could
  this plausibly be about IOE? When in doubt, say YES", it scored 36/39. A third framing
  (ANSWER/REFUSE) was worse at 32/39.
- **A relevance rescue, only to overturn a NO.** `best_match` scores the raw question
  against the index; ≥ 0.60 answers anyway. This exists because the classifier's remaining
  misses are real questions with vocabulary it does not recognise — "how do I pay with
  eSewa" reads as shopping and scores 0.62.

Two things this cost, both found by measurement rather than reasoning:

- **Retrieval score alone cannot decide scope.** The distributions overlap badly: in-scope
  0.435–0.700, off-scope 0.357–0.573. "how do I apply to Kathmandu University" (0.573)
  outranks "how many seats are there in pulchowk" (0.478). That is why relevance is a
  rescue and not the test.
- **The signal must be read off the student's words, not the rewritten query.** The first
  attempt guarded the classifier against that and then read relevance off the rewrite —
  and `rewrite_query` had turned "lets go on a holiday" into "IOE admission documents for
  holiday related scholarships", scoring 0.615, and "bahamas" into "IOE admission
  documents for Bahamas", scoring 0.646. Both sailed through the rescue. A signal the
  pipeline itself made IOE-shaped cannot be used to judge whether something is IOE.

But judging the message alone then broke bare follow-ups: `what did i just ask you about?`
and `how many are there?` carry no topic at all, and were refused. The distinction that
matters is between the *rewrite*, which injects IOE words into the student's message, and
the *transcript*, which is what was actually said. So the classifier is shown the last two
turns verbatim, with the rule that a message which only makes sense as a follow-up
continues whatever came before. On a 27-case matrix that scored 26/27, the one miss being
the eSewa question the rescue already covers.

Verified against the live bot, 32 checks: the reported transcript now refuses both
off-topic turns and still answers `so when is the entrance exam?` with a citation; 10/10
off-topic questions refused (~1.5s each, no model call); 10/10 real questions answered;
8/8 bare follow-ups answered, including the two that regressed; small talk still returns
in under a second. Refusals are stored on state so a reloaded conversation shows the same
sentence, and `api._stream` sends it explicitly — the `refuse` node makes no model call, so
it streams no tokens of its own.

## 23 · `FIXED` · It gets the fee arithmetic wrong

> it causes error in fee calculation, there are three columns, regular, fullfee and
> foreign, and three boxes: for each box at the end, there is a total [...] a regular
> student has to pay 66487, and 17669 in his lifetime in this college, with the 3400
> dharauti amount to be returned

Every figure in that report is in the documents already, and retrieval finds them. Four
questions, four different ways of getting them wrong:

| Asked | Answered |
| --- | --- |
| total for the whole degree | multiplied 6,974 by 8 correctly, then trailed off before a total |
| total fee for a regular student | invented a per-programme tuition table that is in no document, and a rule that Regular students pay "30% less than full fee" |
| what is due on admission day | right figure, wrong breakdown — called 17,669 the table A total |
| how much do I get back | invented a refund policy, including a hardship refund |

One cause. Reading these tables requires arithmetic — a per-semester figure times eight,
three tables added, and one number that is a *part* of the degree total rather than an
addition to it — and a 7B model does arithmetic about as reliably as it does anything
else it was not given. So the totals are computed in `src/ioe/fees.py` and handed over
already worked out, exactly as `dates.annotate_dates` hands over BS/AD conversions. A
number the model reads is right; a number it derives is a coin toss.

Only the line items are stored. Every total is summed from them, and `verify()` re-derives
all twenty published totals from those line items and fails if any disagrees, so a typo
here breaks loudly rather than teaching the assistant a wrong number. That check also
settled which document wins where the two disagree: the campus notice reproduces from its
own line items, and the booklet does not — it prints 286,470 as the Full Fee amount due at
admission where the items give 216,470, and its Foreign column drifts by a few rupees in
several places.

**On the report's own arithmetic:** 17,669 is not a separate lifetime charge. It is
6,974 + 7,295 + 3,400 — one semester plus both one-time boxes — so it is already inside
the 66,487, not owed on top of it. 66,487 is the published tables-only figure; the campus
notice also charges internet at 600 a semester and 1,000 to the Engineering Council, which
brings the real degree total to 72,287, of which 3,400 comes back.

The wiring is `lookup_result`'s, extended: the fee schedule is a second exact table beside
the pass list, and `guard` treats a fee question as in scope by construction. The block is
read off the raw message and off the rewritten one — the rewrite is a translation, so a
question asked in Nepali is recognised there and not in the original.

Getting the model to actually use it took five rounds, and every one of them was layout
rather than instruction:

- **Position.** Placed before the retrieved documents it was ignored outright — retrieval
  puts the raw fee tables in the same prompt, and the model went back to the line items
  and multiplied. Whatever sits nearest the question wins, so the settled numbers go last.
- **No arithmetic in the block.** It first showed its working — `8 x 6,974 + 7,295 +
  3,400 = 66,487` — and the model copied the habit rather than the result, printing sums
  that were wrong around a figure that was right.
- **One category, not four.** Four columns was tried on the reasoning that reading off a
  number would then mean reading off a heading. It was worse: tracking a column across
  fifty characters of whitespace is the one thing a 7B model cannot do, and "how much is
  the library deposit" came back as the Full Fee figure labelled Regular. It now narrows
  to the category the student named, or to Regular with the answer saying so.
- **Totals first.** The model answers with the first plausible row it meets. Below the
  components, "the sponsored fee at admission" came back as a component subtotal.
- **Labels.** "at admission" appears on the TOTAL row and nowhere else, because while the
  one-time charges were labelled "one-time fees at admission" they took that question
  instead. The three deposits are prose under the table rather than rows, because as rows
  they outcompeted their own total and "the deposit for a full fee student" came back as
  the campus deposit alone.

Two things the block states outright, because they were invented when the model had to
reason: that only the table C deposits are returned and there is no withdrawal or hardship
refund, and that the four categories are separate rates rather than discounts off one
another.

Verified against the live bot: 26 fee questions, every figure correct and no number in any
answer that is not in the schedule — including the ones that were wrong before, the
line-item questions, both totals for all four categories, and the Nepali phrasing. The
detector is 17/17 on firing, and stands down for the entrance examination fee and the
application form fee, which are different money answered by the payment notices. One
interaction bug surfaced and was fixed on the way: "how much is the health insurance fee"
was being *refused*, because `guard`'s classifier reads "health" as a health question. The
40-case regression from `22` still passes in full.
