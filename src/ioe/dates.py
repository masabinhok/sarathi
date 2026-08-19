"""Current-date grounding and Bikram Sambat conversion.

The model has no reliable sense of today's date and invents both AD and BS dates when
asked. It is also poor at BS arithmetic. So rather than asking it to calculate, this
module resolves every BS date in play to its AD equivalent and to a plain-language
offset from today, and hands the model the finished answer to read off.
"""

import datetime
import re
from zoneinfo import ZoneInfo

import nepali_datetime

# Students are in Nepal; the server may not be. Anchoring to Kathmandu keeps "today"
# correct for them regardless of where this runs.
NEPAL_TZ = ZoneInfo("Asia/Kathmandu")

# BS dates in these documents are written 2083/04/26 or 2083-04-26. The year window
# keeps AD dates (2026-08-11) from being misread as BS.
_BS_DATE_RE = re.compile(r"\b(20[6-9]\d)[/-](\d{1,2})[/-](\d{1,2})\b")
BS_MONTHS = (
    "Baishakh",
    "Jestha",
    "Ashadh",
    "Shrawan",
    "Bhadau",
    "Ashwin",
    "Kartik",
    "Mangsir",
    "Poush",
    "Magh",
    "Falgun",
    "Chaitra",
)
MAX_ANNOTATED = 12


def today_in_nepal() -> datetime.date:
    return datetime.datetime.now(tz=NEPAL_TZ).date()


def _relative(target: datetime.date, today: datetime.date) -> str:
    days = (target - today).days
    if days == 0:
        return "today"
    if days == 1:
        return "tomorrow"
    if days == -1:
        return "yesterday"
    if days > 0:
        return f"in {days} days"
    return f"{abs(days)} days ago"


def _bs_label(bs: nepali_datetime.date) -> str:
    month = BS_MONTHS[bs.month - 1] if 1 <= bs.month <= 12 else str(bs.month)
    return f"{bs.year} {month} {bs.day} (BS {bs.year}/{bs.month:02d}/{bs.day:02d})"


def today_context(today: datetime.date | None = None) -> str:
    """Ground the model in the current date, in both calendars."""
    today = today or today_in_nepal()
    bs = nepali_datetime.date.from_datetime_date(today)
    return (
        "[Today's date]\n"
        f"Nepali calendar (BS): {_bs_label(bs)}\n"
        f"Gregorian (AD): {today.isoformat()}, {today.strftime('%A')}"
    )


def annotate_dates(text: str, today: datetime.date | None = None) -> str:
    """Resolve each BS date appearing in `text` to AD and to an offset from today.

    Returns "" when the text carries no BS dates, so no block is injected needlessly.
    """
    today = today or today_in_nepal()
    seen: list[tuple[int, int, int]] = []
    for year, month, day in _BS_DATE_RE.findall(text):
        parts = (int(year), int(month), int(day))
        if parts not in seen:
            seen.append(parts)

    lines = []
    for year, month, day in seen[:MAX_ANNOTATED]:
        try:
            bs = nepali_datetime.date(year, month, day)
            ad = bs.to_datetime_date()
        except (ValueError, IndexError):
            continue  # out-of-range BS date printed in a document; skip rather than guess
        lines.append(
            f"BS {year}/{month:02d}/{day:02d} = AD {ad.isoformat()} ({_relative(ad, today)})"
        )

    if not lines:
        return ""
    return (
        "[Date conversions, computed - use these rather than calculating]\n"
        + "\n".join(lines)
    )
