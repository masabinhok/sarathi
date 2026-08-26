"""Build docs/data/cutoffs.csv from the published 2079-2082 first-list cutoffs.

Run when a new admission year publishes, not as part of the app:

    uv run python notes/scrape_cutoffs.py

Lives in notes/ rather than src/ because docs/ is the RAG corpus and this is build
tooling, and because nothing at request time should depend on somebody else's website
being up. The app reads only the CSV.

Provenance. The figures are collected by ioe-entrance.bibeksubedi0001.com.np, which states
that each is recalculated from the campus admission list it links to, and whose robots.txt
allows crawling. Those linked admission lists are what goes in `source_url`, not the site
itself, so a citation points a student at the primary document the way every other module
in this app does. Where a year's list is not linked, source_url is left empty rather than
filled with the aggregator's own page -- an empty cell is a known gap, a wrong citation is
a student sent to the wrong document.

Scope, and it is narrower than it looks: open/general category only, first list only, four
campuses. Chitwan is not covered at all. cutoffs.py states every one of those limits in
the block it builds, because a student reading a rank against the wrong category is
exactly the mistake this data makes possible.
"""

import csv
import re
import sys
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

BASE = "https://ioe-entrance.bibeksubedi0001.com.np/ioe-cutoff-rank"
OUT = Path(__file__).resolve().parents[1] / "docs" / "data" / "cutoffs.csv"

# Campus names as seats.py spells them, so a programme lookup joins across the two.
PAGES = {
    "Pulchowk": "pulchowk-campus",
    "Thapathali": "thapathali-campus",
    "Pashchimanchal": "wrc-pokhara",
    "Purwanchal": "erc-dharan",
}

# The site writes programmes out in full; seats.py uses the booklet's short names.
# Anything unmapped is reported rather than dropped silently -- a programme appearing
# under a new spelling is a thing to look at, not to lose.
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
RANK = re.compile(r"([\d,]+)")


def rank(cell: str) -> int | None:
    """ "# 1,270" -> 1270. A dash, a blank or an em dash means the programme did not run."""
    match = RANK.search(cell.replace("#", ""))
    return int(match.group(1).replace(",", "")) if match else None


def sources(soup: BeautifulSoup) -> dict[str, str]:
    """year -> the official admission list that year's figures were derived from."""
    found: dict[str, str] = {}
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        text = anchor.get_text(" ", strip=True)
        if not href.startswith("http") or "bibeksubedi" in href:
            continue
        if "admission" not in f"{href} {text}".lower():
            continue
        if match := YEAR.search(f"{text} {href}"):
            found.setdefault(match.group(1), href)
    return found


def scrape(campus: str, path: str) -> tuple[list[dict], list[str]]:
    html = httpx.get(
        f"{BASE}/{path}",
        timeout=30,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (compatible; IOE-Admission-Assistant/1.0)"},
    ).text
    soup = BeautifulSoup(html, "html.parser")
    links = sources(soup)
    rows: list[dict] = []
    unknown: list[str] = []

    for table in soup.find_all("table"):
        heading = table.find_previous(["h2", "h3"])
        match = YEAR.search(heading.get_text(" ", strip=True) if heading else "")
        if not match:
            continue
        year = match.group(1)
        for tr in table.find_all("tr")[1:]:
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["th", "td"])]
            if len(cells) < 3:
                continue
            name = PROGRAMMES.get(cells[0].lower().strip())
            if name is None:
                unknown.append(cells[0])
                continue
            for category, cell in (("Regular", cells[1]), ("Full-fee", cells[2])):
                if (value := rank(cell)) is None:
                    continue
                rows.append(
                    {
                        "year": year,
                        "campus": campus,
                        "programme": name,
                        "category": category,
                        "list": "first",
                        "lowest_rank_admitted": value,
                        "source_url": links.get(year, ""),
                    }
                )
    return rows, unknown


def main() -> int:
    all_rows: list[dict] = []
    problems: list[str] = []
    for campus, path in PAGES.items():
        rows, unknown = scrape(campus, path)
        cited = sum(1 for r in rows if r["source_url"])
        print(f"{campus:16} {len(rows):>4} cutoffs, {cited:>4} with an official source")
        problems += [f"{campus}: unmapped programme {name!r}" for name in set(unknown)]
        all_rows += rows

    all_rows.sort(
        key=lambda r: (-int(r["year"]), r["campus"], r["programme"], r["category"])
    )
    with OUT.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "year",
                "campus",
                "programme",
                "category",
                "list",
                "lowest_rank_admitted",
                "source_url",
            ],
        )
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"\n{len(all_rows)} rows -> {OUT}")
    for problem in problems:
        print(f"  ! {problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
