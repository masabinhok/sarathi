"""Build docs/data/cutoffs.csv from the published 2079-2082 first-list cutoffs.

Run when a new admission year publishes, not as part of the app:

    uv run python notes/scrape_cutoffs.py

Lives in notes/ rather than src/ because docs/ is the RAG corpus and this is build
tooling, and because nothing at request time should depend on somebody else's site
being up. The app reads only the CSV.

Source: ioe-entrance.bibeksubedi0001.com.np/ioe-cutoff-rank, which states every figure was
recalculated from the campus-published first admission lists for 2079-2082 BS, links each
of those lists, and allows crawling. Those linked lists are what goes in `source_url` --
the primary document -- so a citation sends a student where every other module sends them.
Where a year's list is not linked the cell is left empty: an empty cell is a known gap, a
wrong citation is a student sent to the wrong document.

WHAT THE NUMBER IS. The site's own note: "A lower numerical entrance rank is better."
So the figure is the *last* rank admitted -- the largest number that still got a place,
the point where the list closed. A rank is inside it when the student's number is smaller.
The column is `closing_rank` for that reason; an earlier version called it
`lowest_rank_admitted`, which literally reads as rank 1 and inverts the meaning.

The year comes from each table's own <caption>, not from the heading above it. The caption
is inside the table it describes, so it cannot drift if the page is reordered, and the two
are cross-checked on every run.

Scope, narrower than it looks: open/general category, first list only, four campuses.
Chitwan is not covered. cutoffs.py states every one of those limits in the block it
builds, because a student reading a rank against the wrong category is exactly the mistake
this data makes possible.
"""

import csv
import re
import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

BASE = "https://ioe-entrance.bibeksubedi0001.com.np/ioe-cutoff-rank"
OUT = Path(__file__).resolve().parents[1] / "docs" / "data" / "cutoffs.csv"
UA = "Mozilla/5.0 (compatible; IOE-Admission-Assistant/1.0)"

# Campus names as seats.py spells them, so a programme lookup joins across the two. The
# site titles two of them differently -- "WRC (Pashchimanchal Campus)", "ERC (Purwanchal
# Campus)" -- which is why the caption check below matches on a keyword, not the name.
PAGES = {
    "Pulchowk": ("pulchowk-campus", "pulchowk"),
    "Thapathali": ("thapathali-campus", "thapathali"),
    "Pashchimanchal": ("wrc-pokhara", "pashchimanchal"),
    "Purwanchal": ("erc-dharan", "purwanchal"),
}

# The site writes programmes out in full; seats.py uses the booklet's short names. Both
# ampersand and "and" spellings appear on the same site.
PROGRAMMES = {
    "civil engineering": "Civil",
    "architecture": "Architecture",
    "electrical engineering": "Electrical",
    "electronics, communication & information engineering": "Electronics, Communication and Information",
    "electronics, communication and information engineering": "Electronics, Communication and Information",
    "electronics communication & information engineering": "Electronics, Communication and Information",
    "mechanical engineering": "Mechanical",
    "computer engineering": "Computer",
    "aerospace engineering": "Aerospace",
    "chemical engineering": "Chemical",
    "agricultural engineering": "Agriculture",
    "agriculture engineering": "Agriculture",
    "industrial engineering": "Industrial",
    "geomatics engineering": "Geomatics",
    "automobile engineering": "Automobile",
}

YEAR = re.compile(r"\b(20\d\d)\b")
NUMBER = re.compile(r"([\d,]+)")
FIELDS = [
    "year",
    "campus",
    "programme",
    "category",
    "list",
    "closing_rank",
    "source_url",
]


def closing(cell: str) -> int | None:
    """ "# 1,270" -> 1270. A dash or a blank means the programme did not run that year."""
    match = NUMBER.search(cell.replace("#", ""))
    return int(match.group(1).replace(",", "")) if match else None


def sources(soup: BeautifulSoup) -> dict[str, str]:
    """year -> the official admission list that year's figures were recalculated from."""
    found: dict[str, str] = {}
    for anchor in soup.find_all("a", href=True):
        href, text = anchor["href"], anchor.get_text(" ", strip=True)
        if not href.startswith("http") or "bibeksubedi" in href:
            continue
        if "admission" not in f"{href} {text}".lower():
            continue
        if match := YEAR.search(f"{text} {href}"):
            found.setdefault(match.group(1), href)
    return found


def scrape(campus: str, path: str, keyword: str) -> tuple[list[dict], list[str]]:
    html = httpx.get(
        f"{BASE}/{path}", timeout=30, follow_redirects=True, headers={"User-Agent": UA}
    ).text
    soup = BeautifulSoup(html, "html.parser")
    links = sources(soup)
    rows: list[dict] = []
    notes: list[str] = []

    for table in soup.find_all("table"):
        caption = table.find("caption")
        if caption is None:
            notes.append(f"{campus}: a table has no caption and was skipped")
            continue
        label = caption.get_text(" ", strip=True)

        # The caption names its own campus and year. Both are checked, because a page that
        # quietly served another campus's table would otherwise be invisible.
        if keyword not in label.lower():
            notes.append(f"{campus}: caption names another campus -- {label!r}")
            continue
        match = YEAR.search(label)
        if not match:
            notes.append(f"{campus}: caption carries no year -- {label!r}")
            continue
        year = match.group(1)

        heading = table.find_previous("h2")
        found = YEAR.search(heading.get_text(" ", strip=True)) if heading else None
        if found and found.group(1) != year:
            notes.append(
                f"{campus} {year}: heading says {found.group(1)}, caption says {year}"
            )

        for tr in table.find_all("tr")[1:]:
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
            if len(cells) < 3:
                continue
            programme = PROGRAMMES.get(cells[0].lower().strip())
            if programme is None:
                notes.append(f"{campus} {year}: unmapped programme {cells[0]!r}")
                continue
            for category, cell in (("Regular", cells[1]), ("Full-fee", cells[2])):
                if (rank := closing(cell)) is None:
                    continue
                rows.append(
                    {
                        "year": year,
                        "campus": campus,
                        "programme": programme,
                        "category": category,
                        "list": "first",
                        "closing_rank": rank,
                        "source_url": links.get(year, ""),
                    }
                )
    return rows, notes


def main() -> int:
    everything: list[dict] = []
    notes: list[str] = []
    for campus, (path, keyword) in PAGES.items():
        rows, found = scrape(campus, path, keyword)
        years = sorted({row["year"] for row in rows})
        cited = sum(1 for row in rows if row["source_url"])
        print(
            f"{campus:16} {len(rows):>4} figures  years {','.join(years)}  {cited} cited"
        )
        notes += found
        everything += rows

    everything.sort(
        key=lambda row: (
            -int(row["year"]),
            row["campus"],
            row["programme"],
            row["category"],
        )
    )
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(everything)

    print(f"\n{len(everything)} rows -> {OUT}")
    for note in dict.fromkeys(notes):
        print(f"  ! {note}")
    return 1 if notes else 0


if __name__ == "__main__":
    sys.exit(main())
