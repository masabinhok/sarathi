"""Extract dated obligations from the indexed documents into a deadline list.

Documents state their dates in Bikram Sambat and rarely label them as deadlines, so
dates are picked up with their surrounding sentence and kept only when that sentence
reads like an obligation. This is a reading aid for students, not a source of truth:
every entry links back to the document it came from.
"""

import datetime
import re
from dataclasses import asdict, dataclass

import nepali_datetime

from ioe.dates import BS_MONTHS, today_in_nepal
from ioe.rag import DOCS_DIR, SKIP_DIRS, _split_frontmatter

_BS_DATE_RE = re.compile(r"\b(20[6-9]\d)/(\d{1,2})/(\d{1,2})\b")

# A date only becomes a deadline when its sentence asks the student to do something by it.
_OBLIGATION_RE = re.compile(
    r"\b(deadline|last date|apply|application|submit|submission|register|registration|"
    r"pay|payment|fee|admission|exam|examination|entrance|correction|publish|published|"
    r"between|from|until|till|before|within|schedule)\b",
    re.IGNORECASE,
)
# Sentences about what a document *is* rather than what a student must do.
_NOISE_RE = re.compile(
    r"\b(notice date|source|translation type|letterhead|signed)\b", re.IGNORECASE
)

SNIPPET_CHARS = 220

# Snippets are lifted verbatim out of Markdown documents and shown as plain text, so the
# inline markup has to come off -- otherwise a student reads "**point 6**" on screen.
_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_EMPHASIS_RE = re.compile(r"(\*\*|__|\*|_|`)")
WINDOW_PAST_DAYS = 45
WINDOW_FUTURE_DAYS = 365


@dataclass
class Deadline:
    bs_date: str
    bs_label: str
    ad_date: str
    days: int
    status: str  # upcoming | today | passed
    snippet: str
    document: str
    url: str
    file: str


def _sentence_around(text: str, index: int) -> str:
    """The Markdown line holding the date.

    Sentence splitting on "." is useless here: the documents are dense with B.E./B.Arch.
    and 2083/04/26, so a period is rarely a sentence end. Lines are the reliable unit --
    in this corpus each bullet or paragraph is one line.
    """
    start = text.rfind("\n", 0, index) + 1
    end = text.find("\n", index)
    line = text[start:] if end == -1 else text[start:end]
    snippet = _LINK_RE.sub(r"\1", line)
    snippet = _EMPHASIS_RE.sub("", snippet)
    snippet = re.sub(r"\s+", " ", snippet).strip(" #->|")
    if len(snippet) > SNIPPET_CHARS:
        snippet = snippet[:SNIPPET_CHARS].rsplit(" ", 1)[0] + "..."
    return snippet


def _bs_label(year: int, month: int, day: int) -> str:
    name = BS_MONTHS[month - 1] if 1 <= month <= 12 else str(month)
    return f"{year} {name} {day}"


def collect(today: datetime.date | None = None) -> list[Deadline]:
    """Scan the translated documents and return dated obligations, soonest first."""
    today = today or today_in_nepal()
    out: list[Deadline] = []
    seen: set[tuple[str, str]] = set()

    for path in sorted(DOCS_DIR.rglob("*.md")):
        if path.name.startswith("_") or path.name == "README.md":
            continue
        if any(part in SKIP_DIRS for part in path.relative_to(DOCS_DIR).parts[:-1]):
            continue

        meta, body = _split_frontmatter(path.read_text(encoding="utf-8"))
        title = str(meta.get("title") or path.stem)
        url = str(meta.get("url") or "")

        for match in _BS_DATE_RE.finditer(body):
            year, month, day = (int(g) for g in match.groups())
            try:
                ad = nepali_datetime.date(year, month, day).to_datetime_date()
            except (ValueError, IndexError):
                continue

            days = (ad - today).days
            if not -WINDOW_PAST_DAYS <= days <= WINDOW_FUTURE_DAYS:
                continue

            snippet = _sentence_around(body, match.start())
            if not _OBLIGATION_RE.search(snippet) or _NOISE_RE.search(snippet):
                continue

            bs_date = f"{year}/{month:02d}/{day:02d}"
            key = (path.name, bs_date)
            if key in seen:
                continue
            seen.add(key)

            out.append(
                Deadline(
                    bs_date=bs_date,
                    bs_label=_bs_label(year, month, day),
                    ad_date=ad.isoformat(),
                    days=days,
                    status="today"
                    if days == 0
                    else ("upcoming" if days > 0 else "passed"),
                    snippet=snippet,
                    document=title,
                    url=url,
                    file=path.name,
                )
            )

    out.sort(key=lambda d: d.ad_date)
    return out


def as_payload(today: datetime.date | None = None) -> dict:
    today = today or today_in_nepal()
    items = collect(today)
    return {
        "today_nepal": today.isoformat(),
        "upcoming": [asdict(d) for d in items if d.days >= 0],
        "passed": [asdict(d) for d in reversed(items) if d.days < 0],
    }
