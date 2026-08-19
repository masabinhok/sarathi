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

# "2083-4567" written out, or a bare number qualified by form/application/symbol wording.
_FORM_RE = re.compile(r"\b(20\d{2})[-\s]?(\d{1,6})\b")
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
    """Context for every form number mentioned in the question, or "" if none are."""
    numbers = find_form_numbers(text)[:limit]
    return "\n\n".join(format_lookup(n) for n in numbers) if numbers else ""
