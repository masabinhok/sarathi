"""What rank actually got in, for the four campuses and four years anyone has published.

This is the "before the priority form" half of the chances question. A student who has not
applied yet has exactly one fact about themselves -- their rank -- and the only honest way
to say anything is to show where that rank would have landed in previous years and to be
loud about the ways that is not a prediction.

The "after the form" half is `priority.py`, which simulates the actual allocation over the
published priority applications and can say what a rank lands on rather than what it would
have landed on. When both can answer, `priority.py` is the better answer, because it is
about this year's applicants rather than the last four years' ones.

**Where the figures come from.** `docs/data/cutoffs.csv`, built by `notes/scrape_cutoffs.py`
from a public collection of first-list cutoffs that states each is recalculated from the
campus admission list it links to. `source_url` on every row is that admission list -- the
primary document -- so a citation sends a student where every other module sends them. Some
Purwanchal rows have no link and carry an empty `source_url`; an empty cell is a known gap
and a wrong citation is a student sent to the wrong document.

**What is not in it, all of which the block says out loud.**

    Open/general category only. A quota applicant's competition is a different pool and
    these numbers do not describe it.
    First list only. Merit lists move as admitted students take higher priorities, so the
    rank that eventually got in is deeper than the rank recorded here.
    Four campuses. Chitwan publishes no comparable figures and is absent entirely.
    Constituent campuses only -- no affiliated college is covered.

The one thing this module refuses to do is turn a rank into a probability. Nothing here
knows how many people will apply next year.
"""

import csv
import re
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

from ioe import seats

CUTOFFS_CSV = Path(__file__).resolve().parents[2] / "docs" / "data" / "cutoffs.csv"

# How close to a published cutoff still counts as "about there" rather than "inside".
# A merit list moves between admission rounds as admitted students move up their own
# priority lists, so a rank a little past the first list's cutoff is not out.
MARGIN = 0.05

CATEGORIES = ("Regular", "Full-fee")


@lru_cache(maxsize=1)
def _rows() -> list[dict[str, str]]:
    """Every recorded cutoff. A missing or header-only file yields an empty list."""
    if not CUTOFFS_CSV.exists():
        return []
    with CUTOFFS_CSV.open(encoding="utf-8", newline="") as fh:
        return [row for row in csv.DictReader(fh) if row.get("closing_rank")]


@lru_cache(maxsize=1)
def _index() -> dict[tuple[str, str, str], dict[str, int]]:
    """(campus, programme, category) -> {year: rank}."""
    out: dict[tuple[str, str, str], dict[str, int]] = defaultdict(dict)
    for row in _rows():
        key = (row["campus"], row["programme"], row["category"])
        out[key][row["year"]] = int(row["closing_rank"])
    return dict(out)


@lru_cache(maxsize=1)
def years() -> list[str]:
    return sorted({row["year"] for row in _rows()}, reverse=True)


def covered_campuses() -> list[str]:
    """The campuses any figure exists for, in seats.py's order."""
    present = {key[0] for key in _index()}
    return [campus for campus in seats.CAMPUSES if campus in present]


def have_data() -> bool:
    return bool(_rows())


def _match(campus: str, programme: str, category: str) -> tuple[str, str, str] | None:
    """Case-insensitive lookup of a key that is stored in the booklet's spelling."""
    wanted = (campus.casefold(), programme.casefold(), category.casefold())
    for key in _index():
        if tuple(part.casefold() for part in key) == wanted:
            return key
    return None


def history(campus: str, programme: str, category: str = "Regular") -> dict[str, int]:
    """{year: closing rank}, newest first, or {} if nothing is recorded."""
    key = _match(campus, programme, category)
    return dict(sorted(_index()[key].items(), reverse=True)) if key else {}


def cutoff(campus: str, programme: str, category: str = "Regular") -> int | None:
    """The most recent year's cutoff, which is the one a student should reason from."""
    recorded = history(campus, programme, category)
    return recorded[next(iter(recorded))] if recorded else None


def against_each_year(
    rank: int, campus: str, programme: str, category: str = "Regular"
) -> list[tuple[str, int, str]]:
    """(year, closing rank, verdict) for every recorded year, newest first.

    All four years rather than the newest one, and compared rather than averaged. A mean
    of 724 and 1270 is a number no admission list ever produced, and it hides the thing a
    student most needs to see -- that the figure moves, and by how much. Four verdicts
    say "this held every year" or "this held once out of four", which is a real answer to
    "what are my chances" without inventing a probability.
    """
    verdicts = []
    for year, closed in history(campus, programme, category).items():
        if rank <= closed * (1 - MARGIN):
            verdict = "cleared"
        elif rank <= closed * (1 + MARGIN):
            verdict = "borderline"
        else:
            verdict = "missed"
        verdicts.append((year, closed, verdict))
    return verdicts


# How the count of cleared years is put into words. Never a percentage and never a
# promise: the count is a fact about four past lists, and the sentence says only that.
CHANCE = {
    4: "cleared in every one of the {total} recorded years -- the strongest signal this "
    "data can give, though still not a promise",
    3: "cleared in {cleared} of the {total} recorded years -- it held in most of them",
    2: "cleared in {cleared} of the {total} recorded years -- genuinely borderline, it "
    "went both ways",
    1: "cleared in only {cleared} of the {total} recorded years -- it held once and "
    "missed the rest",
    0: "cleared in none of the {total} recorded years",
}


def chance_line(rank: int, verdicts: list[tuple[str, int, str]]) -> str:
    """The one sentence that answers "what are my chances", counted not estimated."""
    cleared = sum(1 for _, _, verdict in verdicts if verdict == "cleared")
    borderline = sum(1 for _, _, verdict in verdicts if verdict == "borderline")
    total = len(verdicts)
    reading = CHANCE[min(cleared, 4)].format(cleared=cleared, total=total)
    line = f"Rank {rank} would have {reading}."
    if borderline:
        line += (
            f" A further {borderline} year(s) were within {int(MARGIN * 100)}% either "
            "way, which is too close to call."
        )
    return line


def sources_for(
    campus: str, programme: str, category: str = "Regular"
) -> dict[str, str]:
    """year -> the official admission list behind that year's figure, newest first."""
    wanted = (campus.casefold(), programme.casefold(), category.casefold())
    found: dict[str, str] = {}
    for row in _rows():
        key = (
            row["campus"].casefold(),
            row["programme"].casefold(),
            row["category"].casefold(),
        )
        if key == wanted and row.get("source_url"):
            found[row["year"]] = row["source_url"]
    return dict(sorted(found.items(), reverse=True))


def source_for(campus: str, programme: str, category: str = "Regular") -> str:
    """The official admission list behind the most recent recorded figure."""
    recorded = history(campus, programme, category)
    if not recorded:
        return ""
    newest = next(iter(recorded))
    for row in _rows():
        if (
            row["campus"].casefold() == campus.casefold()
            and row["programme"].casefold() == programme.casefold()
            and row["category"].casefold() == category.casefold()
            and row["year"] == newest
        ):
            return row.get("source_url", "")
    return ""


def verify() -> list[str]:
    """Assertions that catch a transcription error rather than trusting the scrape.

    Two of these hold only because the data is real: a programme with a cutoff must have
    seats at that campus in seats.py, which was transcribed from the booklet by a
    different route entirely; and a Full-fee cutoff must sit deeper than its Regular
    counterpart, because a Regular seat is cheaper for the same degree and so fills first.
    A violation of either means a column was read wrong.
    """
    problems: list[str] = []
    index = {campus: i for i, campus in enumerate(seats.CAMPUSES)}

    for (campus, programme, category), by_year in _index().items():
        position = index.get(campus)
        if position is None:
            problems.append(f"{campus}: not a constituent campus in seats.py")
            continue
        table = seats.REGULAR if category == "Regular" else seats.FULL_FEE
        allocation = table.get(programme)
        if allocation is None:
            problems.append(f"{programme}: no such programme in seats.py")
        elif allocation[position] == 0:
            problems.append(
                f"{campus} {programme} ({category}): cutoff recorded but seats.py "
                "gives the programme no seats there"
            )
        for year, rank in by_year.items():
            if rank < 1:
                problems.append(
                    f"{campus} {programme} {year}: rank {rank} is not a rank"
                )

    for (campus, programme, category), by_year in _index().items():
        if category != "Regular":
            continue
        paid = _index().get((campus, programme, "Full-fee"), {})
        for year, rank in by_year.items():
            if year in paid and rank > paid[year]:
                problems.append(
                    f"{campus} {programme} {year}: Regular cutoff {rank} is deeper than "
                    f"Full-fee {paid[year]}, which inverts how the two fill"
                )
    return problems


# The caveats, written once and reused, so the wording the model sees cannot drift from
# one turn to the next. Every one of these is a way a student could act on the number and
# be wrong, and the model is told to say them rather than left to infer them.
SCOPE = (
    "These are open/general category figures from each year's FIRST admission list, for "
    "constituent campuses only. They do not describe reserved-quota competition, they do "
    "not include later lists (which always reach deeper as admitted students take higher "
    "priorities), and no figures exist for Chitwan or for any affiliated college."
)

# A smaller rank number being better is not something a 7B model reliably knows -- see
# priority.format_rank_guidance, where it read "last admitted rank 55" as standing above
# a rank of 2000. So the comparison is spelled out rather than left to be derived.
ORDINAL = (
    "A smaller rank number is better. A programme was within reach only if the student's "
    "rank is a smaller number than, or equal to, the rank its list closed at."
)

CAVEAT = (
    "State the year of every figure you quote. A cutoff moves each year with the size of "
    "the applicant pool and the seat count, so past years are guidance and never a "
    "promise. Never turn this into a percentage or a probability, never call a rank "
    "'safe', and never say a student will or will not get in."
)


# A rank plus intent to place it. Without the intent "rank 340" is a pass-list question
# that results.py already answers, and firing here as well would put a stranger's cutoff
# history under a question about who holds that rank.
_INTENT = re.compile(
    r"\bcut[\s-]?off?s?\b|\bclosing\s+rank\b|\blast\s+rank\b|"
    r"\bcan\s+i\s+(?:get|enter|join)\b|\bwill\s+i\s+get\b|\bwould\s+i\s+(?:get|have)\b|"
    r"\bchanc\w*\b|\bwhat\s+can\s+i\s+(?:get|study|choose)\b|\bgood\s+enough\b|"
    r"\benough\s+for\b|\bqualif\w*\s+for\b|\beligible\s+for\b|\bmy\s+rank\b|"
    r"\bwith\s+rank\b|\bat\s+rank\b|\bsafe\b",
    re.IGNORECASE,
)


def is_cutoff_question(text: str) -> bool:
    """Whether this is a rank-against-cutoff question rather than a pass-list lookup."""
    return bool(_INTENT.search(text or ""))


def reachable(rank: int, category: str = "Regular") -> list[tuple[str, str, int, int]]:
    """(campus, programme, years cleared, years recorded) that this rank ever cleared.

    Sorted by how many years it held, most first. Ranking by a single year's figure would
    put a programme that happened to be soft once above one that held every year, which is
    the opposite of what a student choosing between them needs.
    """
    out: list[tuple[str, str, int, int]] = []
    for (campus, programme, cat), by_year in _index().items():
        if cat.casefold() != category.casefold():
            continue
        cleared = sum(1 for closed in by_year.values() if rank <= closed)
        if cleared:
            out.append((campus, programme, cleared, len(by_year)))
    return sorted(out, key=lambda row: (-row[2], row[1], row[0]))


def reachable_context(rank: int, category: str = "Regular") -> str:
    """Every programme this rank cleared in at least one recorded year."""
    span = ", ".join(years())
    options = reachable(rank, category)
    if not options:
        return (
            f"[Cutoff history: nothing reached rank {rank} in {span}]\n"
            f"In none of the recorded years did any {category} first list at the four "
            f"covered campuses reach rank {rank}. Say that plainly. Say too that later "
            "admission lists reach considerably deeper than the first, that Full Fee "
            "seats reach deeper than Regular ones, and that affiliated colleges are not "
            "covered here at all -- so this is not the same as saying there is nothing "
            "available.\n" + SCOPE + "\n" + ORDINAL + "\n" + CAVEAT
        )
    width = max(len(programme) for _, programme, _, _ in options) + 2
    lines = "\n".join(
        f"    {programme:<{width}}{campus:<16}cleared {cleared} of {total} years"
        for campus, programme, cleared, total in options
    )
    held = [row for row in options if row[2] == row[3]]
    strongest = (
        "Strongest: "
        + ", ".join(f"{programme} at {campus}" for campus, programme, _, _ in held[:6])
        + f" -- cleared in all {options[0][3]} recorded years."
        if held
        else "None of these cleared in every recorded year."
    )
    return (
        f"[Cutoff history: what rank {rank} would have cleared, {span}]\n"
        f"Each {category} programme is compared against all {len(years())} recorded "
        f"years, not averaged across them -- a cutoff moves, and how often it held is "
        f"the honest answer to what a rank is worth:\n"
        f"{lines}\n"
        f"{strongest}\n"
        "Give this as what happened in those years and how consistently, never as what "
        "the student will get. Nobody can guarantee a place.\n"
        + SCOPE
        + "\n"
        + ORDINAL
        + "\n"
        + CAVEAT
    )


def _trend(recorded: dict[str, int]) -> str:
    """The history, newest first, with the newest figure also stated on its own.

    Written as one pair per line rather than a run of "2082: 387  2081: 278  2080: 273",
    and with the headline repeated above it. Observed once: asked for Thapathali Civil,
    the model read that run and answered "367 in 2083" -- a digit and a year both wrong,
    out of a block that was correct. The same discipline as priority.format_rank_guidance:
    state the figure that answers the question rather than leaving it to be picked out.
    """
    newest = next(iter(recorded))
    lines = "\n".join(f"    {year}: {rank}" for year, rank in recorded.items())
    return (
        f"Most recent ({newest}): {recorded[newest]}\n  Every recorded year:\n{lines}"
    )


def history_context(campus: str, programme: str, category: str = "Regular") -> str:
    """What a programme's cutoffs were, with no rank to measure against.

    "What was the cutoff for Civil at Thapathali" is a real question and does not need
    the student's own rank. Answering it with "tell me your rank first" would be a
    non-answer to something the data covers exactly.
    """
    recorded = history(campus, programme, category)
    if not recorded:
        return ""
    source = source_for(campus, programme, category)
    return (
        f"[Cutoff history: {programme} ({category}) at {campus} Campus]\n"
        f"Closing rank of the first list -- the last rank admitted -- by year:\n  {_trend(recorded)}\n"
        + (f"Published list this comes from: {source}\n" if source else "")
        + SCOPE
        + "\n"
        + ORDINAL
        + "\n"
        + CAVEAT
    )


def cutoff_context(
    rank: int, campus: str, programme: str, category: str = "Regular"
) -> str:
    """The block, or the block that says there is nothing to go on."""
    if not have_data():
        return (
            "[Cutoff data: none recorded]\n"
            "No admission list has been transcribed into this app, so there is no record "
            "of what rank was actually admitted anywhere. Say plainly that you do not "
            "have cutoff figures and will not guess one, and point the student at the "
            "campus's published admission lists. Do not estimate from the number of "
            "seats: a seat count says how many students a campus takes, not how far down "
            "the merit list it reached."
        )

    recorded = history(campus, programme, category)
    if not recorded:
        covered = ", ".join(sorted({key[0] for key in _index()}))
        return (
            f"[Cutoff data: nothing recorded for {programme} ({category}) at {campus}]\n"
            f"Recorded campuses are {covered}; years are {', '.join(years())}.\n"
            "Say that this particular programme and campus is not one you hold figures "
            "for. Do not reason across from another programme's cutoff, another campus's "
            "cutoff, or the seat count.\n" + SCOPE
        )

    verdicts = against_each_year(rank, campus, programme, category)
    cited = sources_for(campus, programme, category)
    said = {
        "cleared": "would have cleared it -- the list reached past this rank",
        "borderline": f"was within {int(MARGIN * 100)}% of it -- too close to call",
        "missed": "would have been past it -- the list stopped short of this rank",
    }
    # The verdict is welded to every line rather than left to be derived from the two
    # numbers beside it. See priority.format_rank_guidance: handed a bare closing rank of
    # 55 and a student rank of 2000, the model read 55 as the larger of the two.
    lines = "\n".join(
        f"    {year}: closed at {closed:<6} rank {rank} {said[verdict]}"
        for year, closed, verdict in verdicts
    )

    return (
        f"[Cutoff history: {programme} ({category}) at {campus} Campus]\n"
        f"The student's rank: {rank}\n"
        f"Each recorded year's first admission list, and where {rank} sits against it:\n"
        f"{lines}\n"
        f"{chance_line(rank, verdicts)}\n"
        "Give this as the reading: say how many of the years it would have cleared and "
        "name them. That is a description of what happened, not a prediction. Say plainly "
        "that nobody can guarantee a place, because the pool and the seat count change "
        "every year.\n"
        + (
            "Published list each year's figure comes from:\n"
            + "\n".join(f"    {year}: {url}" for year, url in cited.items())
            + "\n"
            if cited
            else ""
        )
        + SCOPE
        + "\n"
        + ORDINAL
        + "\n"
        + CAVEAT
    )


if __name__ == "__main__":
    print(f"{len(_rows())} cutoffs across {len(_index())} programme/category pairs")
    print(f"years: {', '.join(years())}")
    print(f"verify: {verify() or 'clean'}")
    print()
    print(cutoff_context(660, "Pulchowk", "Computer"))
