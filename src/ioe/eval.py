"""A replay of the behaviours the closed issues established.

There has never been a test suite here. Twenty-three issues were verified by hand against
the running bot and the counts written into `issues.md` as prose -- "26 fee questions,
every figure correct", "8/8 bare follow-ups answered" -- which records that the work was
done but leaves nothing behind that can say whether it still is. Issue `26` rewrites the
graph, so that has to change before the rewrite starts, not after.

What is asserted here is **which evidence the graph assembled**, never the prose it wrote.
A question about the dharauti must put the worked fee figures in the prompt; a question
carrying a form number must put the pass list record there. Whether the sentence around
the figure is well phrased is a judgement, and a judgement needs a judge -- but whether
the figure was in front of the model at all is a fact, it is the thing that actually
breaks, and it costs no model call to check.

That also makes the suite portable across the rewrite. Today the evidence lives in four
separate state keys; on the branch it lives in one `blocks` dict. `evidence()` reads
either, so the same cases give a before-and-after on the same axis.

    uv run python -m ioe.eval            # everything
    uv run python -m ioe.eval fees       # one group
"""

import asyncio
import sys
import time
import uuid

from langchain_core.messages import HumanMessage

# The names a case asserts on. On the current graph these are separate state keys; after
# the rewrite they are keys of `blocks`. Kept as one vocabulary so the cases do not move.
DOCUMENTS = "documents"
LOOKUP = "lookup"
FEES = "fees"
SEATS = "seats"
PRIORITY = "priority"
NOTICES = "notices"
REFUSED = "refused"


def evidence(state: dict) -> set[str]:
    """Which evidence this turn put in front of the model.

    Reads the current graph's state keys and the rewrite's `blocks` dict, because the
    point of the suite is to compare them. A key that is present but empty counts as
    absent: retrieval that matched nothing is not evidence, and both graphs write an
    empty string rather than dropping the key, so that the previous turn's documents
    cannot leak into this one.
    """
    blocks = state.get("blocks")
    if isinstance(blocks, dict):
        found = {name for name, text in blocks.items() if text}
    else:
        found = set()
        if state.get("context"):
            found.add(DOCUMENTS)
        if state.get("lookup"):
            found.add(LOOKUP)
        if state.get("fees"):
            found.add(FEES)
    if state.get("refusal"):
        found.add(REFUSED)
    return found


# ── Cases ─────────────────────────────────────────────────────────────────────
# (group, question, must be present, must be absent)
#
# `must be absent` is as load-bearing as `must be present` and is where the subtle
# regressions show up. A fee question that also refuses is broken even though the figures
# arrived; an entrance-exam-fee question that fires the study-fee block is the failure
# `_OTHER_MONEY` exists to prevent.

CASES: list[tuple[str, str, set[str], set[str]]] = [
    # ── Fees. Seeded from issue 23, including the four questions it opens with and the
    # label collisions that took five rounds of layout to settle.
    ("fees", "how much do i have to pay as a regular student", {FEES}, {REFUSED}),
    ("fees", "what is the total fee for a regular student", {FEES}, {REFUSED}),
    ("fees", "how much is one semester", {FEES}, {REFUSED}),
    ("fees", "how much is the dharauti", {FEES}, {REFUSED}),
    ("fees", "धरौती कति हो", {FEES}, {REFUSED}),
    ("fees", "how much is the library deposit", {FEES}, {REFUSED}),
    (
        "fees",
        "what does the whole degree cost for a full fee student",
        {FEES},
        {REFUSED},
    ),
    ("fees", "how much does a foreign student pay", {FEES}, {REFUSED}),
    ("fees", "what is the sponsored fee at admission", {FEES}, {REFUSED}),
    ("fees", "how much is the health insurance fee", {FEES}, {REFUSED}),
    ("fees", "is any of it refundable", {FEES}, {REFUSED}),
    ("fees", "tuition fee per semester", {FEES}, {REFUSED}),
    # The other money. Issue 23 records these as the reason _OTHER_MONEY exists: the
    # entrance fee and the form fee are answered by the payment notices, not the schedule.
    ("fees", "how much is the entrance exam fee", set(), {FEES, REFUSED}),
    ("fees", "what is the application form fee", set(), {FEES, REFUSED}),
    ("fees", "how do i pay with esewa", {DOCUMENTS}, {FEES, REFUSED}),
    # ── Pass list. Issue 21 widened this from form numbers and ranks to names and
    # districts; issue 1 is the original rank lookup.
    ("results", "did form 2083-4567 pass", {LOOKUP}, {REFUSED}),
    ("results", "who is rank 13", {LOOKUP}, {REFUSED}),
    ("results", "who topped the entrance exam", {LOOKUP}, {REFUSED}),
    ("results", "what rank did Ritesh Dawadi get", {LOOKUP}, {REFUSED}),
    ("results", "who are the top candidates from Chitawan", {LOOKUP}, {REFUSED}),
    ("results", "2083-2 ko rank kati ho", {LOOKUP}, {REFUSED}),
    # A number that is not on the list still has to reach the lookup: issue 21 records
    # that saying "not found" is the answer, and inventing a candidate is the failure.
    ("results", "did form 2083-99999 pass", {LOOKUP}, {REFUSED}),
    # ── Ordinary retrieval.
    ("docs", "what documents do i need for the women quota", {DOCUMENTS}, {REFUSED}),
    ("docs", "what is the entrance exam syllabus for physics", {DOCUMENTS}, {REFUSED}),
    ("docs", "how many marks is the entrance exam", {DOCUMENTS}, {REFUSED}),
    ("docs", "which campuses offer architecture", {DOCUMENTS}, {REFUSED}),
    (
        "docs",
        "what happens if i do not take a lower priority seat",
        {DOCUMENTS},
        {REFUSED},
    ),
    ("docs", "am i eligible with a diploma", {DOCUMENTS}, {REFUSED}),
    # ── Language. Issue 19: the answer is English whatever the question was written in,
    # and the question still has to reach the documents.
    ("language", "प्रवेश परीक्षाको शुल्क कति हो", {DOCUMENTS}, {REFUSED}),
    (
        "language",
        "please reply in nepali, what documents do i need",
        {DOCUMENTS},
        {REFUSED},
    ),
    ("language", "answer in hindi: when is the exam", {DOCUMENTS}, {REFUSED}),
    # ── Scope. The half of issue 22's suite that has no history; the follow-ups that
    # need history are in CONVERSATIONS, which is where issue 24 says they belong.
    ("scope", "write me a python function to reverse a list", set(), {DOCUMENTS}),
    ("scope", "who won the world cup", set(), {DOCUMENTS}),
    ("scope", "lets go on a holiday", set(), {DOCUMENTS}),
    ("scope", "how do i apply to Kathmandu University", set(), {DOCUMENTS}),
    ("scope", "solve x^2 + 5x + 6 = 0", set(), {DOCUMENTS}),
    ("scope", "recommend a good laptop under 80000", set(), {DOCUMENTS}),
    # Real questions that issue 22 records the classifier getting wrong on its own.
    ("scope", "how many seats are there in pulchowk", {DOCUMENTS}, {REFUSED}),
    ("scope", "what is the women's quota", {DOCUMENTS}, {REFUSED}),
    ("scope", "which campus is best for civil", {DOCUMENTS}, {REFUSED}),
    ("scope", "when do applications close", {DOCUMENTS}, {REFUSED}),
]

# ── Conversations ─────────────────────────────────────────────────────────────
# One thread, turn by turn. This is what issue 24 is actually about: every one of these
# follow-ups is answerable, and every one of them is meaningless read on its own.
#
# (group, [(message, must be present, must be absent), ...])

CONVERSATIONS: list[tuple[str, list[tuple[str, set[str], set[str]]]]] = [
    (
        # Issue 24's own transcript, verbatim, including the typo.
        "issue24",
        [
            ("hi", set(), {REFUSED}),
            ("how much do i have to pay as a regular student", {FEES}, {REFUSED}),
            (
                "write me a python function to calculate sum of three numbers",
                set(),
                {FEES},
            ),
            ("and what other cateogry i could study in", set(), {REFUSED}),
            ("what is its source", set(), {REFUSED}),
            ("foreign?", {FEES}, {REFUSED}),
        ],
    ),
    (
        "follow-up",
        [
            ("what is the entrance exam fee", {DOCUMENTS}, {REFUSED}),
            ("how do i pay it?", {DOCUMENTS}, {REFUSED}),
            ("and the deadline?", set(), {REFUSED}),
            ("what did i just ask you about?", set(), {REFUSED}),
        ],
    ),
    (
        # Small talk must not inherit the previous question's evidence. Issue 12's bug:
        # "you're welcome" printed the fee notice as its source.
        "hygiene",
        [
            ("how much is the dharauti", {FEES}, {REFUSED}),
            ("thanks!", set(), {FEES, DOCUMENTS, LOOKUP, REFUSED}),
        ],
    ),
]


# ── Running ───────────────────────────────────────────────────────────────────
# A single-turn case asserts on evidence, and the evidence is settled before the
# answering node runs -- so that node is not run. Interrupting in front of it takes a
# case from about twenty seconds to about one, which is the difference between a suite
# that gets run during the rewrite and one that gets run at the end of it.
#
# Conversations do not get this. A follow-up is only a follow-up if the assistant
# actually replied, so those run in full, through the real checkpointer.


def _answer_node() -> str:
    """The name of the node that writes the answer, before or after the rewrite."""
    from ioe.graph import graph

    return "answer" if "answer" in graph.nodes else "chat_node"


def _probe():
    """The graph, stopped in front of the answering node, on a throwaway checkpointer."""
    from langgraph.checkpoint.memory import InMemorySaver

    from ioe.graph import graph

    return graph.compile(
        checkpointer=InMemorySaver(), interrupt_before=[_answer_node()]
    )


async def _run_turn(bot, thread: str, message: str) -> tuple[set[str], float]:
    started = time.time()
    state = await bot.ainvoke(
        {"messages": [HumanMessage(content=message)]},
        {"configurable": {"thread_id": thread}},
    )
    return evidence(state), time.time() - started


def _check(got: set[str], want: set[str], forbid: set[str]) -> str:
    missing = want - got
    present = forbid & got
    if missing:
        return f"missing {sorted(missing)}"
    if present:
        return f"unwanted {sorted(present)}"
    return ""


async def run(groups: set[str] | None = None) -> int:
    """Run the suite. Returns the number of failures."""
    from ioe.graph import get_chatbot

    probe = _probe()
    failures = 0
    total = 0

    for group, question, want, forbid in CASES:
        if groups and group not in groups:
            continue
        total += 1
        got, took = await _run_turn(probe, uuid.uuid4().hex, question)
        problem = _check(got, want, forbid)
        failures += bool(problem)
        mark = "FAIL" if problem else "ok  "
        print(f"{mark} {group:<9} {took:5.1f}s  {question[:52]:<52} {sorted(got)}")
        if problem:
            print(f"     ^ {problem}")

    bot = await get_chatbot()
    for group, turns in CONVERSATIONS:
        if groups and group not in groups:
            continue
        thread = uuid.uuid4().hex
        print(f"\n--- conversation: {group}")
        for message, want, forbid in turns:
            total += 1
            got, took = await _run_turn(bot, thread, message)
            problem = _check(got, want, forbid)
            failures += bool(problem)
            mark = "FAIL" if problem else "ok  "
            print(f"{mark} {group:<9} {took:5.1f}s  {message[:52]:<52} {sorted(got)}")
            if problem:
                print(f"     ^ {problem}")

    print(f"\n{total - failures}/{total} passed")
    return failures


def main() -> None:
    groups = set(sys.argv[1:]) or None
    raise SystemExit(1 if asyncio.run(run(groups)) else 0)


if __name__ == "__main__":
    main()
