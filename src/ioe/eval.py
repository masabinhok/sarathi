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
CUTOFFS = "cutoffs"
CHANCES = "chances"
NOTICES = "notices"
# Two different things, and collapsing them cost a false failure.
#
# DECLINED is the app refusing to act: the task-substitution detector, or the old graph's
# scope guard. No model call, the app's own sentence, nothing answered.
#
# UNCOVERED is "no source matched", which is a fact about the evidence and not a refusal.
# The turn still gets a real answer -- from the conversation, if that is what was asked
# about. Measured: after three turns about the entrance fee, "what did i just ask you
# about?" assembles no evidence, carries the uncovered block, and is answered correctly
# with "You asked about how to pay the IOE Entrance Exam fee."
DECLINED = "declined"
UNCOVERED = "uncovered"
TIMEOUT = "TIMED-OUT"


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
        found.add(DECLINED)
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
    ("fees", "how much do i have to pay as a regular student", {FEES}, {DECLINED}),
    ("fees", "what is the total fee for a regular student", {FEES}, {DECLINED}),
    ("fees", "how much is one semester", {FEES}, {DECLINED}),
    ("fees", "how much is the dharauti", {FEES}, {DECLINED}),
    ("fees", "धरौती कति हो", {FEES}, {DECLINED}),
    ("fees", "how much is the library deposit", {FEES}, {DECLINED}),
    (
        "fees",
        "what does the whole degree cost for a full fee student",
        {FEES},
        {DECLINED},
    ),
    ("fees", "how much does a foreign student pay", {FEES}, {DECLINED}),
    ("fees", "what is the sponsored fee at admission", {FEES}, {DECLINED}),
    ("fees", "how much is the health insurance fee", {FEES}, {DECLINED}),
    ("fees", "is any of it refundable", {FEES}, {DECLINED}),
    ("fees", "tuition fee per semester", {FEES}, {DECLINED}),
    # The other money. Issue 23 records these as the reason _OTHER_MONEY exists: the
    # entrance fee and the form fee are answered by the payment notices, not the schedule.
    ("fees", "how much is the entrance exam fee", set(), {FEES, DECLINED}),
    ("fees", "what is the application form fee", set(), {FEES, DECLINED}),
    ("fees", "how do i pay with esewa", {DOCUMENTS}, {FEES, DECLINED}),
    # ── Pass list. Issue 21 widened this from form numbers and ranks to names and
    # districts; issue 1 is the original rank lookup.
    ("results", "did form 2083-4567 pass", {LOOKUP}, {DECLINED}),
    ("results", "who is rank 13", {LOOKUP}, {DECLINED}),
    ("results", "who topped the entrance exam", {LOOKUP}, {DECLINED}),
    ("results", "what rank did Ritesh Dawadi get", {LOOKUP}, {DECLINED}),
    ("results", "who are the top candidates from Chitawan", {LOOKUP}, {DECLINED}),
    ("results", "2083-2 ko rank kati ho", {LOOKUP}, {DECLINED}),
    # A number that is not on the list still has to reach the lookup: issue 21 records
    # that saying "not found" is the answer, and inventing a candidate is the failure.
    ("results", "did form 2083-99999 pass", {LOOKUP}, {DECLINED}),
    # ── Ordinary retrieval.
    ("docs", "what documents do i need for the women quota", {DOCUMENTS}, {DECLINED}),
    ("docs", "what is the entrance exam syllabus for physics", {DOCUMENTS}, {DECLINED}),
    ("docs", "how many marks is the entrance exam", {DOCUMENTS}, {DECLINED}),
    ("docs", "which campuses offer architecture", {DOCUMENTS}, {DECLINED}),
    (
        "docs",
        "what happens if i do not take a lower priority seat",
        {DOCUMENTS},
        {DECLINED},
    ),
    ("docs", "am i eligible with a diploma", {DOCUMENTS}, {DECLINED}),
    # ── Language. Issue 19: the answer is English whatever the question was written in,
    # and the question still has to reach the documents.
    ("language", "प्रवेश परीक्षाको शुल्क कति हो", {DOCUMENTS}, {DECLINED}),
    (
        "language",
        "please reply in nepali, what documents do i need",
        {DOCUMENTS},
        {DECLINED},
    ),
    ("language", "answer in hindi: when is the exam", {DOCUMENTS}, {DECLINED}),
    # ── Scope. The half of issue 22's suite that has no history; the follow-ups that
    # need history are in CONVERSATIONS, which is where issue 24 says they belong.
    ("scope", "write me a python function to reverse a list", {DECLINED}, set()),
    ("scope", "who won the world cup", {DECLINED}, set()),
    ("scope", "lets go on a holiday", {UNCOVERED}, {DECLINED}),
    ("scope", "how do i apply to Kathmandu University", {UNCOVERED}, {DECLINED}),
    ("scope", "solve x^2 + 5x + 6 = 0", {DECLINED}, set()),
    ("scope", "recommend a good laptop under 80000", {DECLINED}, set()),
    # Real questions that issue 22 records the classifier getting wrong on its own.
    ("scope", "how many seats are there in pulchowk", {DOCUMENTS}, {DECLINED}),
    ("scope", "what is the women's quota", {DOCUMENTS}, {DECLINED}),
    ("scope", "which campus is best for civil", {DOCUMENTS}, {DECLINED}),
    ("scope", "when do applications close", {DOCUMENTS}, {DECLINED}),
    # ── Cutoffs. Issue 30. The last two matter most: a bare rank question is a pass-list
    # lookup and must not drag in four years of cutoff history, and a chances question
    # must not drag in the stranger who actually holds that rank -- which is the hazard
    # results.lookup_context's skip_ranks was added for.
    ("cutoffs", "i got rank 660, what can i study", {CUTOFFS}, {LOOKUP, DECLINED}),
    # Names Pulchowk, so the allocation answers it; the four-year cutoff history now
    # stands alongside rather than being suppressed, so it is no longer asserted absent.
    (
        "cutoffs",
        "is rank 340 enough for computer engineering at pulchowk",
        {CHANCES},
        {LOOKUP, DECLINED},
    ),
    ("cutoffs", "what was the cutoff for civil at thapathali", {CUTOFFS}, {DECLINED}),
    ("cutoffs", "can i get mechanical with my rank", {CUTOFFS}, {DECLINED}),
    ("cutoffs", "what is the closing rank for architecture", {CUTOFFS}, {DECLINED}),
    ("cutoffs", "who is rank 340", {LOOKUP}, {CUTOFFS, DECLINED}),
    ("cutoffs", "did form 2083-4001 pass", {LOOKUP}, {CUTOFFS, DECLINED}),
    # ── Priority allocation. Issue 31. chances supersedes cutoffs at Pulchowk, because
    # with both present the model quoted a published 2082 figure inside an answer about
    # the 2083 simulation. A campus with no priority data must fall back to cutoffs and
    # must never be answered with Pulchowk's allocation.
    (
        "chances",
        "my rank is 500, what should i put as my first priority at pulchowk",
        {CHANCES},
        {DECLINED},
    ),
    ("chances", "i am rank 2000, can i get computer at pulchowk", {CHANCES}, set()),
    ("chances", "rank 40, which programmes can i get", {CHANCES}, {DECLINED}),
    (
        "chances",
        "i got rank 300, what can i get at thapathali",
        {CUTOFFS},
        {CHANCES, DECLINED},
    ),
    (
        "chances",
        "what happens if i refuse a lower priority seat",
        {PRIORITY},
        {CHANCES, DECLINED},
    ),
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
            ("hi", set(), {DECLINED}),
            ("how much do i have to pay as a regular student", {FEES}, {DECLINED}),
            (
                "write me a python function to calculate sum of three numbers",
                set(),
                {FEES},
            ),
            # IOE runs BE and BArch. The documents do not cover "other categories", and
            # saying so is the answer -- inventing BBA and PhD programmes is the bug.
            ("and what other cateogry i could study in", {UNCOVERED}, {DECLINED}),
            ("what is its source", set(), {DECLINED}),
            ("foreign?", {FEES}, {DECLINED}),
        ],
    ),
    (
        "follow-up",
        [
            ("what is the entrance exam fee", {DOCUMENTS}, {DECLINED}),
            ("how do i pay it?", {DOCUMENTS}, {DECLINED}),
            ("and the deadline?", set(), {DECLINED}),
            ("what did i just ask you about?", set(), {DECLINED}),  # UNCOVERED is fine
        ],
    ),
    (
        # Small talk must not inherit the previous question's evidence. Issue 12's bug:
        # "you're welcome" printed the fee notice as its source.
        "hygiene",
        [
            ("how much is the dharauti", {FEES}, {DECLINED}),
            ("thanks!", set(), {FEES, DOCUMENTS, LOOKUP, DECLINED}),
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


# Defensive, not diagnostic. Nothing has been observed hanging mid-turn; a run that
# looked stuck turned out to have finished and hung on exit instead (see close_saver).
# But a turn is one model call away from an Ollama that may be reloading an evicted
# model, and a suite that stops with no output says less than one that fails a case.
TURN_TIMEOUT = 180.0


async def _run_turn(bot, thread: str, message: str) -> tuple[set[str], float]:
    started = time.time()
    try:
        state = await asyncio.wait_for(
            bot.ainvoke(
                {"messages": [HumanMessage(content=message)]},
                {"configurable": {"thread_id": thread}},
            ),
            timeout=TURN_TIMEOUT,
        )
    except TimeoutError:
        return {TIMEOUT}, time.time() - started
    return evidence(state), time.time() - started


def _check(got: set[str], want: set[str], forbid: set[str]) -> str:
    if TIMEOUT in got:
        return f"no answer within {TURN_TIMEOUT:.0f}s"
    missing = want - got
    present = forbid & got
    if missing:
        return f"missing {sorted(missing)}"
    if present:
        return f"unwanted {sorted(present)}"
    return ""


# ── The detector ──────────────────────────────────────────────────────────────
# scope.is_task_substitution is the one deterministic thing standing between a student
# and "here's a simple Python function". Its danger is not missing one -- it is firing on
# a real question, which is how issue 24's guard broke the conversation. So its precision
# is checked against every question in this file, on every run. It needs no model and
# takes no measurable time.

MUST_FIRE = [
    "write me a python function to reverse a list",
    "write me a python function to calculate sum of three numbers",
    "solve x^2 + 5x + 6 = 0",
    "recommend a good laptop under 80000",
    "who won the world cup",
    "what is the capital of france",
    "can you help me with my physics homework",
    "translate this into nepali",
    "debug my code please",
    "write me an essay about nepal",
]


def check_detector() -> int:
    """Recall on the tasks it must catch, precision against every question here."""
    from ioe.scope import is_task_substitution

    failures = 0
    for question in MUST_FIRE:
        if not is_task_substitution(question):
            print(f"FAIL detector  did not fire on {question!r}")
            failures += 1

    corpus = [q for _, q, _, _ in CASES] + [
        m for _, turns in CONVERSATIONS for m, _, _ in turns
    ]
    for question in corpus:
        if question in MUST_FIRE:
            continue
        if is_task_substitution(question):
            print(f"FAIL detector  fired on a real question: {question!r}")
            failures += 1

    if not failures:
        print(
            f"ok   detector   {len(MUST_FIRE)}/{len(MUST_FIRE)} caught, "
            f"silent on all {len(corpus)} questions in this suite"
        )
    return failures


async def run(groups: set[str] | None = None) -> int:
    """Run the suite. Returns the number of failures."""
    from ioe.graph import get_chatbot

    probe = _probe()
    failures = check_detector()
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
    await close_saver(bot)
    return failures


async def close_saver(bot) -> None:
    """Close the checkpointer's connection, or the process will not exit.

    AsyncSqliteSaver holds an aiosqlite Connection, and aiosqlite runs it on a
    non-daemon thread that nothing joins. The suite would print its result and then sit
    there: measured at twenty-two minutes elapsed against seven seconds of CPU, with
    forty-nine threads parked on futexes. It looks exactly like a hung run, and it cost
    an hour of believing one.

    The app itself never needed this -- api.py holds one connection for the life of the
    process, which is the right thing for a server and the wrong thing for a script.
    """
    conn = getattr(bot.checkpointer, "conn", None)
    if conn is not None:
        await conn.close()


def main() -> None:
    groups = set(sys.argv[1:]) or None
    raise SystemExit(1 if asyncio.run(run(groups)) else 0)


if __name__ == "__main__":
    main()
