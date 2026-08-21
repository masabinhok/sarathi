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


def find_ranks(text: str) -> list[int]:
    """Pull merit ranks out of a question ("rank 13", "13th rank", "who topped")."""
    found: list[int] = []
    for match in _RANK_RE.finditer(text):
        num = match.group("num") or match.group("num2")
        if num and (rank := int(num)) not in found:
            found.append(rank)
    if _TOPPER_RE.search(text) and 1 not in found:
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


def lookup_context(text: str, limit: int = 3) -> str:
    """Context for every form number and merit rank in the question, or "" if none."""
    blocks = [format_lookup(n) for n in find_form_numbers(text)[:limit]]
    blocks += [format_rank_lookup(r) for r in find_ranks(text)[:limit]]
    return "\n\n".join(blocks)
