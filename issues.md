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

### Closed — 16

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
