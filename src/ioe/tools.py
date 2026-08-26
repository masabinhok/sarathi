"""The tools the model may call, and the blocks their results become.

The arrangement here is the one decision the rest of the rewrite hangs off:

    Tools are a *selection* mechanism. Their results are re-rendered by the app as
    ordered prompt blocks.

Tool calls and their ToolMessages live in a `scratch` channel that only the planner ever
reads. What the answering model sees is `state["blocks"]`, laid out by `render_blocks` in
a fixed order the model has no say in. So the model chooses the evidence and the app
chooses where it sits -- which matters, because every placement lesson this app has
learned was expensive. The fee block goes last, nearest the question, because put in
front of the retrieved documents it was ignored and the model went back to the raw tables
and multiplied. Tool results arriving as ToolMessages would be ordered by call order,
which is to say by the whim of a 7B model, and that lesson would be lost.

Two further consequences worth naming:

- `messages` stays clean. It is the checkpointed transcript the sidebar replays; tool
  traffic has no business in it.
- A tool's declared arguments are a routing signal, not data. `lookup_result` does not
  take a form number, because a model that can pass a form number can invent one. It
  reads the student's own untranslated words off the state and hands them to the same
  `results.lookup_context` that reads them today.
"""

from typing import Annotated

from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from ioe import cutoffs, fees, notices, priority, results, seats
from ioe.dates import annotate_dates
from ioe.memory import previous_question
from ioe.rag import (
    MIN_RELEVANCE,
    TOP_K,
    format_context,
    get_store,
    rerank,
    source_payload,
)

# Nearest the question wins with a 7B model, so this order is the app's answer to that.
# Background first, evidence after it, and the worked figures last of all.
#
#   summary    the conversation so far -- notes, not a source
#   dates      computed BS/AD conversions
#   notices    what has been published lately, titles only
#   lookup     exact records from the published pass list
#   seats      published admission targets
#   priority   Pulchowk's priority-order rules -- the mechanism
#   chances    what this student's rank would actually have been placed into, worked out
#              from the published applications. After the rules, because it is the rules
#              applied, and a reader needs the mechanism before the result.
#   cutoffs    what rank was actually admitted in past years, when that is known
#   documents  retrieved passages
#   fees       worked fee totals. LAST, and see fees.fee_context for what it cost to
#              learn that: ahead of the documents it was ignored, because retrieval puts
#              the raw fee tables in the same prompt and the model went back to them.
#   uncovered  the instruction for a turn that found no evidence at all. After
#              everything, because when it is present there is nothing to crowd out and
#              it is the only instruction that matters.
BLOCK_ORDER = (
    "summary",
    "dates",
    "notices",
    "lookup",
    "seats",
    "priority",
    "chances",
    "cutoffs",
    "documents",
    "fees",
    "uncovered",
)

# The blocks that count as evidence. A turn that assembles none of these has nothing to
# answer from, and gets the `uncovered` instruction instead of being left to improvise.
EVIDENCE_BLOCKS = (
    "lookup",
    "seats",
    "priority",
    "chances",
    "cutoffs",
    "documents",
    "fees",
)


# Lines that already contain the settled answer rather than the evidence for it. A block
# carrying one of these has done the work; the model's only remaining job is to say it.
SETTLED_MARKERS = ("THE ANSWER TO THIS QUESTION IS", "** The student asked about")


def settled_lines(blocks: dict[str, str]) -> list[str]:
    """The already-decided lines, to be restated nearest the question.

    Blocks are rendered before the conversation, and the conversation is rendered before
    the question -- so on a follow-up the previous answer sits closer to the question than
    the evidence does, and the model answers from it. Measured: asked the whole-degree cost
    at Full Fee, told it was wrong, then "for regular", it produced 440,632 -- a number in
    no table, arrived at somewhere between the Regular block above and the Full Fee answer
    below it.

    "Nearest the question wins" is the lesson this codebase keeps relearning. Here it is
    applied one layer up: the settled figure is repeated after the conversation, where
    nothing else can outrank it.
    """
    found: list[str] = []
    for name in BLOCK_ORDER:
        for line in (blocks.get(name) or "").splitlines():
            if line.startswith(SETTLED_MARKERS):
                found.append(line.strip())
    return found


def render_blocks(blocks: dict[str, str]) -> list[str]:
    """The blocks present, in the house order. Unknown keys are dropped, not appended."""
    return [blocks[name] for name in BLOCK_ORDER if blocks.get(name)]


def _category(value: str | None) -> str | None:
    """The model's category argument, mapped onto a real one, or None.

    Never raises and never rejects. Declared as a Literal enum, this argument produced
    ToolInvocationError on a third of the fee questions in the suite: qwen2.5:7b emits
    "" and "full_fee" as readily as "Full Fee", the call fails schema validation, and the
    turn loses its fee figures while every other tool succeeds -- a silent, partial
    failure that looks like the detector missing.

    Which is the point made at the top of this file and then not applied here: a tool
    argument from a 7B model is a hint. The figures come from the student's own words
    either way, so an argument this tool cannot read is worth nothing and must cost
    nothing.
    """
    if not value:
        return None
    want = value.strip().replace("_", " ").replace("-", " ").casefold()
    for category in fees.CATEGORIES:
        if category.casefold() == want:
            return category
    for category in fees.CATEGORIES:
        if want and (
            want in category.casefold() or category.casefold().startswith(want)
        ):
            return category
    return None


def _done(tool_call_id: str, note: str, **update) -> Command:
    """A finished tool call: a short note for the planner, and blocks for the answer.

    The note is deliberately a count or a yes/no rather than the content. The planner
    only needs to know whether the call landed; handing it the passages as well would
    cost a thousand tokens to tell it something one sentence covers.
    """
    return Command(
        update={
            "scratch": [ToolMessage(content=note, tool_call_id=tool_call_id)],
            **update,
        }
    )


@tool
def search_documents(
    query: str = "",
    state: Annotated[dict | None, InjectedState] = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> Command:
    """Search the official IOE admission notices, the admission booklet and the entrance
    syllabus for passages that answer a question.

    Use this for eligibility, required documents, application steps, quotas, exam format
    and marking, syllabus topics, campuses and programmes, payment procedures, and
    anything else the published notices would cover. Pass a standalone query: resolve
    what the student is referring to from the conversation, so that a follow-up like
    "what about for them?" becomes something a document search can match.
    """
    query = (
        query
        or (state or {}).get("question")
        or (state or {}).get("raw_question")
        or ""
    )
    try:
        hits = get_store().similarity_search_with_relevance_scores(query, k=TOP_K * 2)
    except Exception:  # noqa: BLE001 - an unbuilt index yields no context, never a 500
        hits = []
    kept = [(d, s) for d, s in rerank(query, hits) if s >= MIN_RELEVANCE][:TOP_K]
    if not kept:
        return _done(tool_call_id, f"No passage matched {query!r}.")
    context = format_context([doc for doc, _ in kept])
    return _done(
        tool_call_id,
        f"{len(kept)} passages retrieved for {query!r}.",
        blocks={"documents": f"Reference documents:\n\n{context}"},
        sources=source_payload(kept),
        retrieved_text=context,
    )


@tool
def lookup_result(
    reason: str = "",
    state: Annotated[dict | None, InjectedState] = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> Command:
    """Look a candidate up in the published entrance pass list.

    Use this whenever the student is asking about a specific candidate's result: a form
    number, a merit rank, a person's name, who topped, or the best-ranked candidates from
    a district. Say in `reason` what is being looked for, in a few words.

    Do not pass the form number or rank yourself -- this reads the student's own message.
    """
    asked = (state or {}).get("raw_question") or ""
    # A rank inside a chances question belongs to the student and is hypothetical.
    # Looking it up would attach a stranger's name and district to it -- see
    # results.lookup_context's skip_ranks, which exists for exactly this.
    block = results.lookup_context(asked, skip_ranks=cutoffs.is_cutoff_question(asked))
    if not block:
        return _done(
            tool_call_id,
            "No form number, rank, name or district in the message to look up.",
        )
    return _done(
        tool_call_id, f"Pass list record found ({reason}).", blocks={"lookup": block}
    )


@tool
def fee_totals(
    category: str = "",
    state: Annotated[dict | None, InjectedState] = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> Command:
    """Worked-out fees for studying at Pulchowk Campus: one semester, the whole degree,
    what is due on admission day, and the refundable deposits (धरौती).

    Use this for what it costs to study. Pass `category` only if the student has said
    which they are, and pass it exactly as one of: Regular, Full Fee, Foreign Student,
    Sponsored. Leave it empty otherwise -- the block then quotes the Regular rate and
    says so.

    Do NOT use this for the entrance examination fee or the application form fee. Those
    are different money, answered by the payment notices through search_documents.
    """
    raw = (state or {}).get("raw_question") or ""
    english = (state or {}).get("question") or ""
    earlier = previous_question((state or {}).get("messages") or [])
    named = " ".join(filter(None, [raw, english, _category(category) or ""]))
    block = (
        fees.fee_context(raw, carried=earlier)
        or fees.fee_context(english, carried=earlier)
        or fees.fee_context(named, force=True, carried=f"{raw}\n{earlier}")
    )
    if not block:
        return _done(
            tool_call_id,
            "Not a study-fee question -- this looks like the entrance or form fee, "
            "which the payment notices cover.",
        )
    return _done(tool_call_id, "Fee figures assembled.", blocks={"fees": block})


@tool
def seat_counts(
    campus: str = "",
    programme: str = "",
    state: Annotated[dict | None, InjectedState] = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> Command:
    """How many students each campus and affiliated college admits, per programme,
    split into Regular and Full Fee.

    Use this for how many seats or places a programme has, which campuses offer a
    programme, or how large an intake is. Pass an empty string for either argument to get
    the whole column or the whole row.

    These are intake targets. They cannot say whether a rank is good enough for a
    programme, and this tool will not answer that.
    """
    raw = (state or {}).get("raw_question") or ""
    asked = " ".join(filter(None, [raw, campus, programme]))
    block = seats.seat_context(asked, force=True)
    return _done(tool_call_id, "Seat figures assembled.", blocks={"seats": block})


@tool
def priority_rules(
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> Command:
    """Pulchowk's rules for ranking programme priorities on the admission form.

    Use this for how the priority order works, what happens when a student is published
    in a lower priority than they wanted, whether they can refuse a seat and wait for a
    better one, whether they can move down, and how a Full Fee programme ranked above a
    Regular one can force a larger payment. Also use it whenever a student is deciding
    what order to put programmes in.
    """
    return _done(
        tool_call_id,
        "Priority rules supplied.",
        blocks={"priority": priority.priority_context()},
    )


@tool
def priority_chance(
    state: Annotated[dict | None, InjectedState] = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> Command:
    """What a student's rank would actually have been placed into at Pulchowk, worked out
    from the published priority applications rather than from a past year's cutoff.

    Use this when a student gives their entrance rank and asks which programmes they can
    realistically get at Pulchowk, what to put first, or whether a particular programme is
    a realistic first priority. Prefer it over cutoff_standing for Pulchowk, because it is
    computed from who actually applied this year rather than from last year's outcome.

    Pulchowk only, and open category only. Returns nothing if the question names another
    campus or gives no rank.
    """
    raw = (state or {}).get("raw_question") or ""
    block = priority.chance_context(raw)
    if not block:
        return _done(
            tool_call_id,
            "Not a Pulchowk priority question, or no rank given.",
        )
    return _done(
        tool_call_id, "Priority allocation worked out.", blocks={"chances": block}
    )


@tool
def cutoff_standing(
    campus: str = "",
    programme: str = "",
    category: str | None = None,
    state: Annotated[dict | None, InjectedState] = None,
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> Command:
    """What entrance rank actually got into a programme in previous years, and where a
    student's own rank would have stood against it.

    Use this whenever a student gives their rank and asks what they can get, whether a
    rank is enough for a programme or campus, what a cutoff or closing rank was, or how
    their chances look. Leave programme empty for "what can I get with my rank".

    Covers the four campuses that publish comparable figures -- Pulchowk, Thapathali,
    Pashchimanchal and Purwanchal -- for open/general category, first admission list only.
    """
    raw = (state or {}).get("raw_question") or ""

    # The rank is read from the student's own words, never from an argument. A model that
    # can pass a rank can invent one, and here that would be a fabricated number sitting
    # next to real cutoffs -- the one place in this app where that is worst.
    ranks = results.find_ranks(raw, include_topper=False)
    # Read from the student's words first; the model's argument is only a fallback, and
    # a category it cannot supply is better than one it guesses.
    kind = cutoffs.find_category(raw) or _category(category) or ""
    if kind not in cutoffs.CATEGORIES:
        # Sponsored and foreign seats are allocated separately and no cutoff exists for
        # them, so an unrecognised category means "not stated" rather than Regular.
        kind = ""

    named = seats.find_programmes(raw) or ([programme] if programme else [])
    where = seats.find_campuses(raw) or ([campus] if campus else [])
    places = where or list(cutoffs.covered_campuses())

    if named:
        # A named programme can be answered either way: with the student's rank if they
        # gave one, and as a plain history if they did not. "What was the cutoff for
        # Civil at Thapathali" does not need their rank and should not be asked for it.
        parts = [
            cutoffs.both_categories_context(ranks[0], place, named[0], kind)
            if ranks
            else cutoffs.history_context(place, named[0], kind or "Regular")
            for place in places
        ]
        block = "\n\n".join(part for part in parts if part)
        if not block:
            block = cutoffs.both_categories_context(
                ranks[0] if ranks else 0, places[0], named[0], kind
            )
    elif ranks:
        block = cutoffs.reachable_context(ranks[0], kind or "Regular")
    else:
        block = (
            "[Cutoff history: no rank and no programme given]\n"
            "The student is asking about their chances without saying their entrance "
            "rank or naming a programme. Ask for whichever is missing, in one sentence. "
            "Do not estimate, and do not answer from the number of seats -- a seat count "
            "says how many students a campus takes, not how far down the merit list it "
            "reached."
        )
    return _done(tool_call_id, "Cutoff history assembled.", blocks={"cutoffs": block})


@tool
def convert_bs_date(
    bs_date: str = "",
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> Command:
    """Convert a Bikram Sambat date to the Gregorian calendar and say how far off it is.

    Use this whenever a specific BS date needs to be given in both calendars or measured
    against today. Pass it as printed, for example 2083/05/07.
    """
    block = annotate_dates(bs_date)
    if not block:
        return _done(tool_call_id, f"{bs_date!r} is not a date this can read.")
    return _done(tool_call_id, "Date converted.", blocks={"dates": block})


@tool
def latest_notices(
    tool_call_id: Annotated[str, InjectedToolCallId] = "",
) -> Command:
    """The most recent notices published on the official IOE and campus sites.

    Use this when the student asks whether something has been published, whether there is
    anything new, or what the latest notice is. It gives titles and dates, never the
    contents of a notice.
    """
    block = notices.digest()
    if not block:
        return _done(tool_call_id, "The notice feed is empty.")
    return _done(tool_call_id, "Notice feed supplied.", blocks={"notices": block})


TOOLS = [
    search_documents,
    lookup_result,
    fee_totals,
    seat_counts,
    priority_rules,
    priority_chance,
    cutoff_standing,
    convert_bs_date,
    latest_notices,
]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}
