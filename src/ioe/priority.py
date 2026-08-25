"""Pulchowk's priority-order rules, written out rather than retrieved.

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
"""

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
    """Check the derived priority count against the number the notice prints."""
    counted = priority_count()
    if counted != PUBLISHED_PRIORITIES:
        return [
            (
                f"{CAMPUS}: seats.py yields {counted} priorities, "
                f"the notice prints {PUBLISHED_PRIORITIES}"
            )
        ]
    return []


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


if __name__ == "__main__":
    print(f"{CAMPUS} programmes: {', '.join(programmes())}")
    print(f"priorities: {priority_count()}")
    for line in verify() or ["the derived priority count agrees with the notice"]:
        print(line)
