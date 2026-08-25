"""The one thing a prompt could not be trusted to do.

Issue `24` asks for the scope guard to go, and most of it does. The broad "is this about
IOE or not" classifier was the thing that refused `foreign?` and `what is its source` --
it judged a follow-up as though it were a whole message, and a message that means nothing
on its own looks like nothing on its own. That classifier is deleted. A question the
documents cannot answer is now answered in character, from the `uncovered` block, with
the conversation intact.

What is not deleted is a narrow detector for one class of message, because the prompt was
measured failing at it. Given a short scope instruction and asked for a Python function,
qwen2.5:7b replied:

    "This is outside what I cover, but here's a simple Python function to sum three
    numbers: ..."

and wrote it. Asked the capital of France it said "not related to IOE" and then answered
"Paris". The model says the deflection and does the task anyway -- the same shape as the
language failure in `19`, where it wrote the refusal and then switched to Nepali. The
app's own words are the only thing that has ever held.

So this fires on task substitution only: write me code, solve this equation, do my
homework, recommend a laptop, general-knowledge trivia. It is deliberately narrow. It
must not fire on a bare follow-up, and it must not fire on a real question that happens
to be unanswerable -- those get the `uncovered` block and a real reply. Precision is the
property that matters, and it is measured, not assumed: see `is_task_substitution` in the
eval suite.
"""

import re

# The app's own words, for the reason ENGLISH_ONLY_SENTENCE is the app's own words: asked
# to write its own deflection, the model writes one and then complies anyway.
OFF_TOPIC_SENTENCE = (
    "That is not something I can do -- I only know IOE admissions and the entrance "
    "exam. Ask me about the exam, your application, the fees, seats, a result or a "
    "campus and I can help."
)

# Each alternative is a task the assistant is being asked to perform instead of answering
# a question about IOE. Every one of these is anchored on both a verb and its object,
# because the verbs alone are all things a student legitimately asks -- "write" appears in
# "how do I write my name on the form", "calculate" in "calculate my total fee".
_TASK_SUBSTITUTION = re.compile(
    # Produce an artefact.
    r"\b(?:write|compose|generate|create|make|give)\s+(?:me\s+)?(?:a|an|the|some)?\s*"
    r"(?:python|java|javascript|c\+\+|sql|html|css|shell|bash)?\s*"
    r"(?:code|function|program|programme\s+in\s+\w+|script|algorithm|essay|poem|story|"
    r"song|joke|recipe|speech|letter\s+to\s+my|cover\s+letter|resume|cv)\b"
    # Do the mathematics.
    r"|\b(?:solve|simplify|integrate|differentiate|factorise|factorize)\b(?=.*[=^]|.*\b"
    r"equation|.*\bfor\s+x\b)"
    # Debug something.
    r"|\b(?:debug|fix)\s+(?:this|my|the)\s+(?:code|program|script|function|bug|error)\b"
    # Translate a text that is not a question for us.
    r"|\btranslate\s+(?:this|the\s+following|that)\b"
    # Do the schoolwork.
    r"|\b(?:my|the)\s+(?:physics|chemistry|maths?|mathematics|english|science)\s+"
    r"(?:homework|assignment|project)\b"
    r"|\b(?:do|help\s+(?:me\s+)?with|complete)\s+my\s+(?:homework|assignment)\b"
    # Shopping. "computer" is absent on purpose -- it is a programme here.
    r"|\b(?:recommend|suggest)\s+(?:me\s+)?(?:a|an|some|the\s+best)?\s*\w*\s*"
    r"(?:laptop|smartphone|mobile\s+phone|tablet|headphones?|movie|film|restaurant|"
    r"hotel|novel)\b"
    # General knowledge, asked as a lookup.
    r"|\bcapital\s+of\s+(?:france|nepal|india|\w+)\b"
    r"|\bwho\s+(?:won|invented|discovered|wrote|directed|founded)\b"
    r"|\bwho\s+is\s+the\s+(?:president|prime\s+minister|king|ceo)\b",
    re.IGNORECASE,
)


def is_task_substitution(text: str) -> bool:
    """Whether the message asks the assistant to do a task instead of answering.

    Narrow by design. Everything else that this app cannot answer -- another university,
    a holiday, a programme IOE does not run -- is a question, gets the uncovered block,
    and gets a real reply that stays in the conversation.
    """
    return bool(_TASK_SUBSTITUTION.search(text))
