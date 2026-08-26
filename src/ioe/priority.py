"""Pulchowk's priority-order rules, and what its priority applications actually did.

Two halves, both about the same form. The first is the rules for filling it in, written
out rather than retrieved. The second simulates the allocation those applications produced
and answers "with my rank, what would I have got".

They pair with `cutoffs.py`, which is the same question asked earlier. Before the form is
filled, all anyone has is last year's published outcome, which is what `cutoffs.py` holds.
After it is filled, the priority applications are public and the allocation is no longer a
guess: IOE admits by walking the merit list from rank 1 and placing each applicant into
the best still-open programme on their own list, which is a serial dictatorship, which
means the outcome is fully determined by data that has already been published. This module
recomputes it.

Section 5 of the Pulchowk admission notice is the highest-stakes prose in the corpus. It
is the section that decides whether a student who was offered their third choice and
turned it down is still in the running for their first -- and the answer is no, they are
out of the process entirely. A student who skims that loses their place.

It is not left to retrieval for two reasons. The chunker splits on Markdown headings and
then again at 1,200 characters, and this section is longer than that, so the rules and the
worked example that makes them land can end up in different chunks and only one of them
retrieved. And a question that needs these rules -- "what happens if I do not take a lower
priority seat?" -- does not necessarily contain any word that embeds near them.

So the text below is fixed, complete, and either present in full or absent. The same
discipline as `fees.py` and `seats.py`: the thing a student cannot afford to have
half-right is not left to a similarity score.

**Pulchowk only, and the code says so rather than assuming it.** The simulation runs on
whatever `docs/data/<campus>_priority_<year>.csv` files exist, and only Pulchowk's has
been published in a form we hold. Adding a campus is adding its CSV and its code table --
no code changes. Asked about a campus with no dataset, this returns nothing rather than
answering with Pulchowk's numbers.

**Open category only.** The booklet says Regular seats are *inclusive* of quota: women's,
teacher/staff, sponsored and foreign seats are carved out of Regular rather than added to
it. Modelling them wrong would inflate every open-category estimate, and those tables are
the grid the booklet's own translation flags as its highest transcription risk. So the
simulation dedupes each applicant to their Open row and the block says plainly that a
quota applicant's case is not described here.
"""

import csv
import re
from functools import lru_cache
from pathlib import Path

from ioe.results import find_ranks
from ioe.seats import CAMPUSES, FULL_FEE, REGULAR

PRIORITY_SOURCE = {
    "title": (
        "Pulchowk Campus BE/BArch Admission Notice 2083/084 "
        "— Schedule, Priority Rules and Fees"
    ),
    "year": "2083",
    "url": "https://pcampus.edu.np/2026/08/12/be-barch-admission-2083-detail-notice/",
    "file": "13_Pulchowk_BE_Admission_Detail_Notice_2083_English.md",
    "sections": ["5. Priority-order rules"],
}

# The notice states this outright, and it is also derivable: every programme Pulchowk
# offers, in both its Regular and its Full Fee variant. verify() checks the two agree.
PUBLISHED_PRIORITIES = 16

# Only Pulchowk publishes rules of its own. Thapathali, Purwanchal, Pashchimanchal and
# Chitwan are not covered here and must not be answered as though they were.
CAMPUS = "Pulchowk"


def programmes(campus: str = CAMPUS) -> list[str]:
    """The programmes a campus offers, in the booklet's row order."""
    index = CAMPUSES.index(campus)
    return [name for name in REGULAR if REGULAR[name][index] or FULL_FEE[name][index]]


def priority_count(campus: str = CAMPUS) -> int:
    """How many priorities a campus's applicants rank: each programme, twice."""
    index = CAMPUSES.index(campus)
    return sum(
        bool(REGULAR[name][index]) + bool(FULL_FEE[name][index]) for name in REGULAR
    )


def verify() -> list[str]:
    """Check the derived priority count, the code table, and the simulation's output.

    The code table is the one thing here transcribed from a document seats.py has never
    seen -- page 2 of the priority-application form -- so checking every code against
    seats.py is a real cross-check between two independent readings of the same campus.
    A code naming a programme the campus does not run, or runs no seats of, means one of
    the two was read wrong.
    """
    problems: list[str] = []

    counted = priority_count()
    if counted != PUBLISHED_PRIORITIES:
        problems.append(
            f"{CAMPUS}: seats.py yields {counted} priorities, "
            f"the notice prints {PUBLISHED_PRIORITIES}"
        )

    for campus, codes in CODES.items():
        if campus not in CAMPUSES:
            problems.append(f"{campus}: not a constituent campus in seats.py")
            continue
        if len(codes) != priority_count(campus):
            problems.append(
                f"{campus}: {len(codes)} priority codes but seats.py gives the campus "
                f"{priority_count(campus)} programme/category pairs"
            )
        for code, (programme, category) in sorted(codes.items()):
            if seats_for(campus, programme, category) == 0:
                problems.append(
                    f"{campus} code {code} ({programme}, {category}): seats.py gives "
                    "this programme no seats of that category at this campus"
                )

    # The simulation's own output. A cutoff worse than the deepest rank that applied is
    # arithmetically impossible, and a programme whose cutoff is better than its seat
    # count means fewer people were placed than there were seats -- both mean the walk
    # went wrong rather than that the data is surprising.
    for campus, year in datasets():
        applicants = _applicants(campus, year)
        if not applicants:
            problems.append(f"{campus} {year}: dataset present but no applicants read")
            continue
        deepest = max(record["rank"] for record in applicants)
        for code, value in allocation(campus, year).items():
            if value is None:
                continue
            if value > deepest:
                problems.append(
                    f"{campus} {year} code {code}: cutoff {value} is deeper than the "
                    f"deepest rank that applied ({deepest})"
                )
            programme, category = CODES[campus][code]
            if value < seats_for(campus, programme, category):
                problems.append(
                    f"{campus} {year} {programme} ({category}): cutoff {value} is better "
                    f"than the {seats_for(campus, programme, category)} seats available, "
                    "so fewer applicants were placed than there were seats"
                )
    return problems


RULES = """[Pulchowk priority-order rules, from section 5 of the campus admission \
notice. These are the published rules, not a summary -- state them as they are.]

Pulchowk applicants rank up to 16 priorities: each of the campus's 8 programmes appears
twice, once as Regular and once as Full Fee. Admission lists are published in that
priority order, on the basis of the rank the applicant obtained in the entrance
examination.

- An applicant already admitted under a lower priority whose rank later reaches a higher
  priority is published in the higher priority automatically.
- An applicant published in a higher priority and admitted there cannot move back down to
  a lower-priority programme.
- To stay in the running, a lower-priority seat must actually be taken. An applicant is
  published in higher-priority programmes in later lists only if they were admitted after
  being published in a lower priority they listed.
- THE TRAP, and the one thing worth saying plainly whenever these rules come up: an
  applicant published in a lower-priority programme who does NOT get admitted in it is
  excluded from the admission process entirely. The notice's own example is an applicant
  whose priorities are Computer (Regular), then Civil (Full Fee), then Architecture
  (Regular). If they are published for Architecture and do not take it, they are out --
  they do not stay in line for Computer or Civil.
- An applicant admitted to a Regular programme who later comes out in a Full Fee
  programme they ranked higher must be admitted there, paying the difference. Not taking
  it cancels the admission they already had.
- An applicant can stop moving up only by submitting a written application to the
  Admission Committee saying they will not move to a higher priority hereafter.

Because of the last two, the notice advises applicants not to list any programme they do
not actually want. Ranking an unwanted Full Fee programme above a wanted Regular one can
force a much larger payment, or cost the seat.

These rules are Pulchowk's. Thapathali, Purwanchal, Pashchimanchal and Chitwan publish
their own admission notices and are not covered here -- do not state these rules as
theirs."""


def priority_context() -> str:
    """The block. Fixed text, so it is either entirely present or entirely absent."""
    return RULES


# ── The allocation simulation ─────────────────────────────────────────────────

PRIORITY_DIR = Path(__file__).resolve().parents[2] / "docs" / "data"
DATASET = re.compile(r"^(?P<campus>[a-z]+)_priority_(?P<year>\d{4})\.csv$")

# Priority code -> (programme, category), transcribed from page 2 of the campus's
# priority-application form. Seats are deliberately NOT here: they come from seats.py, so
# the booklet is transcribed once and a disagreement between the two is a verify() failure
# rather than a drift nobody notices. Programme names are seats.py's, for the same reason.
CODES: dict[str, dict[int, tuple[str, str]]] = {
    "Pulchowk": {
        1: ("Civil", "Regular"),
        2: ("Civil", "Full-fee"),
        3: ("Architecture", "Regular"),
        4: ("Architecture", "Full-fee"),
        5: ("Electrical", "Regular"),
        6: ("Electrical", "Full-fee"),
        7: ("Electronics, Communication and Information", "Regular"),
        8: ("Electronics, Communication and Information", "Full-fee"),
        9: ("Mechanical", "Regular"),
        10: ("Mechanical", "Full-fee"),
        11: ("Computer", "Regular"),
        12: ("Computer", "Full-fee"),
        27: ("Aerospace", "Regular"),
        28: ("Aerospace", "Full-fee"),
        29: ("Chemical", "Regular"),
        30: ("Chemical", "Full-fee"),
    },
}

# The words a student uses for each programme. Longest alternative first, so "electronics"
# is tried before "electronic".
_PROGRAM_WORDS: dict[str, str] = {
    r"civil": "Civil",
    r"architecture|b\.?\s?arch|barch": "Architecture",
    r"electrical": "Electrical",
    r"electronics?|communication": "Electronics, Communication and Information",
    r"mechanical": "Mechanical",
    r"computer": "Computer",
    r"aerospace": "Aerospace",
    r"chemical": "Chemical",
}

_REGULAR_RE = re.compile(r"\bregular\b", re.IGNORECASE)
_FULLFEE_RE = re.compile(r"\bfull[\s-]?fee\b", re.IGNORECASE)

# A priority question is a rank plus intent to choose or place programmes. Without the
# intent, a bare "rank 34" is a pass-list question that results.py already answers, and
# firing here as well would attach an unrelated candidate's identity to a question that
# was never about them.
_PRIORITY_INTENT_RE = re.compile(
    r"\bpriorit(?:y|ies)\b|\bpreferenc\w*\b|\bfill\b|\bchoose\b|\bchoos\w*\b|"
    r"\bwhich\s+(?:program\w*|branch\w*|subject\w*|faculty|stream|course|department)\b|"
    r"\bwhat\s+(?:program\w*|branch\w*|subject\w*|faculty|stream|course|department)\b|"
    r"\bget\s+into\b|\b(?:will|can|could|would)\s+i\s+get\b|\bchanc\w*\b|"
    r"\bsafe\b|\bfirst\s+(?:choice|priority)\b|\bin\s+what\s+order\b|\border\s+of\b|"
    # "what should I put first" is the question this whole module exists to answer and it
    # matched none of the above -- no programme named, and "first" not followed by
    # "choice" or "priority". Found by checking what the app's own example questions
    # actually fire.
    r"\b(?:put|list|rank|place|pick|select)\b[^.?!]{0,30}\bfirst\b|"
    r"\bwhat\s+should\s+i\s+(?:put|choose|pick|list|go\s+for)\b",
    re.IGNORECASE,
)

# A campus we hold no priority data for means the question is not one this can answer.
# Saying nothing beats answering Thapathali with Pulchowk's numbers.
_OTHER_CAMPUS_RE = re.compile(
    r"\b(thapathali|purwanchal|paschimanchal|pashchimanchal|chitwan|chitawan|"
    r"kantipur|kathford|khwopa|sagarmatha|janakpur|himalaya|advanced\s+college|"
    r"national\s+college|kathmandu\s+engineering)\b",
    re.IGNORECASE,
)


@lru_cache(maxsize=1)
def datasets() -> dict[tuple[str, str], Path]:
    """(campus, year) -> the priority CSV for it. Discovered, not declared.

    Adding next year's list, or another campus's, is adding the file. Nothing here needs
    editing for either.
    """
    found: dict[tuple[str, str], Path] = {}
    for path in sorted(PRIORITY_DIR.glob("*_priority_*.csv")):
        match = DATASET.match(path.name)
        if not match:
            continue
        campus = match["campus"].capitalize()
        if campus in CODES:
            found[(campus, match["year"])] = path
    return found


def latest(campus: str = CAMPUS) -> str:
    """The most recent year we hold a priority list for at this campus, or ""."""
    held = [year for (place, year) in datasets() if place == campus]
    return max(held) if held else ""


def seats_for(campus: str, programme: str, category: str) -> int:
    """The seat count from seats.py, which is the one transcription of the booklet."""
    table = REGULAR if category == "Regular" else FULL_FEE
    row = table.get(programme)
    return row[CAMPUSES.index(campus)] if row else 0


@lru_cache(maxsize=8)
def _applicants(campus: str, year: str) -> list[dict]:
    """The priority applications, one row per candidate, ordered by merit rank.

    A candidate who applied under more than one quota appears on more than one row, each
    with its own priority list; the Open row is the one that governs open-seat competition,
    so it wins the dedupe. A missing file yields no applicants and, downstream, no cutoffs.
    """
    path = datasets().get((campus, year))
    if path is None:
        return []
    by_roll: dict[str, dict] = {}
    with path.open(encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            roll = row.get("roll_no", "")
            try:
                rank = int(row["rank"])
            except (KeyError, ValueError):
                continue
            record = {
                "rank": rank,
                "prios": [int(row[f"p{n}"]) for n in range(1, 10) if row.get(f"p{n}")],
                "quota": row.get("quota_group", ""),
            }
            if roll not in by_roll or (
                record["quota"] == "Open" and by_roll[roll]["quota"] != "Open"
            ):
                by_roll[roll] = record
    return sorted(by_roll.values(), key=lambda record: record["rank"])


@lru_cache(maxsize=8)
def allocation(campus: str, year: str) -> dict[int, int | None]:
    """Priority code -> the worst rank admitted into it, by serial dictatorship.

    Walks the merit list from the top and drops each applicant into the first programme on
    their priority list with a seat left. The last rank placed into a programme is its
    cutoff; a programme nobody reached stays None.
    """
    codes = CODES.get(campus, {})
    filled = dict.fromkeys(codes, 0)
    cutoff: dict[int, int | None] = dict.fromkeys(codes)
    for applicant in _applicants(campus, year):
        for code in applicant["prios"]:
            if code not in codes:
                continue
            programme, category = codes[code]
            if filled[code] < seats_for(campus, programme, category):
                filled[code] += 1
                cutoff[code] = applicant["rank"]
                break
    return cutoff


def find_programs(text: str) -> list[str]:
    """The programme names mentioned in the question, in the order they appear."""
    hits: list[tuple[int, str]] = []
    for pattern, name in _PROGRAM_WORDS.items():
        if match := re.search(pattern, text, re.IGNORECASE):
            hits.append((match.start(), name))
    return [name for _, name in sorted(hits)]


def _codes_for(campus: str, programme: str, text: str) -> list[int]:
    """The codes for a programme, narrowed to one category if the question fixed one."""
    codes = [
        code for code, (name, _) in CODES.get(campus, {}).items() if name == programme
    ]
    if _REGULAR_RE.search(text) and not _FULLFEE_RE.search(text):
        codes = [c for c in codes if CODES[campus][c][1] == "Regular"]
    elif _FULLFEE_RE.search(text) and not _REGULAR_RE.search(text):
        codes = [c for c in codes if CODES[campus][c][1] == "Full-fee"]
    return sorted(codes)


def _label(campus: str, code: int) -> str:
    programme, category = CODES[campus][code]
    return f"{programme} ({category})"


# Method, caveat and strategy, written once and reused verbatim so the wording the model
# sees cannot drift from one turn to the next.


def _method(campus: str, year: str) -> str:
    return (
        f"Method: a merit-order simulation of the published {year} {campus} priority "
        "applications -- applicants placed by rank, each into the best still-open "
        "programme on their own list. A rank 'clears' a programme if it is at least as "
        "good as that programme's last-admitted rank. Open category only: a reserved-quota "
        "applicant competes in a different pool and these figures do not describe it."
    )


def _caveat(campus: str, year: str) -> str:
    return (
        f"Caveat: these are {year} figures, not a promise for this year. A cutoff moves "
        "every year with the applicant pool and the seat count, so treat it as guidance, "
        "never a guarantee, and never as a rank a student is 'safe' at."
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


def format_rank_guidance(rank: int, campus: str, year: str) -> str:
    """Which programmes a rank would and would not have cleared.

    The verdict is welded to every line -- "attainable" or "NOT attainable", with the
    comparison spelled out in words -- because the model cannot be trusted to derive it
    from the raw numbers. Handed a bare "- Computer Regular (last admitted rank 55)" for a
    rank of 2000, qwen2.5:7b read 55 as "much higher than your rank" and promoted a
    programme the rank misses by a mile. A smaller rank number being better is not
    something a 7B model reliably knows, so it is never left to work it out: each line
    states the outcome outright, and the not-attainable list is labelled do-not-offer.
    """
    cutoff = allocation(campus, year)

    # Grouped by programme with Regular above its Full-fee twin, NOT sorted by cutoff.
    # Sorted by cutoff the list opens with whichever programme was tightest, which for a
    # mid-range rank means three Full-fee seats at the top -- and the model read that
    # order as a recommendation and advised putting Full-fee first. That is the one piece
    # of advice _STRATEGY exists to forbid, so the list is never in an order that suggests
    # it. Within a programme Regular is first because it is the same degree for less money.
    def shelf(code: int) -> tuple[str, int]:
        programme, category = CODES[campus][code]
        return programme, 0 if category == "Regular" else 1

    reached = [
        (value, code)
        for code, value in sorted(cutoff.items(), key=lambda item: shelf(item[0]))
        if value is not None and rank <= value
    ]
    missed = [
        (value, code)
        for code, value in sorted(cutoff.items(), key=lambda item: shelf(item[0]))
        if value is not None and rank > value
    ]

    header = f"[{campus} priority analysis: merit rank {rank}, {year} data]"
    summary = (
        f"A smaller rank number is better, so a programme was attainable only if {rank} "
        "is at least as good as (less than or equal to) its last-admitted rank."
    )
    if reached:
        attainable = (
            "Attainable. This list is alphabetical, not a ranking -- offer them in "
            "the student's own order of preference:\n"
            + "\n".join(
                f"- {_label(campus, code)}: attainable. Last-admitted rank {value}, and "
                f"{rank} is at least as good, so it would have been placed."
                for value, code in reached
            )
        )
    else:
        attainable = (
            f"Attainable: none. Every {campus} programme's last-admitted rank in {year} "
            f"was better than {rank}, so none would have taken this rank. Say so plainly "
            "and point the student to campuses or affiliated colleges with lower cutoffs."
        )
    missed_block = (
        (
            f"NOT attainable -- rank {rank} was past each one's last-admitted rank. Do "
            "not present these as a plan or imply the student can pick them; if mentioned "
            "at all, say plainly they were out of reach at this rank. When few or none "
            "were attainable, tell the student honestly that this rank is a stretch for "
            f"{campus} and point them to other campuses or affiliated colleges, which "
            "have lower cutoffs.\n"
            + "\n".join(
                f"- {_label(campus, code)}: last-admitted rank {value}"
                for value, code in missed
            )
        )
        if missed
        else ""
    )

    return "\n".join(
        part
        for part in (
            header,
            _method(campus, year),
            summary,
            attainable,
            missed_block,
            _caveat(campus, year),
            _STRATEGY,
        )
        if part
    )


def format_program_feasibility(
    rank: int, programme: str, text: str, campus: str, year: str
) -> str:
    """Whether a rank cleared the named programme -- "is X realistic as a first priority".

    Reports both categories unless the question fixed one.
    """
    cutoff = allocation(campus, year)
    lines = []
    for code in _codes_for(campus, programme, text):
        value = cutoff[code]
        if value is None:
            lines.append(
                f"{_label(campus, code)}: nobody reached this programme in the {year} "
                "simulation, so there is no last-admitted rank to compare against."
            )
        elif rank <= value:
            lines.append(
                f"{_label(campus, code)}: last admitted rank {value}. Rank {rank} was "
                "within that -- it would have been placed."
            )
        else:
            lines.append(
                f"{_label(campus, code)}: last admitted rank {value}. Rank {rank} was "
                "past that -- it would not have been placed."
            )
    header = (
        f"[{campus} priority analysis: merit rank {rank}, {programme}, {year} data]"
    )
    return "\n".join(
        [header, _method(campus, year), *lines, _caveat(campus, year), _STRATEGY]
    )


# Questions the fixed rules answer. Separate from _PRIORITY_INTENT_RE, which wants a rank
# and is about outcomes; this is about the mechanism and needs no rank at all. Kept narrow:
# it must fire on "what if I refuse a lower priority" and not on every mention of a
# programme, because the rules block is long and crowds out whatever sits below it.
_RULES_INTENT_RE = re.compile(
    r"\bpriorit(?:y|ies)\b|\bpreference\s+(?:form|order|list)\b|"
    r"\b(?:refus\w*|reject\w*|decline\w*|turn(?:ing)?\s+down|not\s+tak\w*|"
    r"do\s*n[o']?t\s+(?:take|want|accept))\b.{0,40}\b(?:seat|programme|program|offer|"
    r"admission|list)\b|"
    r"\bexcluded\b|\bforfeit\w*\b|\bgive\s+up\b.{0,20}\bseat\b|"
    r"\bwhat\s+order\b|\bin\s+what\s+order\b|\bhow\s+many\s+choices\b",
    re.IGNORECASE,
)


def is_rules_question(text: str) -> bool:
    """Whether the fixed priority-order rules answer this, rank or no rank."""
    return bool(_RULES_INTENT_RE.search(text or ""))


def chance_context(text: str, campus: str = CAMPUS) -> str:
    """Context for a priority question, or "" when this is not one we can answer.

    Fires only on a rank paired with intent to choose or place programmes, and never when
    a campus we hold no data for is named. Read from the raw question, like the pass-list
    lookup, so a rank survives verbatim rather than through a paraphrase or a translation.
    """
    year = latest(campus)
    if not year or _OTHER_CAMPUS_RE.search(text):
        return ""
    programmes_named = find_programs(text)
    if not (_PRIORITY_INTENT_RE.search(text) or programmes_named):
        return ""
    ranks = find_ranks(text, include_topper=False)
    if not ranks:
        return ""
    if programmes_named:
        return "\n\n".join(
            format_program_feasibility(ranks[0], programme, text, campus, year)
            for programme in programmes_named
        )
    return format_rank_guidance(ranks[0], campus, year)


if __name__ == "__main__":
    print(f"{CAMPUS} programmes: {', '.join(programmes())}")
    print(f"priorities: {priority_count()}")
    print(f"datasets: {[f'{c} {y}' for c, y in datasets()]}")
    for campus, year in datasets():
        placed = allocation(campus, year)
        print(f"\n{campus} {year}: {len(_applicants(campus, year))} applicants")
        for code, value in sorted(placed.items()):
            print(f"  {_label(campus, code):<46} {value}")
    print()
    for line in verify() or ["every check clean"]:
        print(line)
