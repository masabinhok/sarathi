import asyncio
import re

import aiosqlite
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import MessagesState

from ioe.dates import annotate_dates, today_context
from ioe.fees import FEE_SOURCE, fee_context
from ioe.notices import digest as notice_digest
from ioe.rag import (
    MAX_SOURCES,
    NUM_CTX,
    OLLAMA_URL,
    format_context,
    get_store,
    keep_grounded,
    rerank,
    source_payload,
)
from ioe.results import RESULT_SOURCE, lookup_context
from ioe.threads import DB_PATH

TEXT_MODEL = "qwen2.5:7b"

# Chunks retrieved per question, and the cosine relevance floor a chunk must clear.
# Measured separation on bge-m3 is wide (~0.6 on topic vs ~0.3 off topic), so this
# mainly exists to keep unrelated chunks out of the prompt when a question misses.
TOP_K = 6
MIN_RELEVANCE = 0.45

SYSTEM_PROMPT = SystemMessage(
    content="""You are Sarathi, the IOE entrance and admission assistant -- a guide for \
students applying to the Institute of Engineering (IOE), Tribhuvan University, Nepal, \
and for the parents helping them.

You help with:
- The IOE entrance examination for BE, BArch, and postgraduate programs
- Eligibility, application steps, required documents, and admission timelines
- Exam structure, syllabus coverage, marking, and preparation strategy
- IOE constituent and affiliated campuses -- Pulchowk, Thapathali, Purwanchal, \
Paschimanchal, Chitwan and the rest -- and the programs each offers

Scope: you answer ONLY questions about IOE admissions and entrance exams. If a \
student asks about anything else -- coding, homework, general knowledge, other \
universities, personal advice -- you must refuse. Do not answer the off-topic question \
even partially. Say in one sentence that you only handle IOE admission and entrance \
questions, then invite them to ask one.

Language: you write in English. Always.

Using a pass list lookup:
- A "Pass list lookup" block below is an exact record from the published result table, not a guess. Never alter a rank, name, or district from it.
- Restate the record as an ordinary sentence to the student. Do not copy the block itself: neither its bracketed header nor its field labels.
- If the lookup says the number does not appear on the list, say so plainly, note that this cannot distinguish a candidate who did not pass from a mistyped number, and suggest verifying on entrance.ioe.edu.np. Be kind about it; this is hard news to receive.
- The lookup covers both directions: a form number resolves to a rank, and a merit rank resolves to the candidate holding it. If a block is present, answer from it directly and do not ask the student for a form number they did not need to give.
- Never guess whether a candidate passed, never infer a rank from a form number, and never infer a candidate from a rank.
- Refer to a candidate as "they". Never guess a candidate's gender from their name, and do not state a gender even when you could infer one.
- A lookup can also be by name or by district, and either can match one candidate, several, or none. When a block says several candidates match, list what it gave you and ask the student which one they mean -- a form number, a fuller name, or a district would narrow it down. Never pick one for them, and never describe a candidate the block did not include.
- When a block says a name matched but not the district the student gave, say exactly that -- it is not evidence the candidate never sat the exam, only that this particular record does not carry that district. Do not treat it as a "not found".
- A district lookup names only the best-ranked candidates from that district, and says so. Never imply the ones shown are the only candidates from there.

Using the reference documents:
- Reference documents may be supplied below under "Reference documents". When they \
are, answer from them rather than from memory, and name the source you used.
- If the documents carry a year, state it, so the student knows which admission cycle \
the answer describes.
- If the documents do not cover the question, say so directly and point the student to \
the notice feed in this app, to ioe.edu.np or entrance.ioe.edu.np, or to their campus \
admission office. Do not fill the gap from memory.
- Do not end your answer with a source list, a bibliography, or a "References" heading. \
The interface prints the documents you were given underneath your answer, with links to \
the official notices. Naming a source mid-sentence is still welcome; repeating the list \
is not.

Using the notice feed:
- A "Notice feed" block below lists the most recent notices published on the official \
sites, newest first. It is the only current record of what has been published; the \
reference documents were prepared earlier and do not know about anything in it.
- When a student asks whether something has been published, whether there is anything \
new, or what the latest notice is, answer from this block. Give the title, the date in \
both calendars, which campus or board published it, and a Markdown link.
- Never tell a student that nothing has been published recently unless the block is \
empty. If the block lists a notice, it exists.
- The block gives titles, not contents. Never describe what a notice says, or state a \
name, list, rank, date, or amount from it, on the strength of its title. Say what was \
published and when, and link the student to it so they can read it.
- A notice appearing here that the reference documents do not cover is normal and worth \
saying plainly: the notice is newer than the documents.

Dates:
- A "Today's date" block below gives the current date in both calendars. Use it rather than guessing, and never state a date you were not given.
- A "Date conversions" block, when present, has already resolved the BS dates in play to AD and to an offset from today. Read those off; do not do calendar arithmetic yourself.
- Every date and day-count you write must appear verbatim in one of these blocks. Do not convert, add, subtract, or restate a date in any other form. When you give an offset, copy it from the line for that exact date -- offsets on neighbouring lines belong to other dates.
- Say plainly when a deadline has already passed, and how long ago.
- When a document says a deadline has moved, that a list is final, or that a student must appear in person to verify documents, put that date in **bold** and say plainly what they have to do. These are the answers a student cannot afford to skim past.
- Do not volunteer the date in answers that did not ask about timing.

Formatting your answer:
- Write in short paragraphs separated by a blank line. A dense block goes unread by someone scanning for one fact.
- Use "- " bullets for a set of documents, requirements, or options, and numbered "1." steps for a procedure the student works through in order.
- Use **bold** for a deadline, an amount, or anything that costs the student their place if missed. Use it sparingly; bolding everything bolds nothing.
- Write in Markdown. Paragraphs, "- " bullets, numbered steps, **bold**, headings, tables, and [links](url) all render properly for the student.
- Use a table when you are comparing the same fields across several things -- campuses, seat types, payment methods. Use a list when you are not. A two-row table is a list wearing a costume.
- Never wrap a table, a list, or anything else in a code fence. Write it directly. A fence is for code, and nothing in IOE admissions is code.
- When a document gives an official URL, write it as a Markdown link.
- Do not use emoji, and do not decorate an answer with headings it does not need. A four-sentence answer is four sentences, not a document.

Rules:
- Never invent year-specific facts. Exam dates, deadlines, fees, seat counts, cutoff \
marks, and results change every year. If you are not certain, say so plainly rather \
than guessing.
- Never predict a student's chance of admission, and never state a cutoff rank or cutoff mark for a campus or program. You have no cutoff data. If asked, say so directly, and point them to the published results and their campus admission office rather than offering an estimate.
- A seat count is not a rank threshold. Never compare a student's rank against a number of seats, and never tell a student their rank falls within, qualifies for, is safe for, or is close to a program. Seat totals in these documents say how many students a campus takes, not how far down the merit list it reaches.
- Distinguish clearly between stable facts about the process and details a student must \
verify for their own admission year.
- Be clear, direct, and encouraging. Students asking these questions are often anxious, \
so keep answers concrete and free of filler."""
)


REWRITE_PROMPT = """Rewrite the student's latest message as a standalone search query \
for a document search over IOE admission documents.

Resolve any pronouns and implied subjects using the conversation. Keep the wording of \
the original where you can. Output only the query, with no preamble or quotes.

Conversation so far:
{history}

Latest message: {question}

Standalone search query:"""


class ChatState(MessagesState):
    # The student's question as the model should read it: any "reply in Nepali" taken
    # out, and translated to English if it was not written in English. The message the
    # student actually typed stays in `messages`, which is what the transcript shows.
    question: str
    query: str
    context: str
    lookup: str
    # Fee totals worked out in full, so the model reads them instead of doing the
    # arithmetic that it got wrong every time it was asked.
    fees: str
    sources: list[dict]
    # The refusal the guard wrote if it turned the question away, or "".
    refusal: str


model = ChatOllama(model=TEXT_MODEL, base_url=OLLAMA_URL, num_ctx=NUM_CTX)


# ── Keeping the answer in English ─────────────────────────────────────────────
# SYSTEM_PROMPT says to answer in English and on its own that does not hold. Measured
# against the live bot: asked "please reply in Nepali", asked in Nepali with no
# instruction at all, and asked for Hindi, qwen2.5:7b switched every time -- and what it
# produced was not worth reading, mixing Hindi into Nepali sentences and inventing
# syllabus subjects while it was at it.
#
# Four rounds of prompting could not fix it. Told to refuse and then answer, the model
# wrote the refusal in Nepali; given the refusal to copy, it copied it and then treated
# it as the whole reply on 3 of 12 runs; told the refusal was already handled and to
# ignore the request, it went back to Nepali on 12 of 18. The pattern across all four is
# that naming the request in the prompt is what keeps it alive.
#
# So the request is not named. It is removed. The sentence asking for another language
# is stripped out of the question, the app says the one thing that needs saying, and the
# model is handed an ordinary question -- which it answers in English, because that is
# what it does with ordinary questions.
#
# SYSTEM_PROMPT is down to one line on the subject for the same reason. The paragraph it
# used to carry explained the rule, offered two justifications the model could pass on,
# and told it what to do when asked for Nepali -- nine lines that named the request four
# times, in the prompt, on every turn, including the turns nobody asked.

_DEVANAGARI = re.compile(r"[\u0900-\u097f]")
_LATIN = re.compile(r"[A-Za-z]")

# Languages a student might ask to be answered in. English is deliberately absent: a
# student asking for English is asking for what they are already getting.
_OTHER_LANGUAGE = re.compile(
    r"\b(nepali|nepalese|hindi|newari|newa|maithili|bhojpuri|urdu|bengali|bangla|"
    r"tamil|chinese|mandarin|japanese|korean|arabic|russian|spanish|french|german|"
    r"portuguese|italian|devanagari)\b"
    r"|नेपाली|हिन्दी|हिंदी|मैथिली|भोजपुरी|नेवारी|उर्दू",
    re.IGNORECASE,
)

# A language on its own is not a request -- "is the exam set in Nepali" is a question
# about the exam. It takes a language and something that means "say it", together.
_SPEECH = re.compile(
    r"\b(reply|replies|answer|answers|respond|responds|write|writes|say|says|speak|"
    r"speaks|talk|talks|explain|explains|translate|translates|tell|tells)\b"
    r"|जवाफ|जवाब|भन्नु|लेख्नु|बोल्नु|दिनुहोस्|सुनाउनु|बताइए|समझाइए|लिखिए",
    re.IGNORECASE,
)

# Devanagari ends a sentence with a danda, which no ASCII sentence splitter knows about.
_SENTENCE = re.compile(r"(?<=[.!?।])\s+|\n+")

# The app's own words. Fixed, so the wording cannot drift from one turn to the next, and
# naming no particular language, because the same sentence has to serve a request for
# Nepali and a request for Hindi.
ENGLISH_ONLY_SENTENCE = (
    "I answer only in English. The notices I work from are in English, and I am not "
    "reliable enough in any other language to be trusted with something you will act on."
)

TRANSLATE_PROMPT = """Translate the student's message into English.

Output only the translation. No preamble, no quotes, no explanation, no note about what \
you did. Keep a question a question. Leave proper nouns, form numbers, dates and any \
English already in the message exactly as they are.

Message: {question}

English:"""


def without_language_request(question: str) -> str:
    """The question with any "reply in <language>" sentence taken out of it.

    Returns the question unchanged when it contains no such sentence -- and, crucially,
    when the request *is* the whole question. "Can I answer the exam paper in Nepali?"
    reads as a request by every test above, and stripping it would leave nothing to
    answer; a student asking that is asking about the exam, so they get the ordinary
    treatment and an ordinary answer.
    """
    parts = [p for p in _SENTENCE.split(question) if p.strip()]
    kept = [p for p in parts if not (_OTHER_LANGUAGE.search(p) and _SPEECH.search(p))]
    if not kept or len(kept) == len(parts):
        return question
    return " ".join(p.strip() for p in kept)


def english_only_preface(question: str) -> str:
    """The app's sentence for a turn that asked for another language, or "".

    Used twice on the same turn and it must agree with itself: api._stream sends it
    ahead of the model's first token so the student sees it as the answer opens, and
    chat_node prepends it to the stored message so a reloaded conversation reads the
    same as the one that was watched live.
    """
    if without_language_request(question) == question:
        return ""
    return f"{ENGLISH_ONLY_SENTENCE}\n\n"


def _in_devanagari(text: str) -> bool:
    """Whether the text is written in Devanagari rather than merely quoting a term in it."""
    return len(_DEVANAGARI.findall(text)) > len(_LATIN.findall(text))


def read_in_english(question: str) -> str:
    """The question in English, translating it first if it was not written that way.

    Telling the model not to mirror the student's language does not hold either -- it
    answered a Nepali question in Nepali often enough to matter. Translating removes the
    thing being mirrored: the model is handed an English question, and English questions
    it answers in English every time.

    This is the same bargain the documents already get. They are translated on the way in
    because the model reads English better than it translates while it reasons, and a
    question is no different. Retrieval gets the same benefit for free: an English query
    embeds against an English index rather than across languages.

    The student's own words are what the transcript keeps. Only the copy the model reads
    is translated.
    """
    if not _in_devanagari(question):
        return question
    try:
        rendered = model.invoke(
            [HumanMessage(content=TRANSLATE_PROMPT.format(question=question))]
        )
        english = (rendered.content or "").strip()
    except Exception:  # noqa: BLE001 - a failed translation must not fail the answer
        return question
    # A translation that came back empty, or still in Devanagari, is no translation.
    return question if not english or _in_devanagari(english) else english


def rewrite_query(state: ChatState) -> dict:
    """Settle what the question is, then condense it into a search query.

    Two steps that both have to happen before anything else reads the question. First it
    is put into the form the model should see -- request to switch language removed, and
    translated to English if it was not written in English. Then, on a follow-up, it is
    condensed against the history: "what about the fees?" retrieves nothing useful on its
    own, but becomes "BArch entrance exam fees". The first turn needs no condensing.
    """
    messages = state["messages"]
    question = read_in_english(without_language_request(messages[-1].content))

    prior = messages[:-1]
    if not prior:
        return {"question": question, "query": question}

    history = "\n".join(
        f"{'Student' if isinstance(m, HumanMessage) else 'Assistant'}: {m.content}"
        for m in prior[-6:]
    )
    rewritten = model.invoke(
        [
            HumanMessage(
                content=REWRITE_PROMPT.format(history=history, question=question)
            )
        ]
    )
    return {
        "question": question,
        "query": (rewritten.content or question).strip() or question,
    }


def retrieve(state: ChatState) -> dict:
    """Fetch supporting chunks. An empty or missing index simply yields no context."""
    try:
        # Over-fetch so a demoted chunk can actually be displaced by a better-suited one.
        hits = get_store().similarity_search_with_relevance_scores(
            state["query"], k=TOP_K * 2
        )
    except Exception:  # noqa: BLE001 - an unbuilt index must degrade to no context, not 500
        return {"context": "", "sources": []}

    ordered = rerank(state["query"], hits)
    kept = [(doc, score) for doc, score in ordered if score >= MIN_RELEVANCE][:TOP_K]
    # The scores travel with the documents because the two uses want different cuts: the
    # prompt takes everything that cleared MIN_RELEVANCE, while the citation block takes
    # only what is strong enough to be worth naming. See source_payload.
    #
    # Both keys are written on every path, including the empty one. State persists across
    # turns, so a turn that retrieves nothing has to clear the previous turn's documents
    # rather than inherit them and cite the wrong notice.
    return {
        "context": format_context([doc for doc, _ in kept]) if kept else "",
        "sources": source_payload(kept),
    }


# ── Turns that need no documents ──────────────────────────────────────────────
# "thanks" was costing more than a real question. rewrite_query is told to resolve
# implied subjects from the history, and a greeting has no subject, so the model
# borrowed the previous one: "thanks" was rewritten to "IOE admission exam date 2083",
# which then retrieved 6.2 KB of exam-date documents to be prefilled into the prompt
# before the model could say "you're welcome". Measured on the running app, one such
# turn spent ~0.7s in the rewrite call and ~0.5s in the embedding call to assemble
# context the answer could not use, and made every following turn slower still.
#
# So a turn that is only a greeting, a thank-you, or an acknowledgement is routed
# straight to the answer. The test is a whole-message match against a fixed vocabulary,
# not a judgement: anything with a question attached ("thanks, what about BArch?")
# fails it and takes the ordinary path, because the cost of skipping retrieval on a
# real question is an ungrounded answer, and the cost of not skipping it on a greeting
# is a second of latency.
#
# Deliberately absent: "yes", "no", "sure". They read like small talk but they are
# often the answer to something the assistant asked, and that turn may well need the
# documents the question was about.
_SMALL_TALK = re.compile(
    r"^\W*(?:"
    r"h+i+|h+e+y+|h+e+l+o+|hello|hiya|yo|namaste|namaskar|"
    r"good\s+(?:morning|afternoon|evening|day)|good\s?night|"
    r"thanks?|thank\s+you(?:\s+so\s+much|\s+very\s+much)?|thx|tysm|ty|"
    r"ok(?:ay)?|k|cool|nice|great|awesome|perfect|got\s+it|understood|alright|all\s+right|"
    r"bye|goodbye|see\s+you|"
    r"how\s+are\s+you(?:\s+doing)?|what'?s\s+up|sup|"
    r"who\s+are\s+you|what\s+can\s+you\s+do"
    r")"
    r"(?:\W+(?:there|again|sarathi|bro|sir|maam|ma'?am|dai|friend|buddy|man|guys?|"
    r"a\s+lot|so\s+much|very\s+much))*\W*$",
    re.IGNORECASE,
)


def is_small_talk(text: str) -> bool:
    """Whether the message is social in its entirety and needs no documents."""
    return bool(_SMALL_TALK.match(text.strip()))


def small_talk(state: ChatState) -> dict:
    """The no-documents path: answer from the system prompt and the conversation.

    Every key retrieve and lookup_result would have written is written here too, and
    written empty. State survives the turn it was made on, so leaving them alone would
    hand chat_node the previous question's documents -- and print the previous
    question's citations under "you're welcome".
    """
    return {
        "question": state["messages"][-1].content,
        "query": "",
        "context": "",
        "lookup": "",
        "fees": "",
        "sources": [],
        "refusal": "",
    }


def route_question(state: ChatState) -> str:
    """Whether this turn needs the retrieval pipeline at all."""
    return (
        "small_talk"
        if is_small_talk(state["messages"][-1].content)
        else "rewrite_query"
    )


def lookup_result(state: ChatState) -> dict:
    """Answer from the exact tables -- the pass list and the fee schedule -- rather than
    leaving either to retrieval and arithmetic."""
    asked = state["messages"][-1].content
    # The raw message, not the rewritten or translated one: both of those go through the
    # model, and a form number that survives a paraphrase may not survive a translation.
    lookup = lookup_context(asked)
    # Fees are the other way round. There is no exact token to preserve, and the rewrite
    # is a translation into English, so a question asked in Nepali is recognised there
    # and not in the original. Both are read, and the first that matches wins.
    fees = fee_context(asked) or fee_context(state.get("question") or "")
    return {"lookup": lookup, "fees": fees}


# ── Keeping to the subject ────────────────────────────────────────────────────
# SYSTEM_PROMPT says to refuse anything that is not IOE admission, and on its own that
# does not hold either. Asked "lets go on a holiday", the assistant produced a six-point
# holiday-planning questionnaire; the next message, "bahamas", then arrived in a prompt
# stuffed with IOE fee documents and the model could make no sense of it. The second
# failure looked like lost memory and was not -- history was intact, and asked outright
# the model recalled the earlier turns correctly. It was the first failure spreading:
# once an off-topic answer is in the transcript, every turn after it is incoherent.
#
# So the decision is taken out of the answering prompt and made on its own, where the
# model has one thing to weigh instead of ninety lines of instructions. Three signals,
# and refusing needs all three to agree, because refusing is the damaging mistake: a
# student turned away with a real question has no way to appeal, while an off-topic
# answer costs a few wasted seconds.
#
#   1. An exact pass list hit. A form number was found in the published table -- that is
#      not a judgement call and nothing overrides it.
#   2. The classifier. On its own it never once let an off-topic question through in 17
#      tries, but it turned away 2 of 22 real ones, which is the wrong way round.
#   3. So a NO gets a second opinion: how well the question matches the documents.
#      Measured over 39 questions, both real questions the classifier misread scored
#      above this line ("how do I pay with eSewa", 0.700) and nothing off topic reached
#      it (the closest, "how do I apply to Kathmandu University", 0.573). Below it the
#      question is merely unmatched, not off topic -- "how many seats are there in
#      pulchowk" only reaches 0.478.
#
# Signal 3 is measured here, against the student's own words, rather than read off what
# retrieve already scored. That score belongs to the rewritten query, and the rewrite is
# what makes a follow-up IOE-shaped: "lets go on a holiday", asked after a greeting, was
# condensed into "IOE admission documents for holiday related scholarships" and scored
# 0.615 on it. A signal that the pipeline itself contaminated cannot be used to overrule
# the one honest reading of the question. Running it only to overturn a NO also keeps it
# off the common path, where it would cost an embedding call for nothing.
SCOPE_RESCUE = 0.60

# Judged on the student's own words, never on the rewritten search query. The rewrite
# resolves a follow-up against the conversation, which for "bahamas" produced something
# with IOE in it -- and a guard that reads a query the pipeline just made IOE-shaped is a
# guard that passes everything. The transcript below the message is the conversation as it
# actually happened, which is a different thing: "how many are there?" is a real question
# about whatever was just discussed, and judged alone it looks like nothing at all.
SCOPE_PROMPT = """Sarathi answers questions about applying to the Institute of \
Engineering (IOE), Tribhuvan University, Nepal -- its entrance exam, results, fees, \
forms, quotas, documents, deadlines, campuses, programs, notices -- and questions about \
Sarathi itself.

{history}Read the student's message. Could it plausibly be one of those? Say YES.
Say NO only if the message is clearly about something else entirely: another university, \
another country, coding, homework, general knowledge, news, travel, health, shopping, or \
personal life.

A short message that only makes sense as a follow-up to the conversation above -- \
"how many are there?", "what about the fees?", "what did I just ask?" -- continues \
whatever that conversation was about. Say YES.

When in doubt, say YES.

Message: {question}

YES or NO:"""

# The app's own words again, for the same reason they are the app's own in
# english_only_preface: asked to write its own refusal, the model writes a paragraph and
# then answers the question anyway.
OFF_TOPIC_SENTENCE = (
    "I only handle questions about IOE admissions and the IOE entrance exam, so I have "
    "to leave that one alone. Ask me about the exam, your application, the fees, a "
    "result, or a campus and I can help."
)


def recent_exchange(messages: list, turns: int = 2) -> str:
    """The last few turns verbatim, so a bare follow-up can be read in context."""
    lines = []
    for message in messages[-(turns * 2 + 1) : -1]:
        speaker = "student" if isinstance(message, HumanMessage) else "Sarathi"
        said = " ".join((message.content or "").split())
        if said:
            lines.append(f"{speaker}: {said[:400]}")
    return "\n".join(lines)


def is_in_scope(question: str, history: str = "") -> bool:
    """Whether the question is plausibly about IOE admission. Errs towards yes."""
    preamble = f"So far in this conversation:\n{history}\n\n" if history else ""
    try:
        verdict = model.invoke(
            [
                HumanMessage(
                    content=SCOPE_PROMPT.format(history=preamble, question=question)
                )
            ]
        )
    except Exception:  # noqa: BLE001 - a guard that cannot run must not refuse the student
        return True
    return not (verdict.content or "").strip().upper().startswith("NO")


def best_match(question: str) -> float:
    """How well the question itself matches the documents, ignoring the rewrite."""
    try:
        hits = get_store().similarity_search_with_relevance_scores(
            question, k=TOP_K * 2
        )
    except Exception:  # noqa: BLE001 - an unbuilt index is not evidence of anything
        return 0.0
    ordered = rerank(question, hits)
    return ordered[0][1] if ordered else 0.0


def guard(state: ChatState) -> dict:
    """Decide whether this question is answered at all."""
    if state.get("lookup") or state.get("fees"):
        return {"refusal": ""}
    messages = state["messages"]
    question = state.get("question") or messages[-1].content
    history = recent_exchange(messages)
    if is_in_scope(question, history) or best_match(question) >= SCOPE_RESCUE:
        return {"refusal": ""}
    return {"refusal": OFF_TOPIC_SENTENCE}


def refuse(state: ChatState) -> dict:
    """Turn the question away in the app's own words, with no model call at all.

    Nothing is cited, because nothing was read. api._stream sends this text to the
    student; it is stored here so a reloaded conversation shows the same refusal rather
    than an empty turn.
    """
    return {"messages": AIMessage(content=state["refusal"])}


def route_scope(state: ChatState) -> str:
    return "refuse" if state.get("refusal") else "chat_node"


def chat_node(state: ChatState) -> dict:
    messages = state["messages"]
    context = state.get("context")

    prompt = [SYSTEM_PROMPT, SystemMessage(content=today_context())]

    # Always present, not only when a question looks time-sensitive. The failure this
    # fixes was the assistant flatly denying that a notice existed, and a question does
    # not have to mention notices to be answered that way.
    feed = notice_digest()
    if feed:
        prompt.append(SystemMessage(content=feed))

    # Resolve BS dates from both the question and the retrieved text, so the model reads
    # off conversions instead of attempting calendar arithmetic it gets wrong.
    dates = annotate_dates(
        f"{state.get('question') or messages[-1].content}\n{context or ''}"
    )
    if dates:
        prompt.append(SystemMessage(content=dates))

    lookup = state.get("lookup")
    if lookup:
        prompt.append(SystemMessage(content=lookup))
    if context:
        prompt.append(SystemMessage(content=f"Reference documents:\n\n{context}"))

    # Last, after the documents rather than before them. Placed ahead of them it was
    # ignored: retrieval puts the raw fee tables in the same prompt, and asked for a
    # degree total the model went back to the line items and multiplied, which is the
    # one thing these worked figures exist to stop. Whatever is nearest the question
    # wins with a 7B model, so the settled numbers go nearest the question.
    fees = state.get("fees")
    if fees:
        prompt.append(SystemMessage(content=fees))

    # rewrite_query settled what the question is: stripped of any request to answer in
    # another language, and in English. The message the student typed stays in the
    # transcript untouched -- only the copy the model reads is swapped.
    asked = messages[-1].content
    question = state.get("question") or asked
    prompt.extend(
        messages
        if question == asked
        else [*messages[:-1], HumanMessage(content=question)]
    )

    answer = model.invoke(prompt)

    # api._stream has already sent this ahead of the first token; putting it on the
    # stored message is what keeps the reloaded conversation identical to the live one.
    preface = english_only_preface(asked)
    if preface:
        answer.content = preface + (answer.content or "")

    # Citations are assembled from what retrieval placed in this prompt, then narrowed to
    # the documents the finished answer visibly drew on. That second step is why this
    # happens here rather than in retrieve: a question can pull good documents and still
    # be answered with a refusal -- "How do I apply to Kathmandu University?" matches
    # these notices closely -- and a refusal with a reading list under it is a lie about
    # where the answer came from.
    sources = keep_grounded(answer.content or "", question, state.get("sources") or [])
    if state.get("lookup"):
        # The pass list is exact and is not put to the same test: a form number was looked
        # up in the published table, whatever the answer around it reads like. The pass
        # list and the notice that published it are one document at one URL, so citing
        # both would print the same notice twice, and the exact record keeps the slot.
        sources = [
            RESULT_SOURCE,
            *(s for s in sources if s.get("url") != RESULT_SOURCE["url"]),
        ]
    if state.get("fees"):
        # Same reasoning as the pass list: the figures came from the notice's own tables,
        # whatever else retrieval put in the prompt, so the notice is cited outright.
        sources = [
            FEE_SOURCE,
            *(s for s in sources if s.get("file") != FEE_SOURCE["file"]),
        ]

    # Attached to the message rather than to the state so they stay with the turn they
    # belong to, and the checkpointer replays them into /api/history.
    if sources:
        answer.additional_kwargs["sources"] = sources[:MAX_SOURCES]
    return {"messages": answer}


graph = StateGraph(ChatState)

graph.add_node("rewrite_query", rewrite_query)
graph.add_node("retrieve", retrieve)
graph.add_node("lookup_result", lookup_result)
graph.add_node("small_talk", small_talk)
graph.add_node("guard", guard)
graph.add_node("refuse", refuse)
graph.add_node("chat_node", chat_node)

graph.add_conditional_edges(
    START,
    route_question,
    {"rewrite_query": "rewrite_query", "small_talk": "small_talk"},
)
graph.add_edge("small_talk", "chat_node")
graph.add_edge("rewrite_query", "retrieve")
graph.add_edge("retrieve", "lookup_result")
graph.add_edge("lookup_result", "guard")
graph.add_conditional_edges(
    "guard", route_scope, {"refuse": "refuse", "chat_node": "chat_node"}
)
graph.add_edge("refuse", END)
graph.add_edge("chat_node", END)


# Checkpoints live in the same SQLite file as the conversation index, on the same volume
# as the notice cache. The earlier in-memory saver was fine while a conversation lasted
# one page visit, but the history sidebar promises a conversation is still there
# tomorrow, and a restart would otherwise leave the sidebar listing threads whose
# messages no longer exist.
_lock = asyncio.Lock()
_chatbot = None


async def get_chatbot():
    """The compiled graph, built on first use.

    Not built at import: AsyncSqliteSaver binds itself to the running event loop in its
    constructor, and at import time there isn't one. The lock makes the two requests that
    can arrive together during startup share a single connection rather than race to open
    two against the same file.
    """
    global _chatbot
    if _chatbot is None:
        async with _lock:
            if _chatbot is None:
                DB_PATH.parent.mkdir(parents=True, exist_ok=True)
                saver = AsyncSqliteSaver(aiosqlite.connect(DB_PATH))
                await saver.setup()
                _chatbot = graph.compile(checkpointer=saver)
    return _chatbot
