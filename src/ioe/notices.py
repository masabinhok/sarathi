"""Scrape published notices from IOE, TU, and campus websites into a local cache.

These are other people's websites and their markup will change without warning, so each
parser is small, defensive, and independent: one site breaking or going down degrades that
source to an error entry and leaves the rest intact.

What is collected is the listing -- title, date, source, link. That listing is both shown
to students and indexed alongside the translated documents, so the assistant can say that
a notice exists and when it was published, even when the notice itself post-dates the
document set. Before that the assistant could not see this cache at all, and would tell a
student there was no recent notice while the app displayed one from the day before.
"""

import datetime
import json
import re
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from ioe.dates import ad_to_bs_labels, today_in_nepal

CACHE_PATH = Path(__file__).resolve().parents[2] / ".cache" / "notices.json"
USER_AGENT = "Mozilla/5.0 (compatible; IOE-Admission-Assistant/1.0)"
TIMEOUT = 20.0
PER_SOURCE_LIMIT = 12

# The admission portals publish under a per-year path or subdomain, so next year is a
# one-line change here rather than a hunt through SOURCES. Expect those sources to 404
# when the cycle turns over: that is the year moving on, not a parser breaking.
ADMISSION_YEAR = "2083"

# Notice pages are not fetched. Sampling one page from every source, each turned out to be
# a heading over a link to a scanned PDF -- the richest of them held 209 characters, most
# of it "Click Here" and "in pdf format" -- so the text worth indexing is the record
# itself: what was published, by whom, and when. Fetching the pages would have added a
# request per notice and put site chrome into the index to compete with the translated
# documents. Worth revisiting only if a source starts publishing notices as real HTML.

_MONTH_NAMES = (
    "january february march april may june july august september october "
    "november december"
)
_MONTHS = {m: i for i, m in enumerate(_MONTH_NAMES.split(), start=1)}


@dataclass
class Notice:
    title: str
    url: str
    date: str  # ISO yyyy-mm-dd, or "" when the site does not publish one
    source: str
    source_label: str
    bs_date: str = ""  # 2083/05/03, derived from `date`
    bs_label: str = ""  # 2083 Bhadau 3


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _iso(year: str, month: str, day: str) -> str:
    try:
        return datetime.date(int(year), int(month), int(day)).isoformat()
    except ValueError:
        return ""


def parse_entrance(html: str, base: str) -> list[Notice]:
    """entrance.ioe.edu.np: numbered cards, date written MM/DD/YYYY."""
    soup = BeautifulSoup(html, "html.parser")
    out: list[Notice] = []
    for anchor in soup.select('a[href*="/Notice/Detail/"]'):
        card = anchor.find_parent(["div", "li", "article", "tr"]) or anchor
        text = _clean(card.get_text(" ", strip=True))
        date = ""
        if match := re.search(r"\b(\d{2})/(\d{2})/(\d{4})\b", text):
            date = _iso(match.group(3), match.group(1), match.group(2))
        title = re.sub(r"\b\d{2}/\d{2}/\d{4}\b", "", text)
        title = re.sub(r"View Full Notice\s*$", "", title, flags=re.IGNORECASE)
        title = _clean(re.sub(r"^\d+\s+", "", title))
        if title:
            out.append(Notice(title, urljoin(base, anchor["href"]), date, "", ""))
    return out


def parse_pcampus(html: str, base: str) -> list[Notice]:
    """pcampus.edu.np is WordPress: the publication date is in the permalink itself."""
    soup = BeautifulSoup(html, "html.parser")
    out: list[Notice] = []
    for anchor in soup.select('a[href*="pcampus.edu.np/20"]'):
        url = anchor["href"]
        match = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
        title = _clean(anchor.get_text(" ", strip=True))
        # The date-stamp link repeats each post's permalink; its text is just the date.
        if not title or not match or re.fullmatch(r"[A-Za-z]+ \d{1,2}, \d{4}.*", title):
            continue
        out.append(Notice(title, urljoin(base, url), _iso(*match.groups()), "", ""))
    return out


def _month_number(name: str) -> int | None:
    """A month name, spelled out or abbreviated, as a number.

    The WordPress sources write "August", the admission feeds write "Aug". A prefix is
    accepted only when it picks out exactly one month, so "Ju" stays unknown rather than
    silently becoming June.
    """
    name = name.lower()
    if name in _MONTHS:
        return _MONTHS[name]
    matches = [number for month, number in _MONTHS.items() if month.startswith(name)]
    return matches[0] if len(matches) == 1 else None


def _iso_from_name(month: str, day: str, year: str) -> str:
    """ "August 22, 2026" -> 2026-08-22. Unknown month names yield no date, not a guess."""
    number = _month_number(month)
    return _iso(year, str(number), day) if number else ""


# "Mon, 24 Aug 2026" -- the shape both admission portals publish.
_RFC_DATE = re.compile(r"\b(\d{1,2})\s+([A-Za-z]{3,})\s+(\d{4})\b")


def _iso_from_rfc(text: str) -> str:
    if not (match := _RFC_DATE.search(text)):
        return ""
    number = _month_number(match.group(2))
    return _iso(match.group(3), str(number), match.group(1)) if number else ""


def parse_wp_articles(html: str, base: str) -> list[Notice]:
    """WordPress: each notice is an <article> whose h2 holds the permalink, with the date
    written out in the surrounding text. Serves Pashchimanchal (ioepas.edu.np)."""
    soup = BeautifulSoup(html, "html.parser")
    out: list[Notice] = []
    for article in soup.select("article"):
        anchor = article.select_one("h2 a[href]")
        if not anchor:
            continue
        title = _clean(anchor.get_text(" ", strip=True))
        date = ""
        if match := re.search(
            r"\b([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})\b",
            _clean(article.get_text(" ", strip=True)),
        ):
            date = _iso_from_name(*match.groups())
        if title:
            out.append(Notice(title, urljoin(base, anchor["href"]), date, "", ""))
    return out


def parse_admission_portal(html: str, base: str) -> list[Notice]:
    """admission.ioe.edu.np: an htmx fragment, one table row per notice.

    The row's anchor has href="#" and carries the real path inside an onclick argument,
    so the link is read from there. A row whose path cannot be read is skipped rather
    than published pointing at "#": a notice a student cannot open is worse than one
    they never saw.
    """
    soup = BeautifulSoup(html, "html.parser")
    out: list[Notice] = []
    for row in soup.select("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
        if len(cells) < 3:
            continue
        anchor = row.find("a", onclick=True)
        match = re.search(r"'(/[^']+)'", anchor["onclick"]) if anchor else None
        title = _clean(cells[1])
        if title and match:
            date = _iso_from_rfc(cells[2])
            out.append(Notice(title, urljoin(base, match.group(1)), date, "", ""))
    return out


def parse_admission_feed(text: str, base: str) -> list[Notice]:
    """Thapathali and Chitwan: a JSON feed, {"notices": [{title, created, link}]}.

    The only source that hands over structured data rather than markup, and the only one
    whose links often point straight at the notice PDF instead of a page wrapping it.
    """
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []
    out: list[Notice] = []
    for item in payload.get("notices") or []:
        title = _clean(str(item.get("title") or ""))
        link = str(item.get("link") or "")
        if title and link:
            date = _iso_from_rfc(str(item.get("created") or ""))
            out.append(Notice(title, urljoin(base, link), date, "", ""))
    return out


def parse_ioepc_admission(html: str, base: str) -> list[Notice]:
    """admission.ioepc.edu.np (Purwanchal): a bootstrap row per notice, ISO date last."""
    soup = BeautifulSoup(html, "html.parser")
    out: list[Notice] = []
    for anchor in soup.select('a[href*="notice-details/"]'):
        row = anchor.find_parent("div", class_="row") or anchor.parent
        text = _clean(row.get_text(" ", strip=True))
        date = ""
        if match := re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text):
            date = _iso(*match.groups())
        # The row reads "1. <title> View Notice 2026-08-23"; none of that is the title.
        title = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", "", text)
        title = re.sub(r"View\s+Notice", "", title, flags=re.IGNORECASE)
        title = _clean(re.sub(r"^\d+\s*\.?\s*", "", title))
        if title:
            out.append(Notice(title, urljoin(base, anchor["href"]), date, "", ""))
    return out


@dataclass(frozen=True)
class Source:
    key: str
    label: str
    url: str
    parser: Callable[[str, str], list[Notice]]
    # Thapathali and Chitwan answer their feed only on POST; a GET there returns
    # {"Error":"Only POST method is allowed"} rather than an error status, so it would
    # otherwise parse to zero notices and look like a site that had published nothing.
    method: str = "GET"


# Admission and entrance only. Tribhuvan University's own feeds used to be sources here
# and are deliberately gone: a student asking when the admission list is published does
# not need the university's unrelated notices competing for the six slots in the digest.
SOURCES = [
    Source(
        "entrance",
        "IOE Entrance Exam Board",
        "https://entrance.ioe.edu.np/Notice",
        parse_entrance,
    ),
    Source(
        "admission",
        "IOE Central Admission Portal",
        f"https://admission.ioe.edu.np/be/{ADMISSION_YEAR}/public/get-notices",
        parse_admission_portal,
    ),
    Source(
        "pcampus",
        "Pulchowk Campus",
        "https://pcampus.edu.np/category/admission-notices/",
        parse_pcampus,
    ),
    Source(
        "thapathali",
        "Thapathali Campus",
        f"https://admission.tcioe.edu.np/be/{ADMISSION_YEAR}/get-feed.php",
        parse_admission_feed,
        method="POST",
    ),
    Source(
        "pashchimanchal",
        "Pashchimanchal Campus",
        "https://ioepas.edu.np/category/news-notices/admission-notice",
        parse_wp_articles,
    ),
    Source(
        "purwanchal",
        "Purwanchal Campus",
        "https://admission.ioepc.edu.np/notices/list",
        parse_ioepc_admission,
    ),
    Source(
        "chitwan",
        "Chitwan Engineering Campus",
        "https://admission.ioecc.edu.np/get-feed.php",
        parse_admission_feed,
        method="POST",
    ),
]

# Every campus now has a feed. The two that did not -- Thapathali, whose main site renders
# its notice list in the browser, and Chitwan, which published nothing of its own -- both
# turned out to have an admission portal that serves one directly, so the headless browser
# the old note here called for is not needed after all.


def _dedupe(notices: list[Notice]) -> list[Notice]:
    seen: set[str] = set()
    out: list[Notice] = []
    for notice in notices:
        if notice.url in seen:
            continue
        seen.add(notice.url)
        out.append(notice)
    return out


def refresh() -> dict:
    """Fetch every source and write the cache. Failures are recorded, not raised."""
    notices: list[Notice] = []
    status: dict[str, dict] = {}

    headers = {"User-Agent": USER_AGENT}
    with httpx.Client(
        timeout=TIMEOUT, follow_redirects=True, headers=headers
    ) as client:
        for source in SOURCES:
            key, label, url = source.key, source.label, source.url
            try:
                if source.method == "POST":
                    response = client.post(url, json={})
                else:
                    response = client.get(url)
                response.raise_for_status()
                found = _dedupe(source.parser(response.text, url))[:PER_SOURCE_LIMIT]
                for notice in found:
                    notice.source, notice.source_label = key, label
                    notice.bs_date, notice.bs_label = ad_to_bs_labels(notice.date)
                notices.extend(found)
                status[key] = {
                    "label": label,
                    "url": url,
                    "count": len(found),
                    "error": "",
                }
            except Exception as exc:  # noqa: BLE001 - one bad site must not sink the rest
                status[key] = {
                    "label": label,
                    "url": url,
                    "count": 0,
                    "error": str(exc)[:200],
                }

    # Undated notices sort last rather than being dropped; a missing date is not a reason
    # to hide a notice a student may need.
    notices.sort(key=lambda n: n.date or "0000-00-00", reverse=True)

    payload = {
        "updated_at": datetime.datetime.now(tz=datetime.UTC).isoformat(),
        "today_nepal": today_in_nepal().isoformat(),
        "sources": status,
        "notices": [asdict(n) for n in notices],
    }
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload


def load() -> dict:
    """Read the cache. Never scrapes; returns an empty shell when not yet built."""
    if not CACHE_PATH.exists():
        return {"updated_at": "", "today_nepal": "", "sources": {}, "notices": []}
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"updated_at": "", "today_nepal": "", "sources": {}, "notices": []}


DIGEST_LIMIT = 6


def digest(limit: int = DIGEST_LIMIT) -> str:
    """The newest notices, as a block the model can read the feed's state off.

    Retrieval surfaces a notice when a question happens to match its title. This is the
    other half: a standing answer to "has anything been published recently", which no
    amount of similarity search provides, because the question names no notice.
    """
    payload = load()
    items = [n for n in (payload.get("notices") or []) if n.get("title")]
    checked = payload.get("updated_at", "")[:10]
    if not items:
        return (
            "Notice feed: the official notice listings could not be read"
            f"{f' (last checked {checked})' if checked else ''}. Do not tell the student "
            "whether anything has or has not been published recently; point them to "
            "entrance.ioe.edu.np instead."
        )

    lines = []
    for notice in items[:limit]:
        when = notice.get("bs_date") or ""
        ad = notice.get("date") or ""
        stamp = f"{when} BS / {ad} AD" if when and ad else (ad or when or "undated")
        lines.append(
            f"- {stamp} -- {notice['title']} "
            f"({notice.get('source_label', 'IOE')}) {notice.get('url', '')}"
        )

    return (
        f"Notice feed -- the {len(items)} most recent notice listings this app tracks, "
        f"last checked {checked}. These are listings, not the notices themselves: each "
        "says that something was published and when, not what it says.\n"
        f"The {len(lines)} newest:\n" + "\n".join(lines)
    )


def remember_indexed(ids: list[str]) -> None:
    """Record which notice records are in the vector store, so the next refresh knows
    what to remove. Kept beside the notices rather than in a file of its own: the two
    are only ever meaningful together."""
    payload = load()
    if not payload.get("updated_at"):
        return
    payload["indexed_ids"] = ids
    CACHE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def age_seconds(payload: dict | None = None) -> float:
    """How long since the cache was last written. A cache that has never been built, or
    whose timestamp is unreadable, is infinitely old -- which is the answer that makes
    the caller refresh it."""
    payload = load() if payload is None else payload
    stamp = payload.get("updated_at") or ""
    try:
        written = datetime.datetime.fromisoformat(stamp)
    except ValueError:
        return float("inf")
    if written.tzinfo is None:
        written = written.replace(tzinfo=datetime.UTC)
    return (datetime.datetime.now(tz=datetime.UTC) - written).total_seconds()


def main() -> None:
    """Entry point for `uv run ioe-notices`."""
    payload = refresh()
    for key, info in payload["sources"].items():
        state = (
            f"ERROR {info['error']}" if info["error"] else f"{info['count']} notices"
        )
        print(f"{key:10s} {state}")
    print(f"total {len(payload['notices'])} -> {CACHE_PATH}")


if __name__ == "__main__":
    main()
