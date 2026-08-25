"""How many seats each campus and college takes, per programme.

The same bargain as `fees.py`, for the same reason. The seat matrix is a grid of small
numerals set in a scanned table, and the booklet's own translation carries a warning
about exactly that:

    Sections 6 (quota tables) and 9 (fee table) contain dense grids of small numerals
    read from scanned table images. These are the highest-risk part of this translation
    for digit-level transcription error.

So only the grid is stored here, every total is summed from it, and `verify()` re-derives
all seventeen totals the booklet printed. A transcription slip shows up as a subtotal
that no longer adds up, which is a thing a test can see -- rather than as a seat count
quietly wrong by 48 in an answer a student is planning around.

That is not hypothetical. Checked against the source PDF, the constituent grid in
`docs/translated/06_BE_BArch_Booklet_2083_English.md` is correct cell for cell, and the
affiliated grid had **nine** cells wrong -- three of its ten column totals did not add up,
and the error cancelled to leave the printed grand total looking right. The figures below
are the PDF's, which reconcile completely.

The numbers here are admission targets: how many students an institution takes. They are
not a rank threshold, and nothing in this module will tell a student whether their rank
reaches one. See `docs/data/cutoffs.csv` for that, and for why it is empty.
"""

import re

# Column order is the booklet's own, so a row here reads the way the printed row reads.
CAMPUSES = ("Pulchowk", "Pashchimanchal", "Purwanchal", "Thapathali", "Chitwan")

COLLEGES = (
    "Kantipur Engineering College",
    "Kathmandu Engineering College",
    "Himalaya College of Engineering",
    "Advanced College of Engineering and Management",
    "National College of Engineering",
    "Kathford International College of Engineering and Management",
    "Janakpur Engineering College",
    "Khwopa College of Engineering",
    "Sagarmatha Engineering College",
    "Lalitpur Engineering College",
)

# Constituent campuses, table 2.7. One tuple per programme, in CAMPUSES order.
REGULAR = {
    "Civil": (108, 36, 36, 36, 0),
    "Architecture": (24, 0, 12, 12, 6),
    "Electrical": (36, 12, 12, 0, 0),
    "Electronics, Communication and Information": (24, 12, 12, 12, 0),
    "Mechanical": (24, 12, 24, 12, 0),
    "Computer": (36, 12, 24, 12, 0),
    "Aerospace": (12, 0, 0, 0, 0),
    "Agriculture": (0, 0, 12, 0, 0),
    "Industrial": (0, 0, 0, 12, 0),
    "Geomatics": (0, 12, 0, 0, 0),
    "Automobile": (0, 12, 0, 12, 0),
    "Chemical": (12, 0, 0, 0, 0),
}
FULL_FEE = {
    "Civil": (84, 108, 108, 108, 0),
    "Architecture": (24, 0, 36, 36, 18),
    "Electrical": (60, 36, 36, 0, 0),
    "Electronics, Communication and Information": (24, 36, 36, 36, 0),
    "Mechanical": (24, 36, 72, 36, 0),
    "Computer": (60, 36, 72, 36, 0),
    "Aerospace": (36, 0, 0, 0, 0),
    "Agriculture": (0, 0, 36, 0, 0),
    "Industrial": (0, 0, 0, 36, 0),
    "Geomatics": (0, 36, 0, 0, 0),
    "Automobile": (0, 36, 0, 36, 0),
    "Chemical": (36, 0, 0, 0, 0),
}

# TU-affiliated colleges, same table. These carry one figure per college, not a
# Regular/Full Fee split: an affiliated college charges its own fee to everyone.
AFFILIATED = {
    "Civil": (96, 96, 96, 96, 96, 96, 96, 96, 48, 48),
    "Architecture": (0, 48, 48, 0, 0, 0, 0, 0, 0, 0),
    "Electrical": (0, 48, 0, 48, 48, 0, 0, 48, 0, 0),
    "Electronics, Communication and Information": (
        96,
        96,
        48,
        96,
        48,
        48,
        48,
        0,
        48,
        0,
    ),
    "Computer": (96, 96, 48, 96, 48, 48, 48, 48, 48, 48),
}

# The booklet's own printed totals, used only to check the sums above.
PUBLISHED_CAMPUS = {
    "Pulchowk": (276, 348),
    "Pashchimanchal": (108, 324),
    "Purwanchal": (132, 396),
    "Thapathali": (108, 324),
    "Chitwan": (6, 18),
}
PUBLISHED_COLLEGE = (288, 384, 240, 336, 240, 192, 192, 192, 144, 96)
PUBLISHED_CONSTITUENT_TOTAL = 2040
PUBLISHED_AFFILIATED_TOTAL = 2304

SEAT_SOURCE = {
    "title": "IOE BE/BArch Admission Booklet 2083 - campuses, seats and quotas",
    "year": "2083",
    "url": "https://entrance.ioe.edu.np/Notice/Detail/5089",
    "file": "06_BE_BArch_Booklet_2083_English.md",
    "sections": ["2.7 Admission Targets by Campus/College"],
}


def verify() -> list[str]:
    """Re-derive every total the booklet printed. An empty list means they all agree."""
    problems: list[str] = []

    for index, campus in enumerate(CAMPUSES):
        regular = sum(row[index] for row in REGULAR.values())
        full = sum(row[index] for row in FULL_FEE.values())
        want = PUBLISHED_CAMPUS[campus]
        if (regular, full) != want:
            problems.append(
                f"{campus}: computed {regular}/{full}, booklet prints {want[0]}/{want[1]}"
            )

    constituent = sum(sum(row) for row in REGULAR.values()) + sum(
        sum(row) for row in FULL_FEE.values()
    )
    if constituent != PUBLISHED_CONSTITUENT_TOTAL:
        problems.append(
            f"constituent total: computed {constituent}, "
            f"booklet prints {PUBLISHED_CONSTITUENT_TOTAL}"
        )

    for index, college in enumerate(COLLEGES):
        seats = sum(row[index] for row in AFFILIATED.values())
        if seats != PUBLISHED_COLLEGE[index]:
            problems.append(
                f"{college}: computed {seats}, booklet prints {PUBLISHED_COLLEGE[index]}"
            )

    affiliated = sum(sum(row) for row in AFFILIATED.values())
    if affiliated != PUBLISHED_AFFILIATED_TOTAL:
        problems.append(
            f"affiliated total: computed {affiliated}, "
            f"booklet prints {PUBLISHED_AFFILIATED_TOTAL}"
        )

    return problems


# ── Reading the question ──────────────────────────────────────────────────────
# Students do not write "Electronics, Communication and Information". They write "ECE",
# or "electronics", or "ioe pulchowk computer". Campuses are worse: Pashchimanchal is
# "Pokhara" to most people and "WRC" to the rest, and Purwanchal is "Dharan".

_CAMPUS_ALIASES = {
    "Pulchowk": r"pulchowk|pulchok|ioe\s+pulchowk|पुल्चोक",
    "Pashchimanchal": r"pashchimanchal|paschimanchal|western\s+region|wrc|pokhara|पश्चिमाञ्चल",
    "Purwanchal": r"purwanchal|purbanchal|eastern\s+region|dharan|पूर्वाञ्चल",
    "Thapathali": r"thapathali|tcioe|थापाथली",
    "Chitwan": r"chitwan|chitawan|rampur|चितवन",
}

_PROGRAMME_ALIASES = {
    "Civil": r"civil",
    "Architecture": r"architect\w*|b\.?\s?arch\b",
    "Electrical": r"electrical",
    "Electronics, Communication and Information": (
        r"electronics?|ece\b|eci\b|communication|information\s+engineering"
    ),
    "Mechanical": r"mechanical",
    "Computer": r"computer|comp\b|software",
    "Aerospace": r"aerospace|aeronautical",
    "Agriculture": r"agricultur\w*",
    "Industrial": r"industrial",
    "Geomatics": r"geomatic\w*|geomatrics|surveying",
    "Automobile": r"automobile|automotive",
    "Chemical": r"chemical",
}

_SEAT_INTENT = re.compile(
    r"\b(seat|seats|सिट|सीट|quota|capacity|intake|admission\s+target|targets|"
    r"how\s+many\s+(?:students|are\s+taken|get\s+in|places)|places|vacan\w*|"
    r"kati\s+seat)\b",
    re.IGNORECASE,
)

# A rank next to a seat count is the question this app must not answer as a threshold.
# It is detected only so the block can say so; see the note seat_context appends.
_RANK_NEARBY = re.compile(
    r"\b(rank|योग्यताक्रम|merit|chance|chances|probability|"
    r"will\s+i\s+get|can\s+i\s+get|do\s+i\s+get)\b",
    re.IGNORECASE,
)


def find_campuses(text: str) -> list[str]:
    """Which campuses the question names, in the booklet's column order."""
    return [c for c in CAMPUSES if re.search(_CAMPUS_ALIASES[c], text, re.IGNORECASE)]


def find_colleges(text: str) -> list[str]:
    """Which affiliated colleges the question names."""
    found = []
    for college in COLLEGES:
        head = college.split()[0]
        if re.search(rf"\b{re.escape(head)}\b", text, re.IGNORECASE):
            found.append(college)
    return found


def find_programmes(text: str) -> list[str]:
    """Which programmes the question names, in the booklet's row order."""
    return [p for p in REGULAR if re.search(_PROGRAMME_ALIASES[p], text, re.IGNORECASE)]


def is_seat_question(text: str) -> bool:
    """Whether the question is about how many places an institution has."""
    return bool(_SEAT_INTENT.search(text))


TOTAL_LABEL = "ALL programmes"


def _cell(value: int) -> str:
    """A dash where the campus does not offer the programme, so it reads as absent."""
    return "-" if not value else str(value)


def format_constituent(campuses: list[str], programmes: list[str]) -> str:
    """The constituent grid, narrowed to what was asked about."""
    campuses = campuses or list(CAMPUSES)
    programmes = programmes or list(REGULAR)
    indexes = [CAMPUSES.index(c) for c in campuses]

    # The totals row's label is wider than most programme names, and a label that
    # overflows its column shifts every figure on that line. Issue 23 records what that
    # costs: a Full Fee figure read off as the Regular one.
    width = max(len(p) for p in (*programmes, TOTAL_LABEL)) + 2
    head = "Programme".ljust(width) + "".join(f"{c:>22}" for c in campuses)
    lines = [head, "-" * len(head)]
    for name in programmes:
        cells = "".join(
            f"{_cell(REGULAR[name][i]) + ' / ' + _cell(FULL_FEE[name][i]):>22}"
            for i in indexes
        )
        lines.append(name.ljust(width) + cells)
    lines.append("-" * len(head))
    totals = "".join(
        f"{str(PUBLISHED_CAMPUS[c][0]) + ' / ' + str(PUBLISHED_CAMPUS[c][1]):>22}"
        for c in campuses
    )
    lines.append(TOTAL_LABEL.ljust(width) + totals)
    return "\n".join(lines)


def seat_context(text: str, force: bool = False) -> str:
    """The authoritative seat block, or "" when the question is not about seats.

    `force` is for a model that asked for seat figures by name, having read a
    conversation the detector cannot see. See fees.fee_context for the same argument.
    """
    if not force and not is_seat_question(text):
        return ""

    campuses = find_campuses(text)
    programmes = find_programmes(text)
    colleges = find_colleges(text)

    affiliated = ""
    if colleges or (not campuses and not programmes):
        affiliated = (
            f"\n\nTU-affiliated colleges take {PUBLISHED_AFFILIATED_TOTAL} students "
            f"between them, against {PUBLISHED_CONSTITUENT_TOTAL} at the five "
            "constituent campuses. An affiliated college charges its own fee to "
            "everyone, so its seats carry no Regular / Full Fee split."
        )
    for college in colleges:
        index = COLLEGES.index(college)
        offered = ", ".join(
            f"{name} {row[index]}" for name, row in AFFILIATED.items() if row[index]
        )
        affiliated += f"\n{college}: {PUBLISHED_COLLEGE[index]} seats -- {offered}."

    # Only when the student has put a rank or their chances next to the question. The
    # rule is in the system prompt as well, but a seat table and a rank in the same
    # prompt is exactly the arrangement that invites the comparison, so it is repeated
    # where the numbers are.
    rank_note = ""
    if _RANK_NEARBY.search(text):
        rank_note = (
            "\n- The student has mentioned a rank, or asked what their chances are. Say "
            "directly that these are seat counts and cannot answer that, and that you "
            "have no cutoff figures at all. Do not estimate, and do not soften it into "
            "a maybe."
        )

    return f"""AUTHORITATIVE SEAT FIGURES -- approved admission targets for admission year
2083, from table 2.7 of the IOE booklet. Every cell is Regular / Full Fee.

Read the figure off the table and write it into a sentence of your own. Never paste a row
of the table. A dash means the campus does not offer that programme at all -- say that,
rather than reporting zero seats.

{format_constituent(campuses, programmes)}{affiliated}

How to read these:
- A seat count is how many students the institution admits. It is NOT a rank threshold,
  and it says nothing about how far down the merit list admission actually reached. Never
  compare a student's rank against one of these numbers, and never tell a student their
  rank is within, safe for, qualifies for, or is close to a programme.
- Reserved seats come out of these totals rather than adding to them: 20 percent of the
  Regular seats are inclusive quota, with further women's, teacher and staff, sponsored
  and foreign quotas set out in section 6 of the booklet.
- An affiliated college may enrol up to 10 percent above its target, provided it charges
  those extra students IOE's own regular rate.
- If a programme's Full Fee seats do not fill to 60 percent across the first three
  admission lists, a constituent campus may suspend that programme for the year and
  refund the admission fee.{rank_note}"""


if __name__ == "__main__":
    for line in verify() or ["every published total agrees"]:
        print(line)
