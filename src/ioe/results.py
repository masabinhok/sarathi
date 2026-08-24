"""Exact lookup over the published entrance pass list.

The pass list is a 7,179-row table keyed by form number. Embedding it would be useless:
similarity search over names and roll numbers returns near-noise, and a student asking
"did form 2083-4567 pass?" wants an exact record, not the nearest neighbour. So it stays
out of the vector index and is answered by direct lookup instead.
"""

import csv
import re
from functools import lru_cache
from pathlib import Path

RESULTS_CSV = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "data"
    / "03_BE_BArch_Entrance_Result_2083_pass_list.csv"
)
RESULT_YEAR = "2083"

# The CSV is a transcription of the published result notice, so a lookup cites the notice
# a student can actually open -- not a file that only exists inside this repository.
RESULT_SOURCE = {
    "title": "BE/BArch Entrance Examination Result 2083 - published pass list",
    "year": RESULT_YEAR,
    "url": "https://entrance.ioe.edu.np/Notice/Detail/5131",
    "file": RESULTS_CSV.name,
    "sections": [],
}

# "2083-4567" written out, or a bare number qualified by form/application/symbol wording.
_FORM_RE = re.compile(r"\b(20\d{2})[-\s]?(\d{1,6})\b")
_RANK_RE = re.compile(
    r"\brank(?:ed|ing)?\s*(?:no\.?|number|#)?\s*(?:is|was|=|:)?\s*(?P<num>\d{1,5})\b"
    r"|\b(?P<num2>\d{1,5})\s*(?:st|nd|rd|th)\s*(?:merit\s*)?rank\b",
    re.IGNORECASE,
)
_TOPPER_RE = re.compile(
    r"\b(topper|topped|top\s+scorer|first\s+rank|rank\s+one|number\s+one)\b",
    re.IGNORECASE,
)

_BARE_RE = re.compile(
    r"\b(?:form|application|admission|symbol|roll)\s*(?:no\.?|number|#)?"
    r"\s*(?:is|was|=|:)?\s*(\d{1,6})\b",
    re.IGNORECASE,
)


@lru_cache(maxsize=1)
def _rows() -> dict[str, dict[str, str]]:
    """Load the pass list keyed by form number. Missing file yields an empty table."""
    if not RESULTS_CSV.exists():
        return {}
    with RESULTS_CSV.open(encoding="utf-8", newline="") as fh:
        return {
            row["form_no"].strip(): row
            for row in csv.DictReader(fh)
            if row.get("form_no")
        }


@lru_cache(maxsize=1)
def _by_rank() -> dict[int, dict[str, str]]:
    """Load the pass list keyed by merit rank. Rank is unique across the list."""
    out: dict[int, dict[str, str]] = {}
    for row in _rows().values():
        try:
            out[int(row["rank"])] = row
        except (KeyError, ValueError):
            continue
    return out


def find_ranks(text: str, include_topper: bool = True) -> list[int]:
    """Pull merit ranks out of a question ("rank 13", "13th rank", "who topped").

    `include_topper` exists for one caller: lookup_context turns it off when the
    question also names a district, because "who topped from Mustang" is a
    district-scoped question the topper heuristic can't answer -- rank 1 overall is a
    different person -- and stating it alongside the district's own top candidate
    would read as though the two were the same. An explicit numeral ("rank 1") is
    unambiguous regardless and is never affected by this.
    """
    found: list[int] = []
    for match in _RANK_RE.finditer(text):
        num = match.group("num") or match.group("num2")
        if num and (rank := int(num)) not in found:
            found.append(rank)
    if include_topper and _TOPPER_RE.search(text) and 1 not in found:
        found.insert(0, 1)
    return found


def lookup_rank(rank: int) -> dict[str, str] | None:
    return _by_rank().get(rank)


def format_rank_lookup(rank: int) -> str:
    """Render a rank lookup as terse fields, matching format_lookup's contract."""
    row = lookup_rank(rank)
    if row is None:
        highest = max(_by_rank(), default=0)
        return (
            f"[Pass list lookup: merit rank {rank}]\n"
            f"Status: no candidate holds this rank on the published {RESULT_YEAR} pass list\n"
            f"Note: ranks on this list run from 1 to {highest}."
        )
    return (
        f"[Pass list lookup: merit rank {rank}]\n"
        f"Status: on the published {RESULT_YEAR} pass list\n"
        f"Merit rank: {row.get('rank', '')}\n"
        f"Name: {row.get('name', '')}\n"
        f"District: {row.get('district', '')}\n"
        f"Form number: {row.get('form_no', '')}"
    )


def find_form_numbers(text: str) -> list[str]:
    """Pull candidate form numbers out of a question, most explicit form first."""
    found: list[str] = []
    # Blank out full matches first, so "form 2083-4" cannot also read as a bare "2083".
    remainder = text
    for match in _FORM_RE.finditer(text):
        year, num = match.groups()
        candidate = f"{year}-{int(num)}"
        if candidate not in found:
            found.append(candidate)
        remainder = remainder.replace(match.group(0), " ")
    for num in _BARE_RE.findall(remainder):
        candidate = f"{RESULT_YEAR}-{int(num)}"
        if candidate not in found:
            found.append(candidate)
    return found


def lookup(form_no: str) -> dict[str, str] | None:
    return _rows().get(form_no)


def format_lookup(form_no: str) -> str:
    """Render one lookup as terse fields.

    Deliberately not written as prose: a fluent paragraph here gets copied to the student
    verbatim, guidance for the model and all. Fields force the model to write the answer.
    """
    row = lookup(form_no)
    if row is None:
        return (
            f"[Pass list lookup: form number {form_no}]\n"
            f"Status: not on the published {RESULT_YEAR} pass list\n"
            "Caveat: the list holds passing candidates only, so absence may equally mean "
            "the number was mistyped or never sat the exam. This lookup cannot tell those "
            "cases apart."
        )

    fields = [
        f"Status: on the published {RESULT_YEAR} pass list",
        f"Form number: {row.get('form_no', '')}",
        f"Merit rank: {row.get('rank', '')}",
        f"Name: {row.get('name', '')}",
        f"District: {row.get('district', '')}",
        f"Alphabetical serial number: {row.get('sno', '')}",
    ]
    if row.get("remarks", "").strip():
        fields.append(f"Remarks: {row['remarks'].strip()}")

    return f"[Pass list lookup: form number {form_no}]\n" + "\n".join(fields)


# ── Name and district lookup ────────────────────────────────────────────────────
# A form number or a rank is a key into an exact index -- one question, one answer, no
# room to get it wrong. A name is not: "Sabin Shrestha" isn't on this list, "Shrestha"
# alone matches 356 rows, and Nepali names run two to four words with no reliable split
# into "first" and "last". So a name match is built the opposite way round from a form
# number -- not "does this look like a name", but "is this word or phrase one that a
# real, published candidate actually has". The vocabulary comes from the CSV itself, the
# same discipline _FORM_RE and _RANK_RE already use, just applied to text instead of
# digits. A stray word never matches unless someone on the list is actually named it.

# Below this length a token is too likely to be an ordinary word that happens to also be
# someone's name -- "Raj", "Dev", "Bal" are all real first or last names on this list and
# all common enough outside it to false-trigger constantly.
NAME_TOKEN_MIN_LEN = 4

# A real surname on this list (11 candidates), and also the single word this app's own
# language handling (see graph.py) makes students type constantly and unrelatedly --
# "reply in Nepali", "the notice is in Nepali". Excluding it loses those 11 candidates
# from single-word search; they are still reachable by full name, form number, or rank.
_NAME_TOKEN_DENYLIST = frozenset({"nepali"})

# How many matching rows are still worth listing individually before the honest answer
# becomes "too many" rather than a wall of names the model would have to summarise.
NAME_LIST_CAP = 8
# How many candidates a district search names, ranked best first. Kathmandu alone holds
# 692 -- nowhere near listable -- so this is always a "best of" cut, stated as one.
DISTRICT_TOP_N = 5

# Gates a *bare* district mention, with no name alongside it, before it counts as a pass
# list question. Nepal's districts are proper nouns and rarely collide with ordinary
# words, but this app talks about quotas and campuses by geography constantly -- "does
# someone from Kathmandu need extra documents" is not a request for the pass list, and
# without this gate it would get one anyway.
_RESULT_INTENT_RE = re.compile(
    r"\b(pass(ed)?|result|results|rank(ed|ing)?|topper|topped|qualif\w*|merit|"
    r"score|scored|candidate|candidates|list)\b",
    re.IGNORECASE,
)

_WORD_RE = re.compile(r"[a-zA-Z]+")


@lru_cache(maxsize=1)
def _by_full_name() -> dict[str, list[dict[str, str]]]:
    """Every published name, verbatim and lowercased, to every row that carries it."""
    out: dict[str, list[dict[str, str]]] = {}
    for row in _rows().values():
        key = row["name"].strip().lower()
        if key:
            out.setdefault(key, []).append(row)
    return out


@lru_cache(maxsize=1)
def _by_name_token() -> dict[str, list[dict[str, str]]]:
    """Every individual word of every published name -- not just the first or the
    last, Nepali names don't split reliably that way -- to every row it appears in."""
    out: dict[str, list[dict[str, str]]] = {}
    for row in _rows().values():
        for tok in row["name"].strip().lower().split():
            if len(tok) >= NAME_TOKEN_MIN_LEN and tok not in _NAME_TOKEN_DENYLIST:
                out.setdefault(tok, []).append(row)
    return out


@lru_cache(maxsize=1)
def _by_district() -> dict[str, list[dict[str, str]]]:
    out: dict[str, list[dict[str, str]]] = {}
    for row in _rows().values():
        district = row["district"].strip()
        if district:
            out.setdefault(district.lower(), []).append(row)
    return out


@lru_cache(maxsize=1)
def _district_names() -> list[str]:
    """Published district names, longest first, so "Nawalparasi west" is matched
    whole rather than being read as the different district "Nawalparasi"."""
    found = {
        row["district"].strip() for row in _rows().values() if row["district"].strip()
    }
    return sorted(found, key=len, reverse=True)


def find_name_matches(text: str) -> list[tuple[str, str]]:
    """Names mentioned in the question that are actually on the pass list.

    Returns ("full", name) or ("word", token) pairs. A full name is matched first, up
    to four words long since some published names run that long, and the words it
    claims are removed from consideration before single-word matching runs -- so
    "Basanta Raj Dahal" is read as one person, not a full-name match plus a stray hit
    on the common surname "Raj". What's left of "first name or last name alone" isn't
    which position the word holds in the candidate's name (Nepali names don't split
    into those roles reliably); it's just: this word, on its own, is one a real
    candidate has.
    """
    words = _WORD_RE.findall(text.lower())
    if not words:
        return []

    consumed = [False] * len(words)
    full_names = _by_full_name()
    matches: list[tuple[str, str]] = []

    for span in (4, 3, 2):
        for i in range(len(words) - span + 1):
            if any(consumed[i : i + span]):
                continue
            phrase = " ".join(words[i : i + span])
            if phrase in full_names:
                matches.append(("full", phrase))
                for j in range(i, i + span):
                    consumed[j] = True

    tokens = _by_name_token()
    seen_tokens = {key for kind, key in matches if kind == "word"}
    for i, word in enumerate(words):
        if consumed[i] or word in seen_tokens:
            continue
        if word in tokens:
            matches.append(("word", word))
            seen_tokens.add(word)

    return matches


def find_district(text: str) -> str | None:
    """The published district named in the question, if any."""
    lowered = text.lower()
    for district in _district_names():
        if re.search(rf"\b{re.escape(district.lower())}\b", lowered):
            return district
    return None


def _intersect_word_matches(tokens: list[str]) -> list[dict[str, str]]:
    """Rows carrying *every* one of these name words, not just any one of them.

    "Is Sabin Shrestha on the list" doesn't match a published full name -- nobody is
    named exactly that -- so it falls to word matching, which finds 15 Sabins and 357
    Shresthas separately. Reported as two blocks, that's noise: the actual question is
    whether one candidate has both words, and the honest answer to that is usually
    "no", stated once, rather than two unrelated "too many to list"s that leave the
    model to guess whether they overlap.
    """
    token_rows = _by_name_token()
    keyed = [{row["form_no"]: row for row in token_rows.get(t, [])} for t in tokens]
    if not keyed:
        return []
    common = set(keyed[0])
    for group in keyed[1:]:
        common &= set(group)
    return [keyed[0][k] for k in common]


def format_name_lookup(kind: str, key: str, district: str | None = None) -> str:
    """Render a single full-name or single-word match. See _render_name_match for the
    shared formatting; this only resolves which rows that key refers to."""
    label = (
        f'name "{key.title()}"'
        if kind == "full"
        else f'name containing "{key.title()}"'
    )
    rows = (
        _by_full_name().get(key, [])
        if kind == "full"
        else _by_name_token().get(key, [])
    )
    return _render_name_match(label, rows, district)


def format_combined_name_lookup(tokens: list[str], district: str | None = None) -> str:
    """Render two or more name words asked about together, as the one candidate (or
    none) who has all of them -- not each word's unrelated matches separately."""
    label = "name containing " + " and ".join(f'"{t.title()}"' for t in tokens)
    return _render_name_match(label, _intersect_word_matches(tokens), district)


def _render_name_match(
    label: str, rows: list[dict[str, str]], district: str | None
) -> str:
    """Render a name match as terse fields -- one candidate, several, or none.

    The three failure shapes this is built to avoid are the same three the rest of
    this module exists to avoid: never state absence when the name matched a
    *different* district (that is not evidence the candidate never sat the exam, it
    is evidence the student may have the district wrong); never silently pick one
    candidate when several share the name; and never claim a capped list is the
    whole list.
    """
    narrowed = (
        [r for r in rows if r["district"].strip().lower() == district.lower()]
        if district
        else rows
    )

    if not narrowed:
        if district and rows:
            elsewhere = sorted({r["district"] for r in rows if r["district"].strip()})
            return (
                f"[Pass list lookup: {label}]\n"
                f"Status: on the published {RESULT_YEAR} pass list, but not from {district}\n"
                f"District(s) actually on record: {', '.join(elsewhere) or 'not stated'}\n"
                "Note: this may be a different candidate with the same name, or the "
                "student may have the district wrong -- do not assume which."
            )
        return (
            f"[Pass list lookup: {label}]\n"
            f"Status: no candidate matching this appears on the published {RESULT_YEAR} "
            "pass list\n"
            "Caveat: this checks the name exactly as published; a different spelling or "
            "transliteration would not match. Absence here does not confirm the candidate "
            "did not sit or pass the exam."
        )

    if len(narrowed) == 1:
        row = narrowed[0]
        return (
            f"[Pass list lookup: {label}]\n"
            f"Status: on the published {RESULT_YEAR} pass list\n"
            f"Name: {row['name']}\n"
            f"Merit rank: {row['rank']}\n"
            f"Form number: {row['form_no']}\n"
            f"District: {row['district'] or 'not stated'}"
        )

    if len(narrowed) > NAME_LIST_CAP:
        return (
            f"[Pass list lookup: {label}]\n"
            f"Status: {len(narrowed)} candidates match -- too many to list individually\n"
            "Note: ask the student for a form number, full name, or district to narrow "
            "this down. Do not guess or pick one."
        )

    listed = "\n".join(
        f"- {r['name']}, rank {r['rank']}, form {r['form_no']}, "
        f"district {r['district'] or 'not stated'}"
        for r in narrowed
    )
    return (
        f"[Pass list lookup: {label}]\n"
        f"Status: {len(narrowed)} candidates match\n"
        f"{listed}\n"
        "Note: more than one candidate matches -- do not pick one. Ask for a form "
        "number, full name, or district to identify which one."
    )


def format_district_lookup(district: str) -> str:
    """The best-ranked candidates from a district. Always a cut, never the roster --
    the largest district here holds 692 names, and the honest version of "who's from
    Kathmandu" is the top few plus a stated total, not a wall of rows the model would
    have to summarise back down anyway."""
    rows = _by_district().get(district.lower(), [])
    if not rows:
        return (
            f'[Pass list lookup: district "{district}"]\n'
            f"Status: no candidate from {district} appears on the published "
            f"{RESULT_YEAR} pass list"
        )

    ranked = sorted(
        rows, key=lambda r: int(r["rank"]) if r["rank"].isdigit() else 10**9
    )
    top = ranked[:DISTRICT_TOP_N]
    listed = "\n".join(
        f"- {r['name']}, rank {r['rank']}, form {r['form_no']}" for r in top
    )
    extra = len(ranked) - len(top)
    tail = f"\n({extra} more not shown, ranked lower)" if extra else ""
    return (
        f'[Pass list lookup: district "{district}"]\n'
        f"Status: {len(ranked)} candidates from {district} are on the published "
        f"{RESULT_YEAR} pass list\n"
        f"Best-ranked {len(top)} shown, lowest rank number first:\n{listed}{tail}\n"
        "Note: this is a ranked subset, not the full list -- do not imply these are "
        "the only candidates from this district."
    )


def lookup_context(text: str, limit: int = 3) -> str:
    """Context for every form number, merit rank, name, and district in the question,
    or "" if none. Name and district lookups are answered against the raw question --
    same as form number and rank, and for the same reason: a rewrite or a translation
    goes through the model, and a name that survives a paraphrase may not survive it
    verbatim."""
    district = find_district(text)
    blocks = [format_lookup(n) for n in find_form_numbers(text)[:limit]]
    # A district in play turns off the topper heuristic: "who topped from Mustang" is
    # answered by the district block below, and the global rank 1 is a different
    # person -- see find_ranks.
    blocks += [
        format_rank_lookup(r)
        for r in find_ranks(text, include_topper=district is None)[:limit]
    ]

    matches = find_name_matches(text)
    full_matches = [key for kind, key in matches if kind == "full"][:limit]
    word_matches = [key for kind, key in matches if kind == "word"]

    blocks += [format_name_lookup("full", key, district) for key in full_matches]
    if len(word_matches) >= 2:
        blocks.append(format_combined_name_lookup(word_matches, district))
    elif len(word_matches) == 1:
        blocks.append(format_name_lookup("word", word_matches[0], district))
    elif not full_matches and district and _RESULT_INTENT_RE.search(text):
        # No name to anchor it, so a bare district only counts as a pass list question
        # when the question also sounds like one -- otherwise "does Kathmandu need
        # extra documents" would get a list of 692 candidates nobody asked for.
        blocks.append(format_district_lookup(district))

    return "\n\n".join(blocks)
