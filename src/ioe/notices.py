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


def parse_tu_theme(html: str, base: str) -> list[Notice]:
    """tu.edu.np and ioe.tu.edu.np: date and title share one wrapper.

    The two sites use different wrapper classes for the same layout, and each has pages
    using the other's, so both selectors are tried rather than one per source.
    """
    soup = BeautifulSoup(html, "html.parser")
    out: list[Notice] = []
    for wrapper in soup.select(".recent-post-wrapper, .inner-notice-wrap"):
        anchor = wrapper.find("a", href=True)
        if not anchor:
            continue
        text = _clean(wrapper.get_text(" ", strip=True))
        date = ""
        if match := re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text):
            date = _iso(match.group(1), match.group(2), match.group(3))
        title = _clean(re.sub(r"\b\d{4}-\d{2}-\d{2}\b", "", text))
        if title and title != ".":
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


def _iso_from_name(month: str, day: str, year: str) -> str:
    """ "August 22, 2026" -> 2026-08-22. Unknown month names yield no date, not a guess."""
    number = _MONTHS.get(month.lower())
    return _iso(year, str(number), day) if number else ""


def parse_wrc(html: str, base: str) -> list[Notice]:
    """wrc.edu.np (Pashchimanchal): WordPress; each notice is an <article> whose h2 holds
    the permalink, with the date written out in the surrounding text."""
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


def parse_ioepc(html: str, base: str) -> list[Notice]:
    """ioepc.edu.np (Purwanchal): cards carrying an ISO timestamp after the title."""
    soup = BeautifulSoup(html, "html.parser")
    out: list[Notice] = []
    for card in soup.select(".card"):
        anchor = card.find("a", href=True)
        if not anchor:
            continue
        text = _clean(card.get_text(" ", strip=True))
        date = ""
        if match := re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text):
            date = _iso(*match.groups())
        # The timestamp trails the title, minutes and all, and is not part of it.
        title = _clean(re.sub(r"\b\d{4}-\d{2}-\d{2}(\s+[\d:]+)?", "", text))
        if title:
            out.append(Notice(title, urljoin(base, anchor["href"]), date, "", ""))
    return out


SOURCES = [
    (
        "entrance",
        "IOE Entrance Exam Board",
        "https://entrance.ioe.edu.np/Notice",
        parse_entrance,
    ),
    (
        "ioe",
        "Institute of Engineering",
        "https://ioe.tu.edu.np/notices",
        parse_tu_theme,
    ),
    ("tu", "Tribhuvan University", "https://tu.edu.np/notices", parse_tu_theme),
    (
        "pcampus",
        "Pulchowk Campus",
        "https://pcampus.edu.np/category/admission-notices/",
        parse_pcampus,
    ),
    (
        "wrc",
        "Pashchimanchal Campus",
        "https://wrc.edu.np/category/admission-notice/",
        parse_wrc,
    ),
    (
        "ioepc",
        "Purwanchal Campus",
        "https://www.ioepc.edu.np/info/category/notice/",
        parse_ioepc,
    ),
]

# Thapathali (tcioe.edu.np) and Chitwan (cec.tu.edu.np) are deliberately absent.
# Thapathali renders its notice list in the browser -- its served HTML contains no notice
# at all -- so scraping it would need a headless browser, which is a dependency this does
# not earn yet. Chitwan publishes no feed of its own and links to tu.edu.np, which is
# already a source above.


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
        for key, label, url, parser in SOURCES:
            try:
                response = client.get(url)
                response.raise_for_status()
                found = _dedupe(parser(response.text, url))[:PER_SOURCE_LIMIT]
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
