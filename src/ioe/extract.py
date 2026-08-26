"""Turn a published notice PDF into text a human can check before it is indexed.

The corpus is hand-translated Markdown, and `docs/README.md` says why: the failure mode
that matters is numeric drift, and a wrong figure in a fee table is a student paying the
wrong amount. Nothing here changes that. What it changes is the starting point -- a
reviewer reads extracted text instead of retyping a PDF, and the extraction is recorded
with what it is and is not sure about.

Three things were measured across the fifteen PDFs in docs/downloads/ before this module
was written, and the design follows from them:

  13 of 15 carry a real text layer. Only 04_Payment_Notice.pdf is a true scan. This is
  a text-extraction problem, not an OCR problem, and needs no OCR dependency.

  `pdftotext -layout` reproduces tabular data exactly. The applicant table in
  Pulchowk_Priority_Applicants_2083-1.pdf comes out row for row identical to the CSV that
  was transcribed from it by hand. Tables are where the numbers live, and tables are the
  part that extracts cleanly.

  Nepali prose comes out one of two ways, and one of them is silent garbage. Some PDFs
  give real Unicode Devanagari. Others were typeset in Preeti, a legacy font that maps
  Devanagari glyphs onto ASCII bytes, and those extract as text that looks like text,
  raises no error, and means nothing: `OlGhlgol/Ë cWoog ;+:yfg` is इन्जिनियरिङ अध्ययन संस्थान.

That last one is the whole reason this module classifies before it returns. Text that is
wrong but well-formed is more dangerous than text that is missing, because only one of
those announces itself.
"""

import hashlib
import json
import re
import subprocess
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

PENDING_DIR = Path(__file__).resolve().parents[2] / ".cache" / "pending"
TIMEOUT = 30.0
USER_AGENT = "Mozilla/5.0 (compatible; IOE-Admission-Assistant/1.0)"

# Past this a PDF is a document rather than a cover sheet. Below it there is nothing for a
# reviewer to read and the extraction is not worth queueing.
MIN_USEFUL_CHARS = 200

# A PDF big enough to be a full pass list is not a notice; it is a data file, and it
# belongs in docs/data/ through results.py, not in the prose index.
MAX_PDF_BYTES = 12_000_000


# ── Preeti ────────────────────────────────────────────────────────────────────
# Preeti maps each Devanagari glyph to an ASCII byte, so extraction returns the bytes that
# were typed rather than the text that was read. The mapping is deterministic and this is
# its table. Two ordering rules go with it, both consequences of the font being a typing
# layout rather than an encoding:
#
#   ि  is typed before the consonant cluster it attaches to and rendered after it.
#   र् (reph) is typed after the cluster it caps and rendered before it.
#
# Longest key first, always: "cf]" is ओ, and matching "cf" first would leave a stray े.

_PREETI: dict[str, str] = {
    # independent vowels
    "cf}": "औ", "cf]": "ओ", "cf": "आ", "P]": "ऐ", "pm": "ऊ", "O{": "ई",
    "c": "अ", "O": "इ", "p": "उ", "P": "ए",
    # conjuncts that occupy more than one byte
    "If": "क्ष", "if": "ष", "em": "झ", "km": "फ", "0f": "ण", "1": "ज्ञ",
    "qm": "क्र", "q": "त्र", "|": "्र", ">": "श्र", "2": "द्ध", "b|": "द्र",
    "å": "द्व", "?": "रू", "~": "ञ्", "Tf": "त्ता", "B\"": "द्य", "›": "ङ्ग", "¿": "रू", "Ù": "ं",
    "S": "क्", "V": "ख्", "U": "ग्", "H": "ज्", "6": "ट", "7": "ठ", "8": "ड", "9": "ढ",
    # consonants
    "s": "क", "v": "ख", "u": "ग", "3": "घ", "ª": "ङ", "Ë": "ङ",
    "r": "च", "5": "छ", "h": "ज", "`": "ञ",
    "t": "त", "y": "थ", "b": "द", "w": "ध", "g": "न",
    "k": "प", "a": "ब", "e": "भ", "d": "म",
    "o": "य", "/": "र", "n": "ल", "j": "व",
    "z": "श", ";": "स", "x": "ह",
    # half forms
    "G": "न्", "D": "म्", "N": "ल्", "W": "ध्", "B": "ब्", "Q": "त्", ":": "स्",
    "R": "च्", "Z": "श्", "K": "प्", "T": "त्", "J": "व्", "Y": "थ्", "C": "ङ्",
    # matras
    "f]": "ो", "f}": "ौ",
    "f": "ा", "l": "ि", "L": "ी", "'": "ु", '"': "ू", "]": "े", "}": "ै", "[": "ृ",
    "+": "ं", "F": "ँ", "M": "ः", "{": "र्", "\\": "्",
    # digits -- the shifted number row, verified against a hand transcription:
    # "@)*#÷)$÷@&" is 2083/04/27, which is the date docs/translated/13_... records.
    "!": "१", "@": "२", "#": "३", "$": "४", "%": "५",
    "^": "६", "&": "७", "*": "८", "(": "९", ")": "०",
    # punctuation
    "=": ".", "÷": "/", ".": "।", ",": ",",
}  # fmt: skip

_PREETI_KEYS = sorted(_PREETI, key=len, reverse=True)
_I_MATRA = "ि"
_REPH = "र्"
_HALANT = "्"

# Bytes that carry a Devanagari glyph in Preeti but are ordinary punctuation in English.
# A run of them is what tells Preeti apart from a page of English prose.
_PREETI_MARKS = re.compile(r"[;/\]\[{}'\"=+^&*()!@#$%]")
_DEVANAGARI = re.compile(r"[ऀ-ॿ]")
# Base letters only -- not matras, not the halant, not the anusvara.
_CONSONANT = re.compile(r"[क-हक़-य़]")
_LATIN_WORD = re.compile(r"[A-Za-z]{3,}")


def _decode_run(run: str) -> str:
    """One run of Preeti bytes to Devanagari, longest key first."""
    out: list[str] = []
    i = 0
    while i < len(run):
        for key in _PREETI_KEYS:
            if run.startswith(key, i):
                out.append(_PREETI[key])
                i += len(key)
                break
        else:
            out.append(run[i])
            i += 1
    return "".join(out)


def _cluster_end(text: str, start: int) -> int:
    """The index just past the consonant cluster beginning at `start`.

    A cluster is a consonant plus every halant-bound consonant after it, so न् + ज is one
    cluster and क् + ष is one cluster. Walking it correctly is the whole difference between
    इन्जि and इनि्ज -- a matra dropped inside a conjunct binds to the wrong letter.
    """
    i = start
    if i >= len(text) or not _CONSONANT.match(text[i]):
        return start
    i += 1
    while i + 1 < len(text) and text[i] == _HALANT and _CONSONANT.match(text[i + 1]):
        i += 2
    return i


def _reorder(text: str) -> str:
    """Apply the two rules that make a typing layout into readable Devanagari.

    Both move a mark across the cluster it belongs to, in opposite directions:

        ि  is typed before its cluster and rendered after it.
        र् is typed after its cluster and rendered before it.
    """
    out: list[str] = []
    i = 0
    while i < len(text):
        if text[i] == _I_MATRA:
            end = _cluster_end(text, i + 1)
            if end > i + 1:
                out.append(text[i + 1 : end])
                out.append(_I_MATRA)
                i = end
                continue
        out.append(text[i])
        i += 1
    text = "".join(out)

    # The reph caps a whole syllable, so it hops back over any matras sitting on that
    # syllable as well as the cluster itself: egf{ is भर्ना, never भनर्ा.
    def _hop(match: re.Match) -> str:
        body = match.group(1)
        start = len(body)
        # Back over the matras sitting on the syllable, then over the consonant itself:
        # the reph is rendered before the letter, not between the letter and its vowel.
        while start and not _CONSONANT.match(body[start - 1]):
            start -= 1
        start = max(start - 1, 0)
        while start >= 2 and body[start - 1] == _HALANT:
            start -= 2
        return body[:start] + _REPH + body[start:]

    return re.sub(r"([ऀ-ॿ]+)" + _REPH, _hop, text)


def looks_like_preeti(text: str) -> bool:
    """Whether this text is Devanagari typed in a legacy font rather than English.

    Deliberately conservative. The cost of a false positive is mangling a page of real
    English into Devanagari nonsense; the cost of a false negative is a reviewer seeing
    the raw bytes and saying so. The second is recoverable and the first is not, so the
    test requires both a high density of Preeti-only marks and an absence of the ordinary
    English words that any genuinely English notice is full of.
    """
    stripped = re.sub(r"\s+", "", text)
    if len(stripped) < MIN_USEFUL_CHARS or _DEVANAGARI.search(text):
        return False
    marks = len(_PREETI_MARKS.findall(stripped))
    words = len(_LATIN_WORD.findall(text))
    return marks / len(stripped) > 0.08 and words < len(stripped) / 40


def _preeti_density(line: str) -> float:
    """Share of a line's non-space characters that carry a Devanagari glyph in Preeti.

    English prose uses these bytes as punctuation and uses them sparsely. Preeti uses them
    as letters, so they run at several per word.
    """
    # A line that already holds Devanagari cannot be Preeti -- Preeti is what you get
    # *instead of* Devanagari. Without this guard a real Nepali line carrying a bracketed
    # numeral, "(१)", scores above the threshold on its two brackets and gets "decoded",
    # turning ( and ) into the digits 9 and 0 inside text that was already correct.
    if _DEVANAGARI.search(line):
        return 0.0
    stripped = re.sub(r"\s+", "", line)
    # A ratio over a handful of characters is noise, not evidence: "Page 1/44" is 8
    # characters of which one is a slash, which scores 0.125 and would be "decoded" into
    # Devanagari rubble. Short lines are left alone.
    if len(stripped) < MIN_LINE_CHARS:
        return 0.0
    return len(_PREETI_MARKS.findall(stripped)) / len(stripped)


# Measured over every line of the fifteen PDFs in docs/downloads/. The distribution is
# continuous, not two clean humps -- roughly 360 lines sit between 0.05 and 0.15 -- so this
# threshold is a judgement about which mistake to make, not a gap in the data.
#
# It is set where it is because of what sits on either side. Below: English table rows and
# headers -- "Sno FormNo Applicant's Name" at 0.02, "Published on: 2083/04/19 B.E./B.Arch.
# Entrance Result" at 0.05, which scores as high as it does purely on the dots and slashes
# in the degree abbreviations. Above: "sDKo'6/ 36 60" at 0.18, which is कम्प्युटर and its two
# seat counts out of a booklet table.
#
# The gap between them is narrow and there is no cleaner signal available. Trying to
# settle it by looking for English words does not work, measured: OlGhlgol, cWoog and cGtu
# all contain ASCII vowels, so a vowel test calls इन्जिनियरिङ अध्ययन संस्थान English and leaves
# it as rubble. Erring high is the safer error, because rubble is visible to the reviewer
# this queue exists for and confidently mistranslated English is not.
PREETI_LINE_THRESHOLD = 0.07

# Shortest line the ratio above is trusted on.
MIN_LINE_CHARS = 10


def preeti_to_unicode(text: str) -> str:
    """Decode Preeti bytes to Devanagari, line by line.

    The decision is per line rather than per document or per word, because these files are
    reliably mixed and neither of the other two granularities works. A whole-document
    decode mangles the English table bodies that are the most valuable thing in the file --
    the applicant names and districts on a priority list. A per-word rule cannot tell
    `nflu` (लागि) from `Male`: both are short, lowercase-ish Latin, and no spelling test
    separates them. A line is the right unit because these documents put Nepali prose and
    English table rows on different lines and essentially never on the same one.
    """
    out = [
        _reorder(_decode_run(line))
        if _preeti_density(line) >= PREETI_LINE_THRESHOLD
        else line
        for line in text.split("\n")
    ]
    return unicodedata.normalize("NFC", "\n".join(out))


# ── extraction ────────────────────────────────────────────────────────────────


@dataclass
class Extracted:
    """One notice, pulled apart far enough for a human to judge it."""

    url: str
    title: str
    source: str
    date: str
    year: str  # BS, because that is the year every document in docs/ is filed under
    encoding: str  # unicode | preeti | latin | scanned
    preeti_lines: int  # how many lines the decoder rewrote -- 0 on a clean document
    chars: int
    text: str

    @property
    def needs_ocr(self) -> bool:
        return self.encoding == "scanned"


def pdf_text(data: bytes) -> str:
    """The text layer of a PDF, laid out.

    -layout is not cosmetic. Without it pdftotext reads a table column by column and the
    rows interleave; with it the applicant tables come out aligned, which is the whole
    reason the priority CSV can be regenerated rather than retyped. Returns "" for a PDF
    with no text layer -- that is a scan, and the caller decides what to do about it.
    """
    try:
        done = subprocess.run(
            ["pdftotext", "-q", "-layout", "-", "-"],
            input=data,
            capture_output=True,
            timeout=TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return done.stdout.decode("utf-8", errors="replace")


def tidy(text: str) -> str:
    """Undo what -layout leaves behind, without undoing what it is for.

    pdftotext -layout pads every line out to the position it occupied on the page, which
    is exactly what keeps a table's columns lined up and exactly what makes the prose
    around it unreadable. Markdown then reads any line indented four spaces as a code
    block, so an approved notice would render as one grey slab.

    Removing the *common* indent fixes both: the page's left margin goes, and every
    column keeps its position relative to the others. Runs of blank lines collapse for
    the same reason -- a page break should not read as the end of the document.
    """
    lines = text.split("\n")
    filled = [line for line in lines if line.strip()]
    margin = min((len(line) - len(line.lstrip()) for line in filled), default=0)
    out = [line[margin:] if line.strip() else "" for line in lines]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def classify(text: str) -> tuple[str, int]:
    """What this document predominantly is, and how many of its lines are Preeti.

    Returns one of scanned / unicode / preeti / latin, plus the Preeti line count, because
    these documents are routinely mixed and the dominant class alone would mislead a
    reviewer. 13_Pulchowk_BE_Admission_Detail_Notice_2083.pdf is the case that forced it:
    1,655 characters of real Devanagari alongside several hundred lines of Preeti, so
    calling the file "unicode" and stopping there would leave half the notice as rubble.
    """
    if len(re.sub(r"\s+", "", text)) < MIN_USEFUL_CHARS:
        return "scanned", 0
    lines = text.split("\n")
    preeti = sum(1 for line in lines if _preeti_density(line) >= PREETI_LINE_THRESHOLD)
    if preeti > len(lines) / 4:
        return "preeti", preeti
    if _DEVANAGARI.search(text):
        return "unicode", preeti
    return "latin", preeti


def extract(data: bytes, notice: dict) -> Extracted:
    """A downloaded PDF and the notice record it came from, as one reviewable item.

    The Preeti decoder always runs. It is a no-op on any line that is not Preeti, and
    running it unconditionally is what makes a mixed document come out whole rather than
    half-decoded according to whichever encoding happened to win the vote.
    """
    raw = pdf_text(data)
    encoding, preeti_lines = classify(raw)
    text = raw if encoding == "scanned" else tidy(preeti_to_unicode(raw))
    return Extracted(
        url=notice.get("url", ""),
        title=notice.get("title", ""),
        source=notice.get("source_label", "") or notice.get("source", ""),
        date=notice.get("date", ""),
        year=(notice.get("bs_date") or "").split("/")[0],
        encoding=encoding,
        preeti_lines=preeti_lines,
        chars=len(re.sub(r"\s+", "", text)),
        text=text,
    )


def _pdf_link(html: str, base: str) -> str:
    """The first PDF a notice page links to, or "".

    Only Thapathali and Chitwan link straight at a file; every other source links to a
    page that links to the PDF, and without this hop the feature would cover four notices
    out of sixty-four. Restricted to http(s) so a page cannot point the fetcher at a
    file:// path, and it takes the first match rather than trying to be clever -- these
    pages carry one attachment, and guessing between several would be worse than not
    following at all.
    """
    soup = BeautifulSoup(html, "html.parser")
    for anchor in soup.find_all("a", href=True):
        target = urljoin(base, str(anchor["href"]))
        if ".pdf" in target.lower() and target.startswith(("http://", "https://")):
            return target
    return ""


def fetch(url: str, hop: bool = True) -> bytes | None:
    """The PDF behind a notice link, or None if there is not one.

    Content-type is checked rather than the extension: some sources link straight at a
    .pdf on a CDN, others serve one from a path that does not say so. When the response
    is a page instead, its first PDF link is followed once and only once -- a notice page
    linking to another notice page is a loop, and one hop is all any observed source
    needs.
    """
    try:
        with httpx.Client(
            timeout=TIMEOUT, follow_redirects=True, headers={"User-Agent": USER_AGENT}
        ) as client:
            response = client.get(url)
            response.raise_for_status()
            kind = response.headers.get("content-type", "").lower()
            if "pdf" in kind or response.content.startswith(b"%PDF"):
                body = response.content
                return body if len(body) <= MAX_PDF_BYTES else None
            if hop and "html" in kind:
                target = _pdf_link(response.text, str(response.url))
                return fetch(target, hop=False) if target else None
            return None
    except Exception:  # noqa: BLE001 - a notice we cannot read is skipped, never fatal
        return None


# ── the pending queue ─────────────────────────────────────────────────────────
# Extraction writes here and stops. Nothing in this file reaches Chroma; approving does
# that, and approving is a person. The queue is a directory of JSON rather than a table
# because it is small, it is inspectable with cat, and it survives a container restart
# through the same .cache volume the notice cache already uses.


def key_for(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]


def queue(item: Extracted) -> Path:
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    path = PENDING_DIR / f"{key_for(item.url)}.json"
    path.write_text(
        json.dumps(asdict(item), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return path


def pending() -> list[dict]:
    """Everything waiting on a reviewer, newest notice first."""
    if not PENDING_DIR.exists():
        return []
    out: list[dict] = []
    for path in PENDING_DIR.glob("*.json"):
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        item["key"] = path.stem
        out.append(item)
    out.sort(key=lambda item: item.get("date") or "0000-00-00", reverse=True)
    return out


def take(key: str) -> dict | None:
    """Read one pending item and remove it from the queue."""
    path = PENDING_DIR / f"{key}.json"
    if not path.is_file() or path.parent != PENDING_DIR:
        return None
    try:
        item = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    path.unlink(missing_ok=True)
    return item


def seen() -> set[str]:
    """Notice keys already extracted, so a refresh does not re-download the same PDFs."""
    if not PENDING_DIR.exists():
        return set()
    return {path.stem for path in PENDING_DIR.glob("*.json")}


# ── harvest ───────────────────────────────────────────────────────────────────
# Deliberately not part of notices.refresh(). That runs in a background thread on every
# chat turn, and adding a dozen PDF downloads to it would turn a cheap freshness check
# into a minute of network for a student who asked about fees. Harvesting is an explicit
# act: the admin console, or `ioe-extract` from a shell.

# One harvest is one small batch. There is no deadline on a review queue, and a run that
# pulls six documents is one a person can be asked to look at.
HARVEST_LIMIT = 6

SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slug(title: str, key: str) -> str:
    """A filename for an approved notice: readable, ASCII, and unique by key.

    Nepali titles slug to nothing at all, so the key is always appended rather than used
    only as a tiebreak -- a directory of files called notice-1.md tells a maintainer less
    than nothing.
    """
    base = SLUG_STRIP.sub("-", title.lower()).strip("-")[:60].strip("-")
    return f"{base}-{key}" if base else f"notice-{key}"


def frontmatter(item: dict) -> str:
    """The same YAML shape docs/README.md documents and the upload route validates.

    `encoding` and `extracted` are recorded on purpose. A reader six months from now
    needs to know this file was machine-extracted and which decoder touched it, because
    that is exactly the provenance that decides how much to trust a number in it.
    """
    title = str(item.get("title") or "Untitled notice").replace('"', "'")
    lines = [
        "---",
        f'title: "{title}"',
        f'source: "{item.get("source", "")}"',
        f'url: "{item.get("url", "")}"',
        f'date: "{item.get("date", "")}"',
        f'year: "{item.get("year", "")}"',
        f'encoding: "{item.get("encoding", "")}"',
        "extracted: true",
        "---",
        "",
        f"# {title}",
        "",
    ]
    if item.get("encoding") == "preeti" or item.get("preeti_lines"):
        note = (
            "> Extracted from a PDF typeset in the Preeti legacy font; "
            f"{item.get('preeti_lines', 0)} lines were decoded to Unicode. "
            "Check any figure here against the original before relying on it."
        )
        lines += [note, ""]
    return "\n".join(lines)


def harvest(limit: int = HARVEST_LIMIT) -> dict:
    """Extract the newest notices that link to a PDF and queue them for review.

    Nothing here writes to the document set or the index. The queue is the whole output.
    """
    from ioe import notices as notices_mod

    already = seen()
    queued, skipped, scans = 0, 0, 0
    for notice in notices_mod.load().get("notices", []):
        if queued >= limit:
            break
        url = notice.get("url", "")
        if not url or key_for(url) in already:
            continue
        data = fetch(url)
        if data is None:
            skipped += 1
            continue
        item = extract(data, notice)
        if item.needs_ocr:
            # A true scan. Recorded in the count so it is visible that the notice was
            # seen and could not be read, rather than silently absent.
            scans += 1
            continue
        queue(item)
        queued += 1
    return {
        "queued": queued,
        "not_pdf": skipped,
        "needs_ocr": scans,
        "pending": len(pending()),
    }


def main() -> None:
    result = harvest()
    print(
        f"queued {result['queued']}, skipped {result['not_pdf']} non-PDF, "
        f"{result['needs_ocr']} need OCR -- {result['pending']} awaiting review"
    )
