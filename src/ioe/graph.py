"""The conversation graph: choose the evidence, then answer from it.

    START ─(route_question)─┬─► small_talk ────────────────────────────┐
                            │                                          ▼
                            └─► prepare ─(deflect?)─┬─► deflect ─► END │
                                                    │                  │
                                                    └─► plan ─► tools ─┴─► assemble ─► answer ─┬─► summarize ─► END
                                                          ▲              │                    └─► END
                                                          └──(rounds)────┘

Two model calls on an ordinary turn, where the old graph made five. The planner reads the
conversation and picks tools; `search_documents(query=...)` is the standalone-query
rewrite, so that one call does the work `rewrite_query` and `is_in_scope` used to do
separately, and `best_match`'s embedding call is gone with them.

Three things here are load-bearing and none of them are obvious.

**The model's tool choice is additive only.** `ensure_default_calls` puts back everything
today's unconditional pipeline guaranteed: retrieval always runs, and the pass-list and
fee lookups run whenever their detectors fire, whatever the planner did or did not ask
for. Ollama ignores `tool_choice` (langchain_ollama marks the argument unused), so there
is no way to require a call at the model layer -- it has to be required here. The floor
this sets is the important part: if tool selection fails completely, the turn degrades to
exactly the old pipeline plus one wasted planner call.

**Tool results do not go into the prompt as ToolMessages.** They are re-rendered by
`tools.render_blocks` in a fixed order. ToolMessages would arrive in call order, decided
by a 7B model, and `fees.fee_context` records what that costs: placed ahead of the
retrieved documents the worked fee figures were ignored and the model went back to the
raw tables and multiplied. The app keeps the placement.

**There is no scope classifier.** Issue 24 is a report of one refusing `foreign?` and
`what is its source` -- a follow-up judged as though it were a whole message looks like
nothing at all. A question with no evidence behind it now gets `UNCOVERED_BLOCK` and a
real reply that stays in the conversation. The only thing still turned away outright is
task substitution, in `scope.py`, and only because the prompt was measured failing at it.
"""

import asyncio
from typing import Annotated

import aiosqlite
from langchain_core.messages import (
    AIMessage,
    AnyMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
)
from langchain_ollama import ChatOllama
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.constants import TAG_NOSTREAM
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import REMOVE_ALL_MESSAGES, MessagesState, add_messages
from langgraph.prebuilt import ToolNode

from ioe import cutoffs, fees, priority, results, seats
from ioe.dates import annotate_dates, today_context
from ioe.fees import FEE_SOURCE
from ioe.language import (
    english_only_preface,
    read_in_english,
    without_language_request,
)
from ioe.memory import (
    previous_question,
    recent_messages,
    should_summarize,
    summarize,
    unseen,
)
from ioe.priority import PRIORITY_SOURCE
from ioe.prompts import (
    CONVERSATION_HEADER,
    PLANNER_PROMPT,
    SYSTEM_PROMPT,
    UNCOVERED_BLOCK,
)
from ioe.rag import MAX_SOURCES, NUM_CTX, OLLAMA_URL, keep_grounded
from ioe.results import RESULT_SOURCE
from ioe.scope import OFF_TOPIC_SENTENCE, is_small_talk, is_task_substitution
from ioe.seats import SEAT_SOURCE
from ioe.threads import DB_PATH
from ioe.tools import EVIDENCE_BLOCKS, TOOLS, render_blocks, settled_lines

TEXT_MODEL = "qwen2.5:7b"

# One round: the planner picks tools, they run, the answer is written. Raising this needs
# dedupe across rounds first -- a 7B model handed what it asked for is likelier to ask
# again than to ask for something better.
MAX_TOOL_ROUNDS = 1

model = ChatOllama(model=TEXT_MODEL, base_url=OLLAMA_URL, num_ctx=NUM_CTX)

# The planner has the tools bound; the answering model does not, and cannot emit a tool
# call as a result. That is the first and most structural layer of the streaming filter:
# api.py forwards tokens from the `answer` node, and nothing else can produce them there.
planner = model.bind_tools(TOOLS)


# ── State ─────────────────────────────────────────────────────────────────────
# Every turn-scoped key is cleared by fresh_turn() and nowhere else. State survives the
# turn it was made on, and forgetting one key has twice produced the same bug: the
# previous question's evidence answering this question, and the previous question's
# citations printed underneath.


def merge_blocks(left: dict | None, right: dict | None) -> dict:
    """Accumulate blocks within a turn. None is the reset, and it is JSON, so it
    survives the checkpointer."""
    return {} if right is None else {**(left or {}), **right}


def add_sources(left: list | None, right: list | None) -> list:
    """Accumulate citations, one per file, first occurrence winning."""
    if right is None:
        return []
    out = list(left or [])
    seen = {s.get("file") for s in out}
    for source in right:
        if source.get("file") not in seen:
            out.append(source)
            seen.add(source.get("file"))
    return out


class ChatState(MessagesState):
    # Exactly what the student typed. Tools that must not be handed a paraphrase read
    # this: a form number survives no translation.
    raw_question: str
    # The same question with any "reply in Nepali" removed and translated to English.
    question: str
    blocks: Annotated[dict[str, str], merge_blocks]
    sources: Annotated[list[dict], add_sources]
    # Tool traffic. Never shown to the student and never in `messages`.
    scratch: Annotated[list[AnyMessage], add_messages]
    retrieved_text: str
    rounds: int
    # Long-term memory, and how much of the transcript it accounts for.
    summary: str
    summarized_upto: int
    # A greeting: no evidence needed, and no "nothing matched" note either.
    social: bool
    # The app's own sentence when a turn is deflected, or "".
    refusal: str


def fresh_turn() -> dict:
    """Every turn-scoped key, cleared. The one place this list exists."""
    return {
        "blocks": None,
        "sources": None,
        # Not []. `scratch` reduces with add_messages, which reads an empty list as
        # "append nothing" and leaves last turn's tool traffic in place -- which would
        # put the previous question's tool calls into this question's planner prompt.
        # Clearing a message channel takes the sentinel.
        "scratch": [RemoveMessage(id=REMOVE_ALL_MESSAGES)],
        "retrieved_text": "",
        "rounds": 0,
        "social": False,
        "refusal": "",
    }


# ── Entry ─────────────────────────────────────────────────────────────────────


def route_question(state: ChatState) -> str:
    """Whether this turn needs evidence at all."""
    return "small_talk" if is_small_talk(state["messages"][-1].content) else "prepare"


def small_talk(state: ChatState) -> dict:
    """A greeting or a thank-you: answered from the system prompt and the conversation."""
    asked = state["messages"][-1].content
    return {
        **fresh_turn(),
        "raw_question": asked,
        "question": asked,
        "social": True,
    }


def prepare(state: ChatState) -> dict:
    """Settle what the question is, and decide whether it is a question for us."""
    asked = state["messages"][-1].content
    question = read_in_english(without_language_request(asked))
    return {
        **fresh_turn(),
        "raw_question": asked,
        "question": question,
        # Checked on both, because the detector reads English and a student may not have
        # written in it. Cheap: both are already in hand.
        "refusal": (
            OFF_TOPIC_SENTENCE
            if is_task_substitution(asked) or is_task_substitution(question)
            else ""
        ),
    }


def route_after_prepare(state: ChatState) -> str:
    return "deflect" if state.get("refusal") else "plan"


def deflect(state: ChatState) -> dict:
    """The app's own words, with no model call.

    The turn stays in the transcript, which is the whole difference from the guard this
    replaces: the next message still has its context, so a student who asks something
    off-topic and then returns to their real question is not starting again.
    """
    return {"messages": AIMessage(content=state["refusal"])}


# ── Planning ──────────────────────────────────────────────────────────────────


def _call(name: str, args: dict, index: int) -> dict:
    return {"name": name, "args": args, "id": f"auto_{index}", "type": "tool_call"}


def ensure_default_calls(calls: list[dict], state: ChatState) -> list[dict]:
    """Everything the old unconditional pipeline guaranteed, guaranteed again.

    The model may add tools. It may not take these away. `retrieve` and `lookup_result`
    ran on every turn before this rewrite and their detectors are unchanged -- what is
    new is only that the model can now ask for more than the regexes found.
    """
    named = {c["name"] for c in calls}
    out = list(calls)
    raw = state.get("raw_question") or ""
    english = state.get("question") or raw

    if "search_documents" not in named:
        out.append(_call("search_documents", {"query": english}, len(out)))
    # skip_ranks because a rank inside a chances question is the student's own, stated
    # hypothetically. Looking it up answers a question nobody asked, with an unrelated
    # candidate's name and district, next to real cutoff figures.
    chances = cutoffs.is_own_rank(raw) or cutoffs.is_own_rank(english)
    if "lookup_result" not in named and results.lookup_context(raw, skip_ranks=chances):
        out.append(
            _call(
                "lookup_result", {"reason": "the message names a candidate"}, len(out)
            )
        )
    if "fee_totals" not in named and (
        fees.is_fee_question(raw) or fees.is_fee_question(english)
    ):
        out.append(_call("fee_totals", {"category": None}, len(out)))
    if "seat_counts" not in named and (
        seats.is_seat_question(raw) or seats.is_seat_question(english)
    ):
        out.append(_call("seat_counts", {"campus": "", "programme": ""}, len(out)))
    if "cutoff_standing" not in named and (
        cutoffs.is_cutoff_question(raw) or cutoffs.is_cutoff_question(english)
    ):
        out.append(_call("cutoff_standing", {"campus": "", "programme": ""}, len(out)))
    if "priority_chance" not in named and priority.chance_context(raw):
        out.append(_call("priority_chance", {}, len(out)))
    if "priority_rules" not in named and (
        priority.is_rules_question(raw) or priority.is_rules_question(english)
    ):
        out.append(_call("priority_rules", {}, len(out)))
    return out


def plan(state: ChatState) -> dict:
    """Ask the model which sources this turn needs, then add the ones it must have."""
    prompt: list[AnyMessage] = [SystemMessage(content=PLANNER_PROMPT)]
    if state.get("summary"):
        prompt.append(SystemMessage(content=CONVERSATION_HEADER + state["summary"]))
    prompt += recent_messages(state["messages"][:-1])

    prompt.append(HumanMessage(content=state.get("question") or ""))
    prompt += state.get("scratch") or []

    try:
        # nostream keeps the planner's tokens out of the messages stream. It is a belt:
        # api.py filters on node name, which is what actually guarantees it.
        chosen = planner.invoke(prompt, config={"tags": [TAG_NOSTREAM]})
        calls = list(chosen.tool_calls or [])
    except Exception:  # noqa: BLE001 - a planner that cannot run falls back to the floor
        calls = []

    if state.get("rounds", 0) == 0:
        calls = ensure_default_calls(calls, state)
    return {
        "scratch": [AIMessage(content="", tool_calls=calls)],
        "rounds": state.get("rounds", 0) + 1,
    }


def route_after_plan(state: ChatState) -> str:
    last = (state.get("scratch") or [])[-1] if state.get("scratch") else None
    return "tools" if getattr(last, "tool_calls", None) else "assemble"


def route_after_tools(state: ChatState) -> str:
    return "plan" if state.get("rounds", 0) < MAX_TOOL_ROUNDS else "assemble"


# ── Answering ─────────────────────────────────────────────────────────────────


def _pinned(blocks: dict, sources: list[dict]) -> list[dict]:
    """Put the exact tables ahead of whatever retrieval also happened to match.

    A figure taken from the fee schedule is cited to the fee schedule, whatever else was
    in the prompt. Same for the pass list, the seat table and the priority rules: those
    blocks are the notice's own content, so the notice is named outright rather than
    being put to the keep_grounded test that retrieved passages face.
    """
    for name, source in (
        ("lookup", RESULT_SOURCE),
        ("fees", FEE_SOURCE),
        ("seats", SEAT_SOURCE),
        ("priority", PRIORITY_SOURCE),
    ):
        if blocks.get(name):
            sources = [
                source,
                *(s for s in sources if s.get("file") != source.get("file")),
            ]
    return sources


def enforce_floor(blocks: dict[str, str], state: ChatState) -> dict[str, str]:
    """Put back any exact table the detectors called for and the tools did not deliver.

    ensure_default_calls guarantees the call is *made*. That turned out not to be the
    same as guaranteeing the block arrives, and the gap was expensive: the planner
    emitted category="full_fee" for fee_totals, the argument failed schema validation,
    the call errored, and the turn lost its fee figures while every other tool succeeded.
    Nine of the suite's fifty-three cases, failing in a way that looked exactly like the
    detector missing.

    The tool arguments are tolerant now, so that particular fault is fixed at source.
    This is the second line: whatever the model asked for and whatever the tools did,
    a question the detectors recognise ends up with its figures. The floor is what the
    old unconditional pipeline gave for free, and it should not be conditional on a 7B
    model getting an argument right.
    """
    raw = state.get("raw_question") or ""
    english = state.get("question") or raw
    blocks = dict(blocks)

    if not blocks.get("fees") and (
        fees.is_fee_question(raw) or fees.is_fee_question(english)
    ):
        earlier = previous_question(state.get("messages") or [])
        recovered = fees.fee_context(raw, carried=earlier) or fees.fee_context(
            english, carried=earlier
        )
        if recovered:
            blocks["fees"] = recovered

    if not blocks.get("lookup"):
        recovered = results.lookup_context(raw, skip_ranks=cutoffs.is_own_rank(raw))
        if recovered:
            blocks["lookup"] = recovered

    if not blocks.get("seats") and (
        seats.is_seat_question(raw) or seats.is_seat_question(english)
    ):
        recovered = seats.seat_context(raw) or seats.seat_context(english)
        if recovered:
            blocks["seats"] = recovered

    # The rules are the highest-stakes prose in the corpus -- section 5 is the one that
    # says an applicant who turns down a lower priority is out of the process entirely --
    # and whether they appeared was left to the planner, which is to say to chance. It
    # came and went between identical runs of the suite.
    if not blocks.get("priority") and (
        priority.is_rules_question(raw) or priority.is_rules_question(english)
    ):
        blocks["priority"] = priority.priority_context()

    # Pulchowk's own allocation, when the question is one it can answer. This is better
    # evidence than a past year's cutoff -- it is computed from who actually applied --
    # so it goes in whatever the planner chose.
    if not blocks.get("chances"):
        recovered = priority.chance_context(raw)
        if recovered:
            blocks["chances"] = recovered

    # The allocation supersedes the published cutoffs where both could speak. Measured
    # with both present, the model quoted a 2082 cutoff inside an answer about the 2083
    # simulation: two sets of rank figures about the same programmes is one set too many,
    # and the one computed from who actually applied is the better one.
    #
    # Emptied rather than deleted, because `blocks` reduces with merge_blocks and a
    # dropped key is simply re-supplied from the accumulated state on the next merge.
    # render_blocks and the eval's evidence() both read an empty string as absent.
    # Both blocks now stand together, and they answer different questions: `chances` is
    # this year's actual allocation at Pulchowk, `cutoffs` is how the same programme's
    # closing rank moved across four published years. A student choosing wants both.
    #
    # They did not always coexist. With the cutoff history written as one line of four
    # year:rank pairs, the model pulled a 2082 figure into an answer about the 2083
    # simulation, and `cutoffs` was cleared whenever `chances` was present. Rewriting the
    # history as one labelled line per year -- with the verdict welded to each -- removed
    # the conflation, measured, so the suppression is gone rather than kept as a charm.
    # A rank sitting in a prompt beside a seat count, with no cutoff block to say what a
    # rank actually reached, is the exact confusion SYSTEM_PROMPT has a rule against. If
    # the detector says this is a chances question, the cutoff figures are in the prompt
    # whatever the planner did.
    if (
        not blocks.get("chances")
        and not blocks.get("cutoffs")
        and (cutoffs.is_cutoff_question(raw) or cutoffs.is_cutoff_question(english))
    ):
        ranks = results.find_ranks(raw, include_topper=False)
        programmes = seats.find_programmes(raw)
        places = seats.find_campuses(raw) or cutoffs.covered_campuses()
        # The category comes from the student's own words, not from a default. Asked about
        # Full Fee, this used to build a Regular block and answer confidently from it.
        asked = cutoffs.find_category(raw) or cutoffs.find_category(english)
        if programmes:
            parts = [
                cutoffs.both_categories_context(ranks[0], place, programmes[0], asked)
                if ranks
                else cutoffs.history_context(place, programmes[0], asked or "Regular")
                for place in places
            ]
            recovered = "\n\n".join(part for part in parts if part)
            if recovered:
                blocks["cutoffs"] = recovered
        elif ranks:
            blocks["cutoffs"] = cutoffs.reachable_context(ranks[0])

    return blocks


def assemble(state: ChatState) -> dict:
    """Finish the evidence for this turn, before anything is written.

    Separate from `answer` because deciding what the model will be shown and calling the
    model are two jobs, and only the first one is worth inspecting. The eval suite stops
    the graph here: it asserts on which evidence a turn assembled, which is deterministic
    and takes a second, rather than on the prose, which is neither.
    """
    blocks = dict(state.get("blocks") or {})
    blocks = enforce_floor(blocks, state)

    if state.get("summary"):
        blocks["summary"] = CONVERSATION_HEADER + state["summary"]

    # Dates are read out of the question and whatever was retrieved, as before, so the
    # model reads conversions rather than attempting calendar arithmetic.
    if not blocks.get("dates"):
        found = annotate_dates(
            f"{state.get('question') or ''}\n{state.get('retrieved_text') or ''}"
        )
        if found:
            blocks["dates"] = found

    # Nothing matched. Say so rather than improvising -- this is what replaces the scope
    # guard for a question that is real and simply unanswerable. A greeting is exempt:
    # "thanks" needs no evidence and no apology for having none.
    if not state.get("social") and not any(blocks.get(b) for b in EVIDENCE_BLOCKS):
        blocks["uncovered"] = UNCOVERED_BLOCK

    return {"blocks": blocks}


def answer(state: ChatState) -> dict:
    blocks = state.get("blocks") or {}

    prompt: list[AnyMessage] = [SystemMessage(content=today_context())]
    prompt += [SystemMessage(content=text) for text in render_blocks(blocks)]
    # After the evidence, because SYSTEM_PROMPT opens with "Answer from the blocks
    # above" and because the rules it carries -- never predict admission chances, never
    # compare a rank against a seat count -- are the ones that must survive contact with
    # a prompt that now contains real seat numbers.
    prompt.append(SystemMessage(content=SYSTEM_PROMPT))

    prompt += recent_messages(state["messages"][:-1])

    # Last of all, nearest the question: any figure the app has already settled. On a
    # follow-up the conversation above carries the *previous* answer, which is closer to
    # the question than the block that settled this one -- and the model answered from it.
    settled = settled_lines(blocks)
    if settled:
        prompt.append(
            SystemMessage(
                content="Answer this turn from these, which are already worked out:\n"
                + "\n".join(settled)
            )
        )

    prompt.append(HumanMessage(content=state.get("question") or ""))

    written = model.invoke(prompt)

    preface = english_only_preface(state.get("raw_question") or "")
    if preface:
        written.content = preface + (written.content or "")

    sources = keep_grounded(
        written.content or "",
        state.get("question") or "",
        state.get("sources") or [],
    )
    sources = _pinned(blocks, sources)
    if sources:
        written.additional_kwargs["sources"] = sources[:MAX_SOURCES]
    return {"messages": written}


def route_after_answer(state: ChatState) -> str:
    return (
        "summarize"
        if should_summarize(state["messages"], state.get("summarized_upto", 0))
        else END
    )


def summarize_node(state: ChatState) -> dict:
    """Fold the last few turns into the running summary.

    After the answer, so the student has already read it -- only the SSE `done` event
    waits on this, never the first token.
    """
    messages = state["messages"]
    upto = state.get("summarized_upto", 0)
    return {
        "summary": summarize(state.get("summary", ""), unseen(messages, upto)),
        "summarized_upto": len(messages),
    }


# ── Wiring ────────────────────────────────────────────────────────────────────

graph = StateGraph(ChatState)
graph.add_node("prepare", prepare)
graph.add_node("small_talk", small_talk)
graph.add_node("deflect", deflect)
graph.add_node("plan", plan)
graph.add_node(
    "tools", ToolNode(TOOLS, messages_key="scratch", handle_tool_errors=True)
)
graph.add_node("assemble", assemble)
graph.add_node("answer", answer)
graph.add_node("summarize", summarize_node)

graph.add_conditional_edges(
    START, route_question, {"prepare": "prepare", "small_talk": "small_talk"}
)
graph.add_edge("small_talk", "assemble")
graph.add_conditional_edges(
    "prepare", route_after_prepare, {"deflect": "deflect", "plan": "plan"}
)
graph.add_edge("deflect", END)
graph.add_conditional_edges(
    "plan", route_after_plan, {"tools": "tools", "assemble": "assemble"}
)
graph.add_conditional_edges(
    "tools", route_after_tools, {"plan": "plan", "assemble": "assemble"}
)
graph.add_conditional_edges(
    "answer", route_after_answer, {"summarize": "summarize", END: END}
)
graph.add_edge("assemble", "answer")
graph.add_edge("summarize", END)


# Checkpoints live in the same SQLite file as the conversation index. Unchanged from
# before the rewrite, including why it is not built at import: AsyncSqliteSaver binds to
# the running event loop in its constructor, and at import time there isn't one.
_lock = asyncio.Lock()
_chatbot = None


async def get_chatbot():
    """The compiled graph, built on first use."""
    global _chatbot
    if _chatbot is None:
        async with _lock:
            if _chatbot is None:
                DB_PATH.parent.mkdir(parents=True, exist_ok=True)
                saver = AsyncSqliteSaver(aiosqlite.connect(DB_PATH))
                await saver.setup()
                _chatbot = graph.compile(checkpointer=saver)
    return _chatbot
