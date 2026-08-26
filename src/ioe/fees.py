"""Exact arithmetic over the published Pulchowk BE admission fee tables.

The fees are already in the corpus, and retrieval finds them. The model still gets the
answer wrong, because reading them requires arithmetic: a per-semester total multiplied
by eight, three separate tables added together, and one figure -- the amount due on
admission day -- that is a *part* of the degree total rather than an addition to it.
Asked what a Regular student pays for the whole degree, the assistant multiplied
correctly and then trailed off; asked for a total fee it invented a per-programme tuition
table that appears in no document; asked what is refundable it invented a refund policy.

So the totals are computed here and handed to the model already worked out, for the same
reason `dates.annotate_dates` hands it BS/AD conversions: a number the model reads is
right, a number it derives is a coin toss.

Only the line items are stored. Every total is summed from them, and `verify()` checks
each one against the figure printed in the notice -- so a typo in this file fails loudly
instead of teaching the assistant a wrong number. Where the two source documents disagree
the notice wins: its totals all reproduce from its own line items, and the booklet's do
not (it prints 286,470 as the Full Fee amount due at admission, where the line items give
216,470, and its Foreign column drifts by a few rupees in several places).
"""

import re

# The four fee categories, in the column order the published tables use.
CATEGORIES = ("Regular", "Full Fee", "Foreign Student", "Sponsored")

# Nepali names, so a question asked in Nepali reaches the same block.
CATEGORY_NEPALI = {
    "Regular": "नियमित",
    "Full Fee": "पूर्णशुल्कीय",
    "Foreign Student": "विदेशी विध्यार्थी",
    "Sponsored": "प्रायोजित",
}

# BE is eight semesters. BArch runs ten, which the block states rather than assumes.
SEMESTERS = 8
BARCH_SEMESTERS = 10

# Table A -- charged every semester.
PER_SEMESTER = {
    "Tuition fee": (2862, 46854, 134755, 60910),
    "Admit card fee": (200, 200, 200, 200),
    "Laboratory fee": (200, 200, 200, 200),
    "Library fee": (50, 200, 200, 200),
    "Examination fee": (3062, 3062, 3062, 3062),
    "Examination centre fee": (150, 150, 150, 150),
    "Examination form fee": (100, 100, 100, 100),
    "Sports fee": (20, 20, 100, 20),
    "Student union fee": (15, 15, 100, 15),
    "Student welfare fee": (15, 15, 150, 15),
    "Sports development fund": (50, 100, 150, 100),
    "Campus development fund": (150, 925, 4000, 925),
    "Campus maintenance fund": (100, 925, 4000, 925),
}

# Table B -- charged once, at admission, and not refundable.
ONE_TIME = {
    "Campus operation and infrastructure development": (6095, 122504, 270735, 122505),
    "TU registration fee": (500, 500, 2000, 500),
    "ID card fee": (200, 200, 200, 200),
    "Student health insurance": (500, 500, 500, 500),
}

# Table C -- धरौती. Charged once, at admission, and returned at the end of study less
# any outstanding dues. This is the only money a student gets back, and the assistant
# invented a refund policy when asked, so the block says so in as many words.
DEPOSITS = {
    "Library deposit": (1200, 5000, 5000, 5000),
    "Laboratory deposit": (500, 10000, 10000, 10000),
    "Campus deposit": (1700, 25000, 100000, 25000),
}

# Charged outside tables A, B and C by the campus notice's final table.
INTERNET_PER_SEMESTER = 600
ENGINEERING_COUNCIL = 1000

# The figures are the notice's own, so a fee answer cites the notice a student can open
# -- the same reasoning as results.RESULT_SOURCE. Title, url and file are copied from
# that document's front matter so this citation is indistinguishable from a retrieved one.
FEE_SOURCE = {
    "title": (
        "Pulchowk Campus BE/BArch Admission Notice 2083/084 "
        "\u2014 Schedule, Priority Rules and Fees"
    ),
    "year": "2083",
    "url": "https://pcampus.edu.np/2026/08/12/be-barch-admission-2083-detail-notice/",
    "file": "13_Pulchowk_BE_Admission_Detail_Notice_2083_English.md",
    "sections": ["Fee table A \u2014 Regular fees, per semester"],
}

# The totals as the notice prints them, used only to check the sums above.
PUBLISHED = {
    "per_semester": (6974, 52766, 147167, 66822),
    "one_time": (7295, 123704, 273435, 123705),
    "deposits": (3400, 40000, 115000, 40000),
    "at_admission_tables": (17669, 216470, 535602, 230527),
    "at_admission_total": (19269, 218070, 537202, 232127),
}


def _column(table: dict[str, tuple[int, ...]], index: int) -> int:
    return sum(row[index] for row in table.values())


def verify() -> list[str]:
    """Every published total, re-derived from the line items. Empty means all agree."""
    problems = []
    for index, name in enumerate(CATEGORIES):
        sums = {
            "per_semester": _column(PER_SEMESTER, index),
            "one_time": _column(ONE_TIME, index),
            "deposits": _column(DEPOSITS, index),
        }
        sums["at_admission_tables"] = sum(sums.values())
        sums["at_admission_total"] = (
            sums["at_admission_tables"] + INTERNET_PER_SEMESTER + ENGINEERING_COUNCIL
        )
        for key, computed in sums.items():
            printed = PUBLISHED[key][index]
            if computed != printed:
                problems.append(
                    f"{name} {key}: computed {computed}, notice says {printed}"
                )
    return problems


def totals(category: str) -> dict[str, int]:
    """Every figure a fee question can want, for one category."""
    index = CATEGORIES.index(category)
    per_semester = _column(PER_SEMESTER, index)
    one_time = _column(ONE_TIME, index)
    deposits = _column(DEPOSITS, index)
    tables_total = per_semester * SEMESTERS + one_time + deposits
    extras = INTERNET_PER_SEMESTER * SEMESTERS + ENGINEERING_COUNCIL
    return {
        "per_semester": per_semester,
        "one_time": one_time,
        "deposits": deposits,
        "at_admission_tables": per_semester + one_time + deposits,
        "at_admission_total": per_semester
        + one_time
        + deposits
        + INTERNET_PER_SEMESTER
        + ENGINEERING_COUNCIL,
        "semesters_total": per_semester * SEMESTERS,
        "degree_tables": tables_total,
        "internet_total": INTERNET_PER_SEMESTER * SEMESTERS,
        "degree_total": tables_total + extras,
        "degree_net": tables_total + extras - deposits,
        "later_semester": per_semester + INTERNET_PER_SEMESTER,
        "barch_extra": (per_semester + INTERNET_PER_SEMESTER)
        * (BARCH_SEMESTERS - SEMESTERS),
    }


def _money(amount: int) -> str:
    return f"NPR {amount:,}"


def _rows(category: str) -> list[tuple[str, int]]:
    """One category's figures, in the order a student meets them.

    Deliberately without arithmetic written out. An earlier version showed its working --
    "8 x 6,974 + 7,295 + 3,400 = 66,487" -- and the model copied the habit rather than
    the result, printing sums that were wrong around a figure that was right.

    Order and labels carry more weight here than the instructions above the table, and
    almost every wrong answer in the fee suite was one of the two rather than a reasoning
    failure:

    - The totals come first, because the model answers with the first plausible row it
      meets. Below the components, "the sponsored fee at admission" was answered with a
      component subtotal.
    - "at admission" appears on the TOTAL line and nowhere else. While the one-time
      charges read "one-time fees at admission" they took that question instead.
    - The three individual deposits are not rows at all. As rows they outcompeted their
      own total, and "the deposit for a full fee student" came back as the campus deposit
      alone; they are spelled out in prose under the table instead, where they still
      answer a question naming one of them without standing in for the total.
    - The per-semester items are listed even though they are also in the retrieved
      documents. Once the worked totals were in the prompt they crowded those documents
      out, and "the tuition fee per semester" came back as the whole semester's total.
    """
    index = CATEGORIES.index(category)
    t = totals(category)
    return [
        # The two totals first. A 7B model reads a table top-down and answers with the
        # first plausible row, which is how "the sponsored fee at admission" kept coming
        # back as a component subtotal that happens to sit above the total.
        ("TOTAL due on admission day", t["at_admission_total"]),
        (f"TOTAL for the whole {SEMESTERS}-semester degree", t["degree_total"]),
        ("    the same, once the deposits come back", t["degree_net"]),
        ("One semester of fees, all of table A together", t["per_semester"]),
        *((f"    {name.lower()}", row[index]) for name, row in PER_SEMESTER.items()),
        ("Internet, charged every semester", INTERNET_PER_SEMESTER),
        ("Every semester after the first", t["later_semester"]),
        ("Campus and registration charges, paid once", t["one_time"]),
        *((f"    {name.lower()}", row[index]) for name, row in ONE_TIME.items()),
        ("Engineering Council, paid once", ENGINEERING_COUNCIL),
        (
            "Deposits / \u0927\u0930\u094c\u091f\u0940, paid once, refundable",
            t["deposits"],
        ),
    ]


def format_table(categories: list[str]) -> str:
    """The figures as one table, a column per category.

    Usually one column. Four columns was tried, on the reasoning that reading off a
    number would then mean reading off a heading -- but tracking a column across fifty
    characters of whitespace is exactly what a 7B model cannot do, and it got worse:
    "how much is the library deposit" came back as the Full Fee figure labelled Regular,
    and a foreign student's degree total came back as a number in no table at all. So
    `fee_context` narrows to the category the student named, and to Regular when they
    named none, and the layout only has to carry one column of numbers.
    """
    labels = [label for label, _ in _rows(categories[0])]
    columns = [[amount for _, amount in _rows(name)] for name in categories]
    label_width = max(len(label) for label in labels)
    widths = [
        max(len(name), max(len(f"{a:,}") for a in column))
        for name, column in zip(categories, columns)
    ]

    header = "  ".join(f"{name:>{width}}" for name, width in zip(categories, widths))
    lines = [f"{'':<{label_width}}  {header}"]
    for row, label in enumerate(labels):
        cells = "  ".join(
            f"{columns[col][row]:>{width},}" if columns[col][row] >= 0 else " " * width
            for col, width in enumerate(widths)
        )
        lines.append(f"{label:<{label_width}}  {cells}")
    for name in categories:
        column = CATEGORIES.index(name)
        items = ", ".join(
            f"{item.lower()} {_money(row[column])}" for item, row in DEPOSITS.items()
        )
        lines.append(
            f"The {_money(totals(name)['deposits'])} of {name} deposits is "
            f"{items} added together."
        )
    nepali = ", ".join(f"{name} = {CATEGORY_NEPALI[name]}" for name in categories)
    lines.append(f"({nepali}. All amounts NPR.)")
    return "\n".join(lines)


# A question about money, in the words students use for it.
# Devanagari terms sit outside the \b(...)\b group, never inside it. A Devanagari word
# usually ends in a combining vowel sign -- the ी of धरौती, the ि of कति, the ा of भर्ना --
# and Python's re does not count a combining mark as a word character, so the closing \b
# has a non-word character on both sides of it and can never match. Written as
# \b(...|धरौती|...)\b the term is not merely unreliable, it is unreachable: measured, the
# whole of "धरौती कति हो" matched nothing and the question was turned away as off topic.
# graph._OTHER_LANGUAGE already had this right; these two did not.
_FEE_INTENT = re.compile(
    r"\b(fee|fees|cost|costs|costly|price|pay|paid|payable|payment|charge|charges|"
    r"expensive|afford|tuition|dharauti|deposit|deposits|refund|refundable|"
    r"how\s+much|refunded|returned|get\s+(?:it\s+)?back|money|budget|"
    r"rupees|rs\.?|npr)\b"
    r"|शुल्क|धरौती|कति|पैसा|रकम",
    re.IGNORECASE,
)

# The entrance examination fee and the admission application form fee are different
# money, answered by the payment notices. Those questions were already answered
# correctly, so this block stands down rather than crowding their prompt.
_OTHER_MONEY = re.compile(
    r"\b(entrance\s+(?:exam(?:ination)?\s+)?(?:fee|form)|exam\s+fee|"
    r"application\s+form|form\s+fee|per\s+subject|khalti|esewa|connectips|"
    r"bank\s?smart|voucher|siddhartha)\b",
    re.IGNORECASE,
)

# What the fee tables are actually about.
_ADMISSION_SUBJECT = re.compile(
    r"\b(admission|admitted|admit|enrol|enroll|enrolment|enrollment|semester|semesters|"
    r"degree|programme|program|course|study|studying|studies|year|years|campus|college|"
    r"pulchowk|be\b|b\.e\.|barch|b\.arch|regular|full[\s-]?fee|fulfee|foreign|sponsored|"
    r"quota|total|overall|altogether|whole|entire|lifetime|deposit|dharauti|"
    r"refund|refundable|refunds|returned|get\s+(?:it\s+|them\s+|that\s+)?back|"
    r"tuition|library|laboratory|lab\b|hostel|insurance|id\s*card|identity\s*card|"
    r"registration|union|welfare|sports|maintenance|infrastructure)\b"
    r"|भर्ना|सेमेस्टर|क्याम्पस|पुल्चोक|कलेज|फिर्ता|धरौती|शुल्क",
    re.IGNORECASE,
)

_CATEGORY_PATTERNS = (
    ("Full Fee", r"\bfull[\s-]?fee|fulfee|पूर्णशुल्कीय\b"),
    ("Foreign Student", r"\bforeign|international|विदेशी\b"),
    ("Sponsored", r"\bsponsor(?:ed|ship)?|प्रायोजित\b"),
    ("Regular", r"\bregular|normal|नियमित\b"),
)


def find_categories(text: str) -> list[str]:
    """The fee categories the question names, in published column order."""
    named = {
        name
        for name, pattern in _CATEGORY_PATTERNS
        if re.search(pattern, text, re.IGNORECASE)
    }
    return [name for name in CATEGORIES if name in named]


def is_fee_question(text: str) -> bool:
    """Whether the question is about what it costs to study here."""
    if _OTHER_MONEY.search(text):
        return False
    if not _FEE_INTENT.search(text):
        return False
    return bool(_ADMISSION_SUBJECT.search(text) or find_categories(text))


def fee_context(text: str) -> str:
    """Worked fee totals for the question, or "" if it is not about fees.

    Every figure is stated. Nothing is left for the model to add up, and the two things
    it invented when it had to reason -- a discount for Regular students, and a refund
    policy -- are contradicted here in as many words.
    """
    if not is_fee_question(text):
        return ""
    asked = find_categories(text)
    # Most students are Regular, and the alternative -- printing all four and leaving the
    # model to choose -- is how it came to quote a Full Fee deposit to a Regular student.
    # So one category is quoted and the answer says which, rather than four being offered
    # and the wrong one picked silently.
    unstated = not asked
    if unstated:
        asked = ["Regular"]
    caveat = (
        "\n\nThe student has not said which category they are in, so the table above is "
        "the Regular (\u0928\u093f\u092f\u092e\u093f\u0924) rate -- the one most students pay. Say that the "
        "figure you are quoting is the Regular rate, and that Full Fee, Foreign Student "
        "and Sponsored students pay different amounts you can look up if they say which "
        "they are."
        if unstated
        else ""
    )
    blocks = format_table(asked) + caveat
    return f"""AUTHORITATIVE FEE FIGURES -- Pulchowk Campus BE/BArch admission and study
fees, admission year 2083. Worked out from the notice's own tables; these override any
fee table in the reference documents above.

Read the figure off the line that answers the question and write it into a sentence of
your own. Never paste a row of the table into the answer, and never give a bare number.
Never add two lines together, never multiply anything, never show a calculation: every
total a student can ask for is already a line below.

- Asked simply what "the fee", "the cost", or "the total" is -- with nothing to say
  whether they mean what they owe now or what the degree comes to -- give both the
  admission-day figure and the whole-degree figure, and say which is which. Both matter
  to a student deciding whether they can start.
- Asked specifically what the degree costs, lead with "TOTAL for the whole degree". The
  after-the-deposits-come-back figure is a second sentence, never the headline.
- Always name the category the figure belongs to. If the table below has more than one
  column, give the figure from every column, each labelled with its heading.

{blocks}

How to read these:
- The admission-day amount is the first semester plus every one-time charge. It is part
  of the degree total, not something owed on top of it.
- Only the table C deposits come back, and only at the end of study, less any
  outstanding dues. There is no refund for withdrawing and no hardship refund -- the
  notices set no such policy, so do not describe one.
- Dharauti (धरौटी) means the table C deposits and nothing else -- not a hostel or
  dormitory charge. Asked for "the dharauti" without naming one of the three, the answer
  is the table C total, not the campus deposit. And the library and laboratory deposits
  are not the per-semester library fee and laboratory fee, which are far smaller and
  never come back.
- The categories are separate rates for different students, not discounts off one
  another. A Regular student is not paying a percentage off the Full Fee rate. The only
  stated relationship is that Sponsored tuition is 30 percent above Full Fee tuition.
- Only if the student says they are asking about BArch: it runs {BARCH_SEMESTERS}
  semesters rather than {SEMESTERS}, so its degree total is
  higher by two more semesters at the rate above, plus NPR 500 for the Architecture
  aptitude test. Never fold this into a figure the student did not ask for.
- The TU registration fee applies only to students not already registered with TU, and
  is NPR 1,000 rather than NPR 500 for someone who passed their qualifying exam abroad.
- Hostel charges are not in these tables; they follow the campus's own rules.
- These are not the entrance examination fee or the admission application form fee,
  which are separate and covered by the payment notices."""
