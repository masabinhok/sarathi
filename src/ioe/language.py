"""Keeping the answer in English, whatever the question was written in.

Moved out of graph.py unchanged. It is settled, it was expensive to settle, and it reads
as a component here rather than as something a future edit might reopen -- which the
comment below is at pains to explain, because the obvious fix is the one that was
measured not to work.
"""

import re

from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama

from ioe.rag import NUM_CTX, OLLAMA_URL

TEXT_MODEL = "qwen2.5:7b"

# Same model, same num_ctx, so Ollama serves this from the runner it already has loaded
# rather than standing up a second one. See rag.NUM_CTX.
model = ChatOllama(model=TEXT_MODEL, base_url=OLLAMA_URL, num_ctx=NUM_CTX)


# ── Keeping the answer in English ─────────────────────────────────────────────
# SYSTEM_PROMPT says to answer in English and on its own that does not hold. Measured
# against the live bot: asked "please reply in Nepali", asked in Nepali with no
# instruction at all, and asked for Hindi, qwen2.5:7b switched every time -- and what it
# produced was not worth reading, mixing Hindi into Nepali sentences and inventing
# syllabus subjects while it was at it.
#
# Four rounds of prompting could not fix it. Told to refuse and then answer, the model
# wrote the refusal in Nepali; given the refusal to copy, it copied it and then treated
# it as the whole reply on 3 of 12 runs; told the refusal was already handled and to
# ignore the request, it went back to Nepali on 12 of 18. The pattern across all four is
# that naming the request in the prompt is what keeps it alive.
#
# So the request is not named. It is removed. The sentence asking for another language
# is stripped out of the question, the app says the one thing that needs saying, and the
# model is handed an ordinary question -- which it answers in English, because that is
# what it does with ordinary questions.
#
# SYSTEM_PROMPT is down to one line on the subject for the same reason. The paragraph it
# used to carry explained the rule, offered two justifications the model could pass on,
# and told it what to do when asked for Nepali -- nine lines that named the request four
# times, in the prompt, on every turn, including the turns nobody asked.

_DEVANAGARI = re.compile(r"[\u0900-\u097f]")
_LATIN = re.compile(r"[A-Za-z]")

# Languages a student might ask to be answered in. English is deliberately absent: a
# student asking for English is asking for what they are already getting.
_OTHER_LANGUAGE = re.compile(
    r"\b(nepali|nepalese|hindi|newari|newa|maithili|bhojpuri|urdu|bengali|bangla|"
    r"tamil|chinese|mandarin|japanese|korean|arabic|russian|spanish|french|german|"
    r"portuguese|italian|devanagari)\b"
    r"|नेपाली|हिन्दी|हिंदी|मैथिली|भोजपुरी|नेवारी|उर्दू",
    re.IGNORECASE,
)

# A language on its own is not a request -- "is the exam set in Nepali" is a question
# about the exam. It takes a language and something that means "say it", together.
_SPEECH = re.compile(
    r"\b(reply|replies|answer|answers|respond|responds|write|writes|say|says|speak|"
    r"speaks|talk|talks|explain|explains|translate|translates|tell|tells)\b"
    r"|जवाफ|जवाब|भन्नु|लेख्नु|बोल्नु|दिनुहोस्|सुनाउनु|बताइए|समझाइए|लिखिए",
    re.IGNORECASE,
)

# Devanagari ends a sentence with a danda, which no ASCII sentence splitter knows about.
_SENTENCE = re.compile(r"(?<=[.!?।])\s+|\n+")

# The app's own words. Fixed, so the wording cannot drift from one turn to the next, and
# naming no particular language, because the same sentence has to serve a request for
# Nepali and a request for Hindi.
ENGLISH_ONLY_SENTENCE = (
    "I answer only in English. The notices I work from are in English, and I am not "
    "reliable enough in any other language to be trusted with something you will act on."
)

TRANSLATE_PROMPT = """Translate the student's message into English.

Output only the translation. No preamble, no quotes, no explanation, no note about what \
you did. Keep a question a question. Leave proper nouns, form numbers, dates and any \
English already in the message exactly as they are.

Message: {question}

English:"""


def without_language_request(question: str) -> str:
    """The question with any "reply in <language>" sentence taken out of it.

    Returns the question unchanged when it contains no such sentence -- and, crucially,
    when the request *is* the whole question. "Can I answer the exam paper in Nepali?"
    reads as a request by every test above, and stripping it would leave nothing to
    answer; a student asking that is asking about the exam, so they get the ordinary
    treatment and an ordinary answer.
    """
    parts = [p for p in _SENTENCE.split(question) if p.strip()]
    kept = [p for p in parts if not (_OTHER_LANGUAGE.search(p) and _SPEECH.search(p))]
    if not kept or len(kept) == len(parts):
        return question
    return " ".join(p.strip() for p in kept)


def english_only_preface(question: str) -> str:
    """The app's sentence for a turn that asked for another language, or "".

    Used twice on the same turn and it must agree with itself: api._stream sends it
    ahead of the model's first token so the student sees it as the answer opens, and
    chat_node prepends it to the stored message so a reloaded conversation reads the
    same as the one that was watched live.
    """
    if without_language_request(question) == question:
        return ""
    return f"{ENGLISH_ONLY_SENTENCE}\n\n"


def _in_devanagari(text: str) -> bool:
    """Whether the text is written in Devanagari rather than merely quoting a term in it."""
    return len(_DEVANAGARI.findall(text)) > len(_LATIN.findall(text))


def read_in_english(question: str) -> str:
    """The question in English, translating it first if it was not written that way.

    Telling the model not to mirror the student's language does not hold either -- it
    answered a Nepali question in Nepali often enough to matter. Translating removes the
    thing being mirrored: the model is handed an English question, and English questions
    it answers in English every time.

    This is the same bargain the documents already get. They are translated on the way in
    because the model reads English better than it translates while it reasons, and a
    question is no different. Retrieval gets the same benefit for free: an English query
    embeds against an English index rather than across languages.

    The student's own words are what the transcript keeps. Only the copy the model reads
    is translated.
    """
    if not _in_devanagari(question):
        return question
    try:
        rendered = model.invoke(
            [HumanMessage(content=TRANSLATE_PROMPT.format(question=question))]
        )
        english = (rendered.content or "").strip()
    except Exception:  # noqa: BLE001 - a failed translation must not fail the answer
        return question
    # A translation that came back empty, or still in Devanagari, is no translation.
    return question if not english or _in_devanagari(english) else english
