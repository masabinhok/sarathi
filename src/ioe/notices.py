"""Scrape published notices from IOE, TU, and campus websites into a local cache.

These are other people's websites and their markup will change without warning, so each
parser is small, defensive, and independent: one site breaking or going down degrades that
source to an error entry and leaves the rest intact. Nothing here feeds the model -- these
notices are displayed to students as links, never quoted as fact.
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
]


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
