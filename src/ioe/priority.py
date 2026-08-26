"""Historical priority-choice analysis for Pulchowk Campus.

A student applying to Pulchowk fills an ordered list of programme priorities, and IOE
admits by a single rule: it walks the merit list from rank 1 downward and places each
applicant into the highest programme on *their* priority list that still has a seat. That
rule is a serial dictatorship -- given the applicants, their priority lists, and the seat
counts, the final allocation is fixed and reproducible. So last year's published priority
applications are enough to reconstruct, for every programme, the worst rank that got in:
its cutoff. That is the one thing a student choosing priorities for next year actually
wants to know, and it exists nowhere as a published table -- only implicitly, inside the
list of who asked for what.

This module reads the 2083 priority applications (docs/data/), runs that simulation once,
and answers two shapes of question against it: "I'm rank N, which programmes could I have
got, and in what order should I list them?" and "with rank N, is programme X realistic as
a first priority?" Every figure it produces is last year's, and it says so: a cutoff moves
each year with the applicant pool and the seat count, so 2083 is guidance, never a promise
for 2084. It is Pulchowk-only, because Pulchowk is the only campus whose priority list we
have.

Like results.py, this is deliberately kept out of the vector index and answered by exact
computation. A cutoff is a number a student will act on; it must be right, not the nearest
neighbour of right.
"""

import csv
import re
from functools import lru_cache
from pathlib import Path

from ioe.results import find_ranks

PRIORITY_CSV = (
    Path(__file__).resolve().parents[2] / "docs" / "data" / "pulchowk_priority_2083.csv"
)
PRIORITY_YEAR = "2083"

# The analysis rests on two published documents: the priority-applications list (whose
# ranks and choices drive the simulation) and the booklet, whose section 2.7 fixes the
# Pulchowk seat counts. The booklet is the openable primary source for the seat totals, so
# the citation points there; the title says plainly that the cutoffs are derived, not
# lifted from a published table, because no such table exists.
PRIORITY_SOURCE = {
    "title": "Pulchowk 2083 priority-choice analysis (derived from the published "
    "priority applications and booklet seat targets)",
    "year": PRIORITY_YEAR,
    "url": "https://entrance.ioe.edu.np/Notice/Detail/5128",
    "file": PRIORITY_CSV.name,
    "sections": [],
}

# Programme code -> (programme, category, Pulchowk seats). Codes are from page 2 of the
# priority-applications PDF; seats are from booklet section 2.7 (Pulchowk Reg/Full column).
CODES: dict[int, tuple[str, str, int]] = {
    1: ("Civil", "Regular", 108),
    2: ("Civil", "Full-fee", 84),
    3: ("Architecture", "Regular", 24),
    4: ("Architecture", "Full-fee", 24),
    5: ("Electrical", "Regular", 36),
    6: ("Electrical", "Full-fee", 60),
    7: ("Electronics", "Regular", 24),
    8: ("Electronics", "Full-fee", 24),
    9: ("Mechanical", "Regular", 24),
    10: ("Mechanical", "Full-fee", 24),
    11: ("Computer", "Regular", 36),
    12: ("Computer", "Full-fee", 60),
    27: ("Aerospace", "Regular", 12),
    28: ("Aerospace", "Full-fee", 36),
    29: ("Chemical", "Regular", 12),
    30: ("Chemical", "Full-fee", 36),
}

# The words a student uses for each programme -> its two codes (Regular, Full-fee). Order
# each alternation longest-first so "electronics" is tried before "electronic".
_PROGRAM_WORDS: dict[str, tuple[int, int]] = {
    r"civil": (1, 2),
    r"architecture|b\.?\s?arch|barch": (3, 4),
    r"electrical": (5, 6),
    r"electronics?|communication": (7, 8),
    r"mechanical": (9, 10),
    r"computer": (11, 12),
    r"aerospace": (27, 28),
    r"chemical": (29, 30),
}

_REGULAR_RE = re.compile(r"\bregular\b", re.IGNORECASE)
_FULLFEE_RE = re.compile(r"\bfull[\s-]?fee\b", re.IGNORECASE)

# A priority question is a rank plus intent to choose or place programmes. Without the
# intent, a bare "rank 34" is a pass-list question that results.py already answers, and
# firing here as well would attach an unrelated candidate's identity to a question that was
# never about them.
_PRIORITY_INTENT_RE = re.compile(
    r"\bpriorit(?:y|ies)\b|\bpreferenc\w*\b|\bfill\b|\bchoose\b|\bchoos\w*\b|"
    r"\bwhich\s+(?:program\w*|branch\w*|subject\w*|faculty|stream|course|department)\b|"
    r"\bwhat\s+(?:program\w*|branch\w*|subject\w*|faculty|stream|course|department)\b|"
    r"\bget\s+into\b|\b(?:will|can|could|would)\s+i\s+get\b|\bchanc\w*\b|"
    r"\bsafe\b|\bfirst\s+(?:choice|priority)\b|\bin\s+what\s+order\b|\border\s+of\b",
    re.IGNORECASE,
)

# Another campus named by name means the question is not about Pulchowk, and Pulchowk is
# the only campus we hold priority data for. Say nothing rather than answer Thapathali with
# Pulchowk's numbers.
_OTHER_CAMPUS_RE = re.compile(
    r"\b(thapathali|purwanchal|paschimanchal|pashchimanchal|chitwan|chitawan|"
    r"kantipur|kathford|khwopa|sagarmatha|janakpur|himalaya|advanced\s+college|"
    r"national\s+college|kathmandu\s+engineering)\b",
    re.IGNORECASE,
)

# Method and caveat lines, repeated verbatim so the wording the model sees cannot drift
# from one turn to the next.
_METHOD = (
    f"Method: a merit-order simulation of the published {PRIORITY_YEAR} Pulchowk priority "
    "applications -- applicants placed by rank, each into the best still-open programme on "
    "their own list. A rank 'clears' a programme if it is at least as good as that "
    "programme's last-admitted rank."
)
_CAVEAT = (
    f"Caveat: these are last year's ({PRIORITY_YEAR}) figures, not a promise for this "
    "year. A cutoff moves every year with the applicant pool and the seat count, so treat "
    "it as guidance, never a guarantee, and never as a rank a student is 'safe' at."
)
# The strategy, stated as the block's own conclusion rather than left for the model to
# reason out. A 7B model asked to advise on ordering invents plausible-sounding tactics --
# "list the full-fee seat first to face less competition" -- which is exactly the mistake
# admission by rank makes impossible and the booklet warns against. So the block says the
# right answer outright and forbids the wrong one by name.
_STRATEGY = (
    "How to order priorities (state this, do not reason around it): list programmes in the "
    "student's genuine order of preference. Placing a programme higher NEVER improves the "
    "chance of reaching a lower one -- admission is by rank into the best still-open choice, "
    "so a lower choice is still there at the same rank if a higher one has filled. The only "
    "effect of listing a less-wanted programme first is being forced to take it. "
    "For the same programme, the Regular seat is far cheaper than the Full-fee seat for the "
    "identical degree, so Regular belongs ABOVE its Full-fee version: listing Regular first "
    "costs nothing, because a student who does not reach Regular still falls through to "
    "Full-fee at their rank. Never advise listing a Full-fee seat above its Regular seat, or "
    "any programme above a more-wanted one, to 'play it safe' or 'increase chances' -- that "
    "only forces a larger payment or an unwanted programme."
)


@lru_cache(maxsize=1)
def _applicants() -> list[dict]:
    """The priority applications, one row per candidate, ordered by merit rank.

    A candidate who applied under more than one quota appears on more than one row, each
    with its own priority list; the Open row is the one that governs open-seat competition,
    so it wins the dedupe. A missing file yields no applicants and, downstream, no cutoffs.
    """
    if not PRIORITY_CSV.exists():
        return []
    by_roll: dict[str, dict] = {}
    with PRIORITY_CSV.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            roll = row.get("roll_no", "")
            try:
                rank = int(row["rank"])
            except (KeyError, ValueError):
                continue
            prios = [int(row[f"p{k}"]) for k in range(1, 10) if row.get(f"p{k}")]
            rec = {"rank": rank, "prios": prios, "quota": row.get("quota_group", "")}
            if roll not in by_roll or (
                rec["quota"] == "Open" and by_roll[roll]["quota"] != "Open"
            ):
                by_roll[roll] = rec
    return sorted(by_roll.values(), key=lambda r: r["rank"])


@lru_cache(maxsize=1)
def _cutoffs() -> dict[int, int | None]:
    """The worst rank admitted into each programme code, by serial dictatorship.

    Walks the merit list from the top and drops each applicant into the first programme on
    their priority list with a seat left. The last rank placed into a programme is its
    cutoff; a programme nobody reached stays None.
    """
    filled = {code: 0 for code in CODES}
    cutoff: dict[int, int | None] = {code: None for code in CODES}
    for applicant in _applicants():
        for code in applicant["prios"]:
            seats = CODES.get(code)
            if seats and filled[code] < seats[2]:
                filled[code] += 1
                cutoff[code] = applicant["rank"]
                break
    return cutoff


def find_programs(text: str) -> list[str]:
    """The Pulchowk programme names mentioned in the question, in the order they appear."""
    hits: list[tuple[int, str]] = []
    for pattern, (reg_code, _) in _PROGRAM_WORDS.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            hits.append((match.start(), CODES[reg_code][0]))
    return [name for _, name in sorted(hits)]


def _codes_for(program: str, text: str) -> list[int]:
    """The programme's codes the question is asking about -- one category if it named one,
    otherwise both. 'computer regular' asks about 11; 'computer' asks about 11 and 12."""
    pair = next(
        codes for codes in _PROGRAM_WORDS.values() if CODES[codes[0]][0] == program
    )
    if _REGULAR_RE.search(text) and not _FULLFEE_RE.search(text):
        return [pair[0]]
    if _FULLFEE_RE.search(text) and not _REGULAR_RE.search(text):
        return [pair[1]]
    return list(pair)


def _label(code: int) -> str:
    program, category, _ = CODES[code]
    return f"{program} {category}"


def format_rank_guidance(rank: int) -> str:
    """Which programmes a rank would and would not have cleared last year.

    The verdict is welded to every line -- "attainable" or "NOT attainable", with the
    comparison spelled out in words -- because the model cannot be trusted to derive it
    from the raw numbers. Handed a bare "- Computer Regular (last admitted rank 55)" for a
    rank of 2000, qwen2.5:7b read 55 as "much higher than your rank" and promoted a
    programme the rank misses by a mile. A smaller rank number being better is not
    something a 7B model reliably knows, so it is never left to work it out: each line
    states the outcome outright, and the not-attainable list is labelled do-not-offer.
    """
    cutoff = _cutoffs()
    reachable = sorted(
        (co, code) for code, co in cutoff.items() if co is not None and rank <= co
    )
    missed = sorted(
        (co, code) for code, co in cutoff.items() if co is not None and rank > co
    )

    header = f"[Pulchowk priority analysis: merit rank {rank}, {PRIORITY_YEAR} data]"
    summary = (
        f"Summary: at rank {rank}, {len(reachable)} of {len(reachable) + len(missed)} "
        f"Pulchowk programmes were attainable last year. A smaller rank number is better, "
        f"so a programme was attainable only if {rank} is at least as good as (less than "
        f"or equal to) its last-admitted rank."
    )
    if reachable:
        attainable = (
            "Attainable last year -- offer these, in the student's own order of "
            "preference:\n"
            + "\n".join(
                f"- {_label(code)}: attainable. Last-admitted rank {co}, and {rank} is at "
                f"least as good, so it would have been placed."
                for co, code in reachable
            )
        )
    else:
        attainable = (
            f"Attainable last year: none. Every Pulchowk programme's last-admitted rank "
            f"in {PRIORITY_YEAR} was better than {rank}, so none would have taken this "
            "rank. Say so plainly and point the student to campuses or affiliated colleges "
            "with lower cutoffs."
        )
    missed_block = (
        "NOT attainable last year -- rank "
        f"{rank} was past each one's last-admitted rank. Do not present these as a plan or "
        "imply the student can pick them; if mentioned at all, say plainly they were out of "
        "reach at this rank and are long shots only. When few or none were attainable, tell "
        "the student honestly that this rank is a stretch for Pulchowk and point them to "
        "other campuses or affiliated colleges, which have lower cutoffs.\n"
        + "\n".join(f"- {_label(code)}: last-admitted rank {co}" for co, code in missed)
        if missed
        else ""
    )

    return "\n".join(
        part
        for part in (
            header,
            _METHOD,
            summary,
            attainable,
            missed_block,
            _CAVEAT,
            _STRATEGY,
        )
        if part
    )


def format_program_feasibility(rank: int, program: str, text: str) -> str:
    """Whether a rank cleared the named programme(s) last year -- the "is X realistic as a
    first priority?" question. Reports both categories unless the question fixed one."""
    cutoff = _cutoffs()
    header = f"[Pulchowk priority analysis: merit rank {rank}, {program}, {PRIORITY_YEAR} data]"
    lines = []
    for code in _codes_for(program, text):
        co = cutoff[code]
        if co is None:
            lines.append(
                f"{_label(code)}: nobody reached this programme in the {PRIORITY_YEAR} "
                "simulation, so there is no last-admitted rank to compare against."
            )
        elif rank <= co:
            lines.append(
                f"{_label(code)}: last admitted rank {co}. Rank {rank} was within that "
                "last year -- it would have been placed."
            )
        else:
            lines.append(
                f"{_label(code)}: last admitted rank {co}. Rank {rank} was past that last "
                "year -- it would not have been placed."
            )
    return "\n".join([header, _METHOD, *lines, _CAVEAT, _STRATEGY])


def priority_context(text: str) -> str:
    """Context for a Pulchowk priority question, or "" if the question is not one.

    Fires only on a rank paired with intent to choose or place programmes, and never when
    another campus is named -- Pulchowk is the only campus with priority data. Read from
    the raw question, like the pass-list lookup, so a rank survives verbatim rather than
    through a paraphrase or a translation.
    """
    if _OTHER_CAMPUS_RE.search(text):
        return ""
    programs = find_programs(text)
    if not (_PRIORITY_INTENT_RE.search(text) or programs):
        return ""
    ranks = find_ranks(text, include_topper=False)
    if not ranks:
        return ""

    rank = ranks[0]
    if programs:
        return "\n\n".join(
            format_program_feasibility(rank, program, text) for program in programs
        )
    return format_rank_guidance(rank)
