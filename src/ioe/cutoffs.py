"""What rank actually got in, and an honest answer when nobody knows.

This is the module behind the request in issue `25`: estimate a student's chance of
getting a programme from their rank. The estimate needs three things -- how many seats a
programme has, how many higher-ranked students chose it, and where the merit list
actually stopped last time. The first is in `seats.py`. The other two are in nobody's
hands here: the published pass list carries rank, name, gender and district and **no
programme or campus column**, so it cannot say what any candidate applied for.

So the arithmetic is written and the data is not invented. `docs/data/cutoffs.csv` holds
the lowest rank admitted per programme per list, and it currently holds only its header.
Asked about a programme it has no row for, this module says so. It does not interpolate
from seat counts, and it does not reason from a rank's position among 7,179 candidates:
a seat count says how many students a campus takes, not how far down the list it reached,
and the difference between those two is a student choosing a campus on a wrong number.

`docs/README.md` records where the real figures are published and what filling this file
involves.
"""

import csv
from functools import lru_cache
from pathlib import Path

CUTOFFS_CSV = Path(__file__).resolve().parents[2] / "docs" / "data" / "cutoffs.csv"

# How close to the published cutoff still counts as "about there" rather than "inside".
# A merit list moves between admission rounds as admitted students move up their own
# priority lists, so a rank a little past the first list's cutoff is not out.
MARGIN = 0.05


@lru_cache(maxsize=1)
def _rows() -> list[dict[str, str]]:
    """Every recorded cutoff. A missing or header-only file yields an empty list."""
    if not CUTOFFS_CSV.exists():
        return []
    with CUTOFFS_CSV.open(encoding="utf-8", newline="") as fh:
        return [row for row in csv.DictReader(fh) if row.get("lowest_rank_admitted")]


def have_data() -> bool:
    """Whether any cutoff has been recorded at all."""
    return bool(_rows())


def cutoff(campus: str, programme: str, category: str = "Regular") -> int | None:
    """The deepest rank recorded as admitted, across every list for that programme.

    The deepest rather than the first list's, because that is the question a student is
    asking: not "who got in on day one" but "did it ever reach me".
    """
    ranks = [
        int(row["lowest_rank_admitted"])
        for row in _rows()
        if row.get("campus", "").casefold() == campus.casefold()
        and row.get("programme", "").casefold() == programme.casefold()
        and row.get("category", "").casefold() == category.casefold()
    ]
    return max(ranks) if ranks else None


def standing(rank: int, campus: str, programme: str, category: str = "Regular") -> str:
    """Where a rank sits against the recorded cutoff, or "" when nothing is recorded."""
    reached = cutoff(campus, programme, category)
    if reached is None:
        return ""
    if rank <= reached * (1 - MARGIN):
        return "inside"
    if rank <= reached * (1 + MARGIN):
        return "near"
    return "beyond"


def cutoff_context(
    rank: int, campus: str, programme: str, category: str = "Regular"
) -> str:
    """The block, or the block that says there is nothing to go on."""
    if not have_data():
        return (
            "[Cutoff data: none recorded]\n"
            "No admission list has been transcribed into this app yet, so there is no "
            "record of what rank was actually admitted to any programme. Say that "
            "plainly -- that you do not have cutoff figures and will not guess one -- "
            "and point the student to the campus's published admission lists and its "
            "admission office. Do not estimate from the number of seats: a seat count "
            "says how many students a campus takes, not how far down the merit list it "
            "reached. Do not tell them their rank is safe, close, or out of range."
        )
    reached = cutoff(campus, programme, category)
    if reached is None:
        return (
            f"[Cutoff data: nothing recorded for {programme} ({category}) at {campus}]\n"
            "Other programmes have recorded cutoffs but this one does not. Say that this "
            "particular programme is not one you have figures for, rather than reasoning "
            "from another programme's cutoff or from the seat count."
        )
    where = standing(rank, campus, programme, category)
    return (
        f"[Cutoff record: {programme} ({category}) at {campus}]\n"
        f"Deepest rank recorded as admitted: {reached}\n"
        f"The student's rank: {rank}\n"
        f"Reading: {where}\n"
        "This is what happened in a published list, not a prediction and not a "
        "guarantee. Say which admission year and list it comes from, and say that a "
        "merit list moves between rounds as admitted students take higher priorities, "
        "so a rank a little past the recorded figure is not necessarily out. Never "
        "phrase it as a probability or a percentage."
    )


if __name__ == "__main__":
    print(f"{len(_rows())} cutoffs recorded in {CUTOFFS_CSV.name}")
    print()
    print(cutoff_context(660, "Pulchowk", "Computer"))
