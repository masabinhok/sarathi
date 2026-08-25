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

from typing import Annotated, Literal

from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command

from ioe import fees, notices, priority, results, seats
from ioe.dates import annotate_dates
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
#   priority   Pulchowk's priority-order rules
#   cutoffs    what rank was actually admitted, when that is known
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
    "cutoffs",
    "documents",
    "fees",
    "uncovered",
)

# The blocks that count as evidence. A turn that assembles none of these has nothing to
# answer from, and gets the `uncovered` instruction instead of being left to improvise.
EVIDENCE_BLOCKS = ("lookup", "seats", "priority", "cutoffs", "documents", "fees")


def render_blocks(blocks: dict[str, str]) -> list[str]:
    """The blocks present, in the house order. Unknown keys are dropped, not appended."""
    return [blocks[name] for name in BLOCK_ORDER if blocks.get(name)]


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
    query: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Search the official IOE admission notices, the admission booklet and the entrance
    syllabus for passages that answer a question.

    Use this for eligibility, required documents, application steps, quotas, exam format
    and marking, syllabus topics, campuses and programmes, payment procedures, and
    anything else the published notices would cover. Pass a standalone query: resolve
    what the student is referring to from the conversation, so that a follow-up like
    "what about for them?" becomes something a document search can match.
    """
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
    reason: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Look a candidate up in the published entrance pass list.

    Use this whenever the student is asking about a specific candidate's result: a form
    number, a merit rank, a person's name, who topped, or the best-ranked candidates from
    a district. Say in `reason` what is being looked for, in a few words.

    Do not pass the form number or rank yourself -- this reads the student's own message.
    """
    asked = state.get("raw_question") or ""
    block = results.lookup_context(asked)
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
    category: Literal["Regular", "Full Fee", "Foreign Student", "Sponsored"] | None,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """Worked-out fees for studying at Pulchowk Campus: one semester, the whole degree,
    what is due on admission day, and the refundable deposits (धरौती).

    Use this for what it costs to study. Leave `category` empty unless the student has
    said which they are -- the block then quotes the Regular rate and says so.

    Do NOT use this for the entrance examination fee or the application form fee. Those
    are different money, answered by the payment notices through search_documents.
    """
    raw = state.get("raw_question") or ""
    english = state.get("question") or ""
    named = " ".join(filter(None, [raw, english, category or ""]))
    block = (
        fees.fee_context(raw)
        or fees.fee_context(english)
        or fees.fee_context(named, force=True)
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
    campus: str,
    programme: str,
    state: Annotated[dict, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """How many students each campus and affiliated college admits, per programme,
    split into Regular and Full Fee.

    Use this for how many seats or places a programme has, which campuses offer a
    programme, or how large an intake is. Pass an empty string for either argument to get
    the whole column or the whole row.

    These are intake targets. They cannot say whether a rank is good enough for a
    programme, and this tool will not answer that.
    """
    raw = state.get("raw_question") or ""
    asked = " ".join(filter(None, [raw, campus, programme]))
    block = seats.seat_context(asked, force=True)
    return _done(tool_call_id, "Seat figures assembled.", blocks={"seats": block})


@tool
def priority_rules(tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
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
def convert_bs_date(
    bs_date: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
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
def latest_notices(tool_call_id: Annotated[str, InjectedToolCallId]) -> Command:
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
    convert_bs_date,
    latest_notices,
]
TOOLS_BY_NAME = {t.name: t for t in TOOLS}
